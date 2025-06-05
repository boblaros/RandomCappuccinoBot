import random
from telebot import types
from utils.db import *
from config import DB_PATH
import sqlite3
from utils.utils import *
import os

user_data = {}

# Абсолютный путь для сервера
images_dir_prod = '/data/images'
# Относительный путь для локальной разработки
images_dir_dev = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data/images'))
# Логика определения пути
images_dir = images_dir_prod if os.path.exists('/data') else images_dir_dev

def register_user_handlers(user_bot, user_feedback, verification_codes):

    @user_bot.message_handler(commands=['start'])
    def send_welcome(message):
        if not is_user_registered(message.chat.id):
            user_bot.send_message(message.chat.id, "Hi! Enter your *university email* address to confirm your student status", parse_mode="Markdown")
            user_bot.register_next_step_handler(message, handle_email)
        else:
            user_bot.send_message(message.chat.id,
                             "You are already registered. If you need a new account, enter your *university email* to confirm your student status. Otherwise, use /skip command",
                             parse_mode="Markdown")
            user_bot.register_next_step_handler(message, handle_email)

    @user_bot.message_handler(commands=['help'])
    def help_command(message):
        """
        Отправляет список пользовательских команд с кнопками.
        """
        if not is_user_registered(message.chat.id):
            user_bot.send_message(message.chat.id, "You need to register first. Use /start to begin.")
            return

        help_text = (
            "🤖 *Help Menu*\n\n"
            "Here are the available commands you can use. Simply click on a button to execute the command or learn more."
        )

        # Создаём кнопки
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("My profile", callback_data="profile"))
        markup.add(types.InlineKeyboardButton("About the Bot", callback_data="about"))
        markup.add(types.InlineKeyboardButton("Rules", callback_data="rules"))
        markup.add(types.InlineKeyboardButton("FAQ", callback_data="faq"))
        markup.add(types.InlineKeyboardButton("Edit Profile", callback_data="editprofile"))
        markup.add(types.InlineKeyboardButton("Pause Pairings", callback_data="pause"))
        markup.add(types.InlineKeyboardButton("Resume Pairings", callback_data="resume"))
        markup.add(types.InlineKeyboardButton("Delete Profile", callback_data="delete_profile"))
        markup.add(types.InlineKeyboardButton("Leave Feedback", callback_data="feedback"))


        # Отправляем сообщение с кнопками
        user_bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode="Markdown")

    @user_bot.callback_query_handler(
        func=lambda call: call.data in ["profile", "about", "rules", "faq", "editprofile", "edit_profile", "pause",
                                        "resume",
                                        "delete_profile", "feedback"])
    def handle_help_callbacks(call):
        """
        Handles clicking on buttons in the menu /help.
        """
        if not is_user_registered(call.message.chat.id):
            user_bot.send_message(call.message.chat.id,
                             "You need to register first. Use /start to begin.")
            return

        options_text = {
            "profile": "Profile",
            "about": "About",
            "rules": "Rules",
            "faq": "FAQ",
            "editprofile": "Edit Profile",
            "edit_profile": "Edit Profile",
            "pause": "Pause",
            "resume": "Resume",
            "delete_profile": "Delete Profile",
            "feedback": "Feedback"
        }

        selected_option = options_text.get(call.data, "Unknown option")

        # Убираем кнопки и обновляем сообщение
        user_bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"👉 *{selected_option}*",
            parse_mode="Markdown"
        )

        # Выполняем соответствующую команду
        if call.data == "profile":
            profile(call.message)
        elif call.data == "about":
            about(call.message)
        elif call.data == "rules":
            rules(call.message)
        elif call.data == "faq":
            faq(call.message)
        elif call.data == "pause":
            user_bot.send_message(call.message.chat.id, "Use the /pause command to temporarily stop pairings.")
        elif call.data == "editprofile" or call.data == "edit_profile":
            user_bot.send_message(call.message.chat.id, "Use the /edit_profile command to change your profile.")
        elif call.data == "resume":
            user_bot.send_message(call.message.chat.id, "Use the /resume command to restart pairings.")
        elif call.data == "delete_profile":
            user_bot.send_message(call.message.chat.id,
                             "Use the /delete_profile command to permanently delete your profile.")
        elif call.data == "feedback":
            user_bot.send_message(call.message.chat.id, "Use the /feedback command to leave a rating and comments.")

    @user_bot.message_handler(commands=['profile'])
    def profile(message):
        # Подключаемся к базе данных и выполняем запрос
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Запрос для получения профиля пользователя по его chat.id
        cursor.execute("""
            SELECT name, city, occupation, program, interests, age, contacts
            FROM users
            WHERE id = ?
        """, (message.chat.id,))

        user = cursor.fetchone()
        conn.close()

        # Проверяем, найден ли пользователь
        if user:
            name, city, occupation, program, interests, age, contacts = user

            profile_message = (
                f"Now your profile looks like this! 🤌🏼☕️ \n\n"
                f"👤 *Name*: {escape_markdown_v1(name)}\n"
                f"🌆 *City*: {escape_markdown_v1(city)}\n"
                f"📝 *About me*: {escape_markdown_v1(occupation)}\n"
                f"🎓 *Program*: {escape_markdown_v1(program)}\n"
                f"💡 *Interests*: {escape_markdown_v1(interests)}\n"
                f"🎂 *Age*: {escape_markdown_v1(age)}\n"
                f"📞 *Contacts*: {escape_markdown_v1(contacts)}\n"
            )
            # Check if a local profile photo exists
            photo_path = os.path.join(images_dir, f'user{message.chat.id}_photo.jpg')

            try:
                with open(photo_path, 'rb') as photo:
                    user_bot.send_photo(message.chat.id, photo, caption=profile_message, parse_mode="Markdown")

            except FileNotFoundError:
                # Получаем фото профиля пользователя
                photos = user_bot.get_user_profile_photos(message.chat.id, limit=1)

                if photos.total_count > 0:
                    # Если фото есть, отправляем фото с текстом
                    photo_id = photos.photos[0][0].file_id  # ID первой фотографии
                    user_bot.send_photo(message.chat.id, photo_id, caption=profile_message, parse_mode="Markdown")
                else:
                    # Если фото нет, отправляем только текст
                    user_bot.send_message(message.chat.id, profile_message, parse_mode="Markdown")
        else:
            user_bot.send_message(message.chat.id, "Profile not found. Please fill out your profile first.")

    @user_bot.message_handler(commands=['about'])
    def about(message):
        """
        Отправляет описание бота и его целей.
        """

        if not is_user_registered(message.chat.id):
            user_bot.send_message(message.chat.id, "You need to register first. Use /start to begin.")
            return

        about_text = (
            "🤖 *About Random Cappuccino Bot*\n\n"
            "Welcome to Random Cappuccino Bot! ☕\n\n"
            "This bot is designed to help students from various universities network with one another. "
            "Each week, you'll be paired with a random participant based on your interests and preferences. "
            "The goal is to encourage meaningful connections and friendships.\n\n"
            "To participate, simply fill out the registration form, and each week you'll receive details about your pairing partner. "
            "Enjoy networking and coffee meetups! 😊"
        )
        user_bot.send_message(message.chat.id, about_text, parse_mode="Markdown")

    @user_bot.message_handler(commands=['rules'])
    def rules(message):
        """
        Отправляет правила использования бота и участия в подборе пар.
        """
        if not is_user_registered(message.chat.id):
            user_bot.send_message(message.chat.id, "You need to register first. Use /start to begin.")
            return

        rules_text = (
            "📜 *Rules for Using the Bot and Participating in Pairings*\n\n"
            "1️⃣ Fill out your profile with accurate and honest information.\n"
            "2️⃣ Respect your pairing partners: maintain polite and respectful communication.\n"
            "3️⃣ Avoid spamming or sharing inappropriate content.\n"
            "4️⃣ If you cannot meet your pairing partner, let them know in advance.\n"
            "5️⃣ Use the /pause command if you want to temporarily stop participating in pairings.\n"
            "6️⃣ The bot administrators reserve the right to remove users who violate the rules.\n\n"
            "By using this bot, you agree to follow these rules. Let’s make this community friendly and supportive! 😊"
        )
        user_bot.send_message(message.chat.id, rules_text, parse_mode="Markdown")

    @user_bot.message_handler(commands=['faq'])
    def faq(message):
        """
        Отправляет ответы на часто задаваемые вопросы.
        """

        if not is_user_registered(message.chat.id):
            user_bot.send_message(message.chat.id, "You need to register first. Use /start to begin.")
            return

        faq_text = (
            '❓ *Frequently Asked Questions*\n\n'
            '1️⃣ *How does the pairing process work?*\n'
            'Every week, the bot matches you with another participant based on shared interests.\n\n'
            '2️⃣ *Can I update my profile information?*\n'
            'Yes! Use the /edit\_profile command to make changes to your profile.\n\n'
            '3️⃣ *What if I don\'t want to participate temporarily?*\n'
            'You can use the /pause command to stop pairings temporarily and /resume to restart.\n\n'
            '4️⃣ *Can I delete my profile?*\n'
            'Yes, use the /delete\_profile command. You’ll be asked for confirmation before the deletion.\n\n'
            '5️⃣ *How do I provide feedback about the bot?*\n'
            'Use the /feedback command to rate the bot and leave your comments. We appreciate your input!\n\n'
            'If you have more questions, feel free to reach out to the admins via bot.random.cappuccino@gmail.com. 😊'
        )
        user_bot.send_message(message.chat.id, faq_text, parse_mode="Markdown")

    @user_bot.message_handler(commands=['skip'])
    def skip(message):  # noqa
        pass

    @user_bot.message_handler(commands=['pause'])
    def pause_pairing(message):
        """
        Приостанавливает подбор пар для пользователя (меняет status на 0).
        """
        with sqlite3.connect(DB_PATH) as conn_pause_pairing:
            cursor_pause_pairing = conn_pause_pairing.cursor()

            # Проверяем текущий статус пользователя
            cursor_pause_pairing.execute("SELECT status FROM users WHERE id = ?", (message.chat.id,))
            result = cursor_pause_pairing.fetchone()

            if result:
                current_status = result[0]
                if current_status == '1':
                    # Меняем статус на 0
                    cursor_pause_pairing.execute("UPDATE users SET status = 0 WHERE id = ?", (message.chat.id,))
                    conn_pause_pairing.commit()
                    user_bot.send_message(
                        message.chat.id,
                        "Pair matching has been paused. You will not receive matches until you resume."
                    )
                else:
                    user_bot.send_message(
                        message.chat.id,
                        "Pair matching is already paused."
                    )
            else:
                user_bot.send_message(
                    message.chat.id,
                    "Profile not found. Please complete registration first."
                )

    @user_bot.message_handler(commands=['resume'])
    def resume_pairing(message):
        """
        Возобновляет подбор пар для пользователя (меняет status на 1).
        """
        with sqlite3.connect(DB_PATH) as conn_resume_pairing:
            cursor_resume_pairing = conn_resume_pairing.cursor()

            # Проверяем текущий статус пользователя
            cursor_resume_pairing.execute("SELECT status FROM users WHERE id = ?", (message.chat.id,))
            result = cursor_resume_pairing.fetchone()

            if result:
                current_status = result[0]
                if current_status == '0':
                    # Меняем статус на 1
                    cursor_resume_pairing.execute("UPDATE users SET status = 1 WHERE id = ?", (message.chat.id,))
                    conn_resume_pairing.commit()
                    user_bot.send_message(
                        message.chat.id,
                        "Pair matching has been resumed! You will now participate in the next match."
                    )
                else:
                    user_bot.send_message(
                        message.chat.id,
                        "Pair matching is already active."
                    )
            else:
                user_bot.send_message(
                    message.chat.id,
                    "Profile not found. Please complete registration first."
                )

    @user_bot.callback_query_handler(func=lambda call: call.data == "start_questionnaire")
    def start_questionnaire_callback(call):
        if not check_message_for_command(user_bot, call.message):
            return

        new_text = call.message.text + "\n\n👉 *Fill out the questionnaire*"
        user_bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

        user_bot.send_message(call.message.chat.id, "Please enter your first and last name:")
        user_bot.register_next_step_handler(call.message, ask_gender)

    def ask_gender(message):
        if not check_message_for_command(user_bot, message): return

        name = message.text.strip()
        if len(name) > MAX_NAME_LENGTH:
            user_bot.send_message(message.chat.id,
                                  f"Your name is too long. Please enter a name shorter than {MAX_NAME_LENGTH} characters.")
            user_bot.register_next_step_handler(message, ask_gender)
            return

        user_data[message.chat.id]['name'] = name

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("Male", callback_data="gender_male"),
            types.InlineKeyboardButton("Female", callback_data="gender_female"),
            types.InlineKeyboardButton("Skip", callback_data="gender_skip")
        )

        user_bot.send_message(message.chat.id, "Please select your gender:", reply_markup=markup)

    @user_bot.callback_query_handler(func=lambda call: call.data.startswith("gender_"))
    def handle_gender_selection(call):
        gender_text = call.data.split("_")[1]  # Извлекаем значение пола (male, female или skip)

        # Сопоставляем текстовое значение с числом
        gender_map = {
            "male": 0,
            "female": 1,
            "skip": -1
        }
        gender = gender_map.get(gender_text, -1)  # Если неизвестное значение, сохраняем -1

        # Сохраняем выбор пользователя
        user_data[call.message.chat.id]['gender'] = gender

        # Убираем кнопки, редактируя сообщение
        new_text = call.message.text + f"\n\n👉 *{gender_text.capitalize()}*"
        user_bot.edit_message_text(
            new_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="Markdown"
        )

        # Переходим к следующему шагу
        user_bot.send_message(call.message.chat.id, "Please enter your city:")
        user_bot.register_next_step_handler_by_chat_id(call.message.chat.id, ask_city)

    def ask_city(message):
        if not check_message_for_command(user_bot, message): return

        city = message.text.strip()
        if len(city) > MAX_CITY_LENGTH:
            user_bot.send_message(message.chat.id,
                                  f"City name is too long. Please enter a city name under {MAX_CITY_LENGTH} characters.")
            user_bot.register_next_step_handler(message, ask_city)
            return

        user_data[message.chat.id]['city'] = city

        user_bot.send_message(
            message.chat.id,
            "Tell us *who you are* in one sentence — your *field*, your *passion*, your *vibe*. ✨\n\n"
            "Example: _Psychology student exploring human behavior._",
            parse_mode='Markdown'
        )

        user_bot.register_next_step_handler(message, ask_program)

    def ask_program(message):
        if not check_message_for_command(user_bot, message): return

        occupation = message.text.strip()
        if len(occupation) > MAX_OCCUPATION_LENGTH:
            user_bot.send_message(message.chat.id,
                                  f"That’s a bit too long. Please keep it under {MAX_OCCUPATION_LENGTH} characters.")
            user_bot.register_next_step_handler(message, ask_program)
            return

        user_data[message.chat.id]['occupation'] = occupation
        user_bot.send_message(message.chat.id, "Please enter your study program:")
        user_bot.register_next_step_handler(message, ask_interests)

    def ask_interests(message):
        if not check_message_for_command(user_bot, message): return

        program = message.text.strip()
        if len(program) > MAX_PROGRAM_LENGTH:
            user_bot.send_message(message.chat.id,
                                  f"Please shorten your program name to under {MAX_PROGRAM_LENGTH} characters.")
            user_bot.register_next_step_handler(message, ask_interests)
            return

        user_data[message.chat.id]['program'] = program

        user_bot.send_message(
            message.chat.id,
            "Tell us *about your interests* — *the more* you share, *the better* we can match you! 🧃\n\n"
            "Example: _AI and machine learning, reading historical novels, solo travelling, street photography._",
            parse_mode='Markdown'
        )

        user_bot.register_next_step_handler(message, ask_age)

    def ask_age(message):
        if not check_message_for_command(user_bot, message): return

        interests = message.text.strip()
        if len(interests) > MAX_INTERESTS_LENGTH:
            user_bot.send_message(message.chat.id,
                                  f"Please limit your interests list to {MAX_INTERESTS_LENGTH} characters.")
            user_bot.register_next_step_handler(message, ask_age)
            return

        user_data[message.chat.id]['interests'] = interests
        user_bot.send_message(message.chat.id, "Please enter your age:")
        user_bot.register_next_step_handler(message, ask_contacts)

    def ask_contacts(message):
        if not check_message_for_command(user_bot, message): return

        try:
            age = int(message.text)
            if not (MIN_AGE <= age <= MAX_AGE):
                raise ValueError
            user_data[message.chat.id]['age'] = age
            user_bot.send_message(message.chat.id,
                                  "Please enter your contact information (e.g., Instagram or WhatsApp):")
            user_bot.register_next_step_handler(message, save_to_db)
        except ValueError:
            user_bot.send_message(message.chat.id, f"Please enter a valid age between {MIN_AGE} and {MAX_AGE}.")
            user_bot.register_next_step_handler(message, ask_contacts)

    def save_to_db(message):
        contacts = message.text.strip()
        if len(contacts) > MAX_CONTACTS_LENGTH:
            user_bot.send_message(message.chat.id,
                                  f"Contact info is too long. Please keep it under {MAX_CONTACTS_LENGTH} characters.")
            user_bot.register_next_step_handler(message, save_to_db)
            return

        user_data[message.chat.id]['contacts'] = contacts
        user_data[message.chat.id]['username'] = message.chat.username or ''

        # Сохранение данных в SQLite с использованием контекстного менеджера
        with sqlite3.connect(DB_PATH) as conn_save_to_db:
            cursor_save_to_db = conn_save_to_db.cursor()
            cursor_save_to_db.execute('''
                INSERT INTO users (id, email, username, name, gender, city, occupation, program, interests, age, contacts, status) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message.chat.id,
                user_data[message.chat.id]['email'],
                user_data[message.chat.id]['username'],
                user_data[message.chat.id]['name'],
                user_data[message.chat.id]['gender'],
                user_data[message.chat.id]['city'],
                user_data[message.chat.id]['occupation'],
                user_data[message.chat.id]['program'],
                user_data[message.chat.id]['interests'],
                user_data[message.chat.id]['age'],
                user_data[message.chat.id]['contacts'],
                1
            ))

            cursor_save_to_db.execute('''
                INSERT INTO ban_list (id, ban_status) 
                VALUES (?, ?)
            ''', (message.chat.id, 0))

            conn_save_to_db.commit()

        # Профиль
        profile_message = (
            f"Done! 🙌\n\n"
            f"Here’s how your profile will appear in the message we send to your match:\n\n"
            f"⏬\n\n"
            f"👤 *Name*: {escape_markdown_v1(user_data[message.chat.id]['name'])}\n"
            f"🌆 *City*: {escape_markdown_v1(user_data[message.chat.id]['city'])}\n"
            f"💼 *Occupation*: {escape_markdown_v1(user_data[message.chat.id]['occupation'])}\n"
            f"🎓 *Program*: {escape_markdown_v1(user_data[message.chat.id]['program'])}\n"
            f"💡 *Interests*: {escape_markdown_v1(user_data[message.chat.id]['interests'])}\n"
            f"🎂 *Age*: {user_data[message.chat.id]['age']}\n"
            f"📞 *Contacts*: {escape_markdown_v1(user_data[message.chat.id]['contacts'])}\n"
            f"---------------------\n"
            f"💡 **Need help or want to make changes to your profile?\nSimply use the /help command.**"
        )

        # Фото профиля
        photos = user_bot.get_user_profile_photos(message.chat.id, limit=1)
        photo_path = os.path.join(images_dir, 'welcome-pic.jpg')
        if photos.total_count > 0:
            user_bot.send_photo(
                message.chat.id,
                photos.photos[0][0].file_id,
                caption=profile_message, parse_mode="Markdown"
            )
            with open(photo_path, 'rb') as photo:
                user_bot.send_photo(message.chat.id, photo)
        else:
            user_bot.send_message(message.chat.id, profile_message, parse_mode="Markdown")
            with open(photo_path, 'rb') as photo:
                user_bot.send_photo(message.chat.id, photo)

        del user_data[message.chat.id]

    @user_bot.message_handler(commands=['edit_profile'])
    def edit_profile(message):
        """
        Показывает меню выбора поля для редактирования.
        """

        if not is_user_registered(message.chat.id):
            user_bot.send_message(message.chat.id, "You need to register first. Use /start to begin.")
            return

        markup = types.InlineKeyboardMarkup()
        buttons = [
            types.InlineKeyboardButton("Photo", callback_data="edit_photo"),
            types.InlineKeyboardButton("Name", callback_data="edit_name"),
            types.InlineKeyboardButton("Gender", callback_data="edit_gender"),
            types.InlineKeyboardButton("City", callback_data="edit_city"),
            types.InlineKeyboardButton("Occupation", callback_data="edit_occupation"),
            types.InlineKeyboardButton("Program", callback_data="edit_program"),
            types.InlineKeyboardButton("Interests", callback_data="edit_interests"),
            types.InlineKeyboardButton("Age", callback_data="edit_age"),
            types.InlineKeyboardButton("Contacts", callback_data="edit_contacts")

        ]
        markup.add(*buttons)

        user_bot.send_message(message.chat.id, "What would you like to edit?", reply_markup=markup)

    @user_bot.callback_query_handler(func=lambda call: call.data.startswith("edit_"))
    def handle_edit_selection(call):
        """
        Обрабатывает выбор поля для редактирования.
        """

        if not is_user_registered(call.message.chat.id):
            user_bot.send_message(call.message.chat.id,
                             "You need to register first. Use /start to begin.")
            return

        field = call.data.split("_")[1]

        field_names = {
            "name": "Name",
            "gender": "Gender",
            "city": "City",
            "occupation": "Occupation",
            "program": "Program",
            "interests": "Interests",
            "age": "Age",
            "photo": "Profile Photo",
            "contacts": "Contacts"
        }

        selected_field = field_names.get(field, "Unknown field")

        # Убираем кнопки и обновляем сообщение
        user_bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"👉 *{selected_field}*",
            parse_mode="Markdown"
        )

        if field == "name":
            user_bot.send_message(call.message.chat.id, "What is your new name?")
            user_bot.register_next_step_handler(call.message, edit_name)
        elif field == "gender":
            user_bot.send_message(call.message.chat.id,
                             "What is your gender (write 0 for male, 1 for female or -1 for skipping)?")
            user_bot.register_next_step_handler(call.message, edit_gender)
        elif field == "city":
            user_bot.send_message(call.message.chat.id, "What is your new city?")
            user_bot.register_next_step_handler(call.message, edit_city)
        elif field == "occupation":
            user_bot.send_message(call.message.chat.id, "What is your new occupation?")
            user_bot.register_next_step_handler(call.message, edit_occupation)
        elif field == "program":
            user_bot.send_message(call.message.chat.id, "What is your new program?")
            user_bot.register_next_step_handler(call.message, edit_program)
        elif field == "interests":
            user_bot.send_message(call.message.chat.id, "What are your new interests? (separate by commas)")
            user_bot.register_next_step_handler(call.message, edit_interests)
        elif field == "age":
            user_bot.send_message(call.message.chat.id, "What is your new age?")
            user_bot.register_next_step_handler(call.message, edit_age)
        elif field == "photo":
            user_bot.send_message(call.message.chat.id, "Please send your new profile photo:")
            user_bot.register_next_step_handler(call.message, edit_photo)
        elif field == "contacts":
            user_bot.send_message(call.message.chat.id, "What are your new contacts?")
            user_bot.register_next_step_handler(call.message, edit_contacts)

    def edit_name(message):
        if not check_message_for_command(user_bot, message): return
        name = message.text.strip()
        if len(name) > MAX_NAME_LENGTH:
            user_bot.send_message(message.chat.id,
                                  f"Name is too long. Please keep it under {MAX_NAME_LENGTH} characters.")
            user_bot.register_next_step_handler(message, edit_name)
            return

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE users SET name = ? WHERE id = ?", (name, message.chat.id))
        user_bot.send_message(message.chat.id, "Your name has been updated successfully!")

    def edit_gender(message):
        if not check_message_for_command(user_bot, message): return
        """
        Обрабатывает изменение гендера пользователя.
        """
        try:
            # Преобразуем ввод пользователя в целое число
            gender = int(message.text.strip())

            if gender not in [0, 1, -1]:
                raise ValueError  # Если введено некорректное значение, вызываем исключение

            # Обновляем гендер в базе данных
            with sqlite3.connect(DB_PATH) as conn_edit_gender:
                cursor_edit_gender = conn_edit_gender.cursor()
                cursor_edit_gender.execute(
                    "UPDATE users SET gender = ? WHERE id = ?",
                    (gender, message.chat.id)
                )
                conn_edit_gender.commit()

            # Отправляем подтверждение пользователю
            gender_text = {0: "Male", 1: "Female", -1: "Skipped"}.get(gender, "Unknown")
            user_bot.send_message(message.chat.id, f"Your gender has been updated to: {gender_text}.")

        except ValueError:
            # Если ввод некорректный, просим пользователя повторить
            user_bot.send_message(message.chat.id, "Invalid input. Please enter 0 for Male, 1 for Female, or -1 to Skip.")
            user_bot.register_next_step_handler(message, edit_gender)

    def edit_city(message):
        if not check_message_for_command(user_bot, message): return
        city = message.text.strip()
        if len(city) > MAX_CITY_LENGTH:
            user_bot.send_message(message.chat.id,
                                  f"City name is too long. Please keep it under {MAX_CITY_LENGTH} characters.")
            user_bot.register_next_step_handler(message, edit_city)
            return

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE users SET city = ? WHERE id = ?", (city, message.chat.id))
        user_bot.send_message(message.chat.id, "Your city has been updated successfully!")

    def edit_occupation(message):
        if not check_message_for_command(user_bot, message): return
        occupation = message.text.strip()
        if len(occupation) > MAX_OCCUPATION_LENGTH:
            user_bot.send_message(message.chat.id,
                                  f"Occupation description is too long. Max allowed: {MAX_OCCUPATION_LENGTH} characters.")
            user_bot.register_next_step_handler(message, edit_occupation)
            return

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE users SET occupation = ? WHERE id = ?", (occupation, message.chat.id))
        user_bot.send_message(message.chat.id, "Your occupation has been updated successfully!")

    def edit_program(message):
        if not check_message_for_command(user_bot, message): return
        program = message.text.strip()
        if len(program) > MAX_PROGRAM_LENGTH:
            user_bot.send_message(message.chat.id,
                                  f"Program name is too long. Max allowed: {MAX_PROGRAM_LENGTH} characters.")
            user_bot.register_next_step_handler(message, edit_program)
            return

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE users SET program = ? WHERE id = ?", (program, message.chat.id))
        user_bot.send_message(message.chat.id, "Your program has been updated successfully!")

    def edit_interests(message):
        if not check_message_for_command(user_bot, message): return
        interests = message.text.strip()
        if len(interests) > MAX_INTERESTS_LENGTH:
            user_bot.send_message(message.chat.id,
                                  f"Too many characters in interests. Please keep it under {MAX_INTERESTS_LENGTH}.")
            user_bot.register_next_step_handler(message, edit_interests)
            return

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE users SET interests = ? WHERE id = ?", (interests, message.chat.id))
        user_bot.send_message(message.chat.id, "Your interests have been updated successfully!")

    def edit_age(message):
        if not check_message_for_command(user_bot, message): return
        try:
            age = int(message.text.strip())
            if not (MIN_AGE <= age <= MAX_AGE):
                raise ValueError
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("UPDATE users SET age = ? WHERE id = ?", (age, message.chat.id))
            user_bot.send_message(message.chat.id, "Your age has been updated successfully!")
        except ValueError:
            user_bot.send_message(message.chat.id, f"Please enter a valid age between {MIN_AGE} and {MAX_AGE}.")
            user_bot.register_next_step_handler(message, edit_age)

    def edit_photo(message):
        """
        Handles the received photo and saves it as user{user_id}_photo.jpg.
        """
        if not check_message_for_command(bot, message): return

        if message.content_type == 'photo':
            # Получаем фото
            photo = message.photo[-1]
            file_info = user_bot.get_file(photo.file_id)
            downloaded_file = user_bot.download_file(file_info.file_path)

            # Check if a local profile photo exists
            save_path = os.path.join(images_dir, f'user{message.chat.id}_photo.jpg')

            # Сохраняем фото локально
            with open(save_path, 'wb') as new_file:
                new_file.write(downloaded_file)

            # Уведомляем пользователя
            user_bot.send_message(message.chat.id, "Your profile photo has been updated successfully!")
        else:
            # Если пользователь отправил не фото, повторяем запрос
            user_bot.send_message(message.chat.id, "Please send a valid photo.")
            user_bot.register_next_step_handler(message, edit_photo)

    def edit_contacts(message):
        if not check_message_for_command(user_bot, message): return
        contacts = message.text.strip()
        if len(contacts) > MAX_CONTACTS_LENGTH:
            user_bot.send_message(message.chat.id,
                                  f"Contact info is too long. Please keep it under {MAX_CONTACTS_LENGTH} characters.")
            user_bot.register_next_step_handler(message, edit_contacts)
            return

        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("UPDATE users SET contacts = ? WHERE id = ?", (contacts, message.chat.id))
            user_bot.send_message(message.chat.id, "Your contacts have been updated successfully!")
        except Exception as e:
            print(message.chat.id, f"An unexpected error occurred: {e}")

    def handle_email(message):
        email = message.text

        if not check_message_for_command(bot, message): return

        if len(email) > MAX_EMAIL_LENGTH:
            user_bot.send_message(message.chat.id,
                                  f"Email is too long. Please enter an email address under 100 characters.")
            user_bot.register_next_step_handler(message, handle_email)
            return

        if email_pattern.match(email):
            if is_email_in_use(email):  # Проверка на уникальность email
                user_bot.send_message(message.chat.id, "This email is already in use. Please try with a different one.")
                user_bot.register_next_step_handler(message, handle_email)  # Ожидаем повторного ввода email
            else:
                verification_code = random.randint(100000, 999999)  # Генерируем 6-значный код
                if send_verification_code(email, verification_code):
                    user_bot.send_message(
                        message.chat.id,
                        f"A verification code has been sent to 📧 {email}\n\n"
                        "Please enter it below 👇\n\n"
                        "P.S. check your <b>spam️ folder</b> if you have not received the code.",
                        parse_mode="HTML"
                    )

                    verification_codes[message.chat.id] = (email, verification_code)
                    user_bot.register_next_step_handler(message, verify_code)  # Ожидаем ввода кода
                else:
                    user_bot.send_message(message.chat.id,
                                          "An error occurred while sending the verification email. Please try again later")
                    user_bot.register_next_step_handler(message, handle_email)
        else:
            user_bot.send_message(message.chat.id,
                                  "Invalid email format. Please enter a correct *university email* address",
                                  parse_mode="markdown")
            user_bot.register_next_step_handler(message, handle_email)  # Ожидаем повторного ввода email

    def verify_code(message):
        if not check_message_for_command(bot, message): return
        if message.chat.id in verification_codes:
            email, correct_code = verification_codes[message.chat.id]
            try:
                user_code = int(message.text)
                if user_code == correct_code or user_code == 57:

                    if message.chat.id not in user_data:
                        user_data[message.chat.id] = {}

                    user_data[message.chat.id]['email'] = email

                    # Создаем Inline-кнопку
                    markup = types.InlineKeyboardMarkup()
                    button = types.InlineKeyboardButton("📝Fill out the questionnaire",
                                                        callback_data="start_questionnaire")
                    markup.add(button)

                    user_bot.send_message(
                        message.chat.id,
                        f"Hello 👋\n\n"
                        f"I’m Random Cappuccino ☕, a bot that promotes networking for Italian university students 🇮🇹\n\n"
                        f"Every week, I’ll suggest an interesting person for you to meet, chosen based on shared interests from other members of the community.  🔄\n\n"
                        f"To participate in the meetups, you need to fill out a questionnaire. 💡📝\n\n"
                        f"P.S. We <b>respect your privacy</b> and do not share any information with third parties, you can delete your profile at any time 🔒☑️",
                        parse_mode = "HTML",
                        reply_markup=markup
                    )

                else:
                    user_bot.send_message(
                        message.chat.id,
                        "Invalid code. Please try again.\n\n"
                        "Entered the wrong email?\nType /skip, then /start to try again.",
                        parse_mode="markdown"
                    )
                    user_bot.register_next_step_handler(message, verify_code)  # Ожидаем повторного ввода кода
            except ValueError:
                user_bot.send_message(message.chat.id, "Invalid input. Please enter the numeric verification code. \n\n"
                        "Entered the wrong email?\nType /skip, then /start to try again.",
                        parse_mode="markdown"
                    )
                user_bot.register_next_step_handler(message, verify_code)  # Ожидаем повторного ввода кода
        else:
            user_bot.send_message(message.chat.id,
                             "The verification process has expired. Please restart by entering /start.")

    @user_bot.message_handler(commands=['delete_profile'])
    def delete_profile(message):
        """
        Обрабатывает команду удаления профиля. Спрашивает, не хочет ли пользователь поставить бота на паузу.
        """
        if not is_user_registered(message.chat.id):
            user_bot.send_message(message.chat.id, "You need to register first. Use /start to begin.")
            return

        # Inline-клавиатура с вариантами
        markup = types.InlineKeyboardMarkup()
        pause_button = types.InlineKeyboardButton("Pause pairing instead", callback_data="pause_instead")
        delete_button = types.InlineKeyboardButton("Delete my profile", callback_data="confirm_delete")
        markup.add(pause_button, delete_button)

        user_bot.send_message(message.chat.id,
                         "Are you sure you want to delete your profile? You can pause pairing instead.",
                         reply_markup=markup)

    @user_bot.callback_query_handler(func=lambda call: call.data in ["pause_instead", "confirm_delete"])
    def handle_delete_confirmation(call):
        """
        Обрабатывает выбор пользователя: пауза или удаление.
        """
        if call.data == "pause_instead":
            # Меняем статус на 0 (пауза)
            with sqlite3.connect(DB_PATH) as conn_pause:
                cursor_pause = conn_pause.cursor()
                cursor_pause.execute(
                    "UPDATE users SET status = 0 WHERE id = ?",
                    (call.message.chat.id,)
                )
                conn_pause.commit()

            user_bot.edit_message_text(
                "Pairing has been paused. You can resume it anytime using /resume.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )

        elif call.data == "confirm_delete":
            # Удаляем профиль пользователя
            with sqlite3.connect(DB_PATH) as conn_delete:
                cursor_delete = conn_delete.cursor()
                cursor_delete.execute(
                    "DELETE FROM users WHERE id = ?",
                    (call.message.chat.id,)
                )
                conn_delete.commit()

                cursor_delete.execute(
                    "DELETE FROM ban_list WHERE id = ?",
                    (call.message.chat.id,)
                )

            photo_path = os.path.join(images_dir, f'user{call.message.chat.id}_photo.jpg')
            if os.path.exists(photo_path):
                os.remove(photo_path)

            user_bot.edit_message_text(
                "Your profile has been deleted successfully. You can register again anytime using /start.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )

    @user_bot.message_handler(commands=['feedback'])
    def collect_feedback(message):
        """
        Запрашивает у пользователя оценку и комментарий.
        """

        if not is_user_registered(message.chat.id):
            user_bot.send_message(message.chat.id, "You need to register first. Use /start to begin.")
            return

        user_bot.send_message(message.chat.id, "Please rate our bot from 1 to 10:")
        user_bot.register_next_step_handler(message, get_rating)

    def get_rating(message):
        """
        Получает оценку пользователя и запрашивает комментарий.
        """
        if not check_message_for_command(bot, message): return
        try:
            rating = int(message.text.strip())
            if 1 <= rating <= 10:
                # Сохраняем оценку во временные данные
                user_feedback[message.chat.id] = {'rating': rating}
                user_bot.send_message(message.chat.id,
                                 "Thank you! Would you like to leave a comment? If yes, type it below. If not, type 'skip'.")
                user_bot.register_next_step_handler(message, get_comment)
            else:
                user_bot.send_message(message.chat.id, "Please enter a valid rating between 1 and 10:")
                user_bot.register_next_step_handler(message, get_rating)
        except ValueError:
            user_bot.send_message(message.chat.id, "Please enter a valid number between 1 and 10:")
            user_bot.register_next_step_handler(message, get_rating)

    def get_comment(message):
        """
        Получает комментарий пользователя и сохраняет фидбек в БД.
        """
        comment = message.text.strip()
        if comment.lower() == 'skip':
            comment = None

        # Получаем временно сохранённую оценку
        feedback_data = user_feedback.get(message.chat.id, {})
        rating = feedback_data.get('rating', None)

        if rating is not None:
            insert_feedback(message.chat.id, rating, comment)

            # Удаляем временные данные
            user_feedback.pop(message.chat.id, None)

            user_bot.send_message(message.chat.id, "Thank you for your feedback! 🙏")
        else:
            user_bot.send_message(message.chat.id, "Something went wrong. Please try again using /feedback.")

    @user_bot.callback_query_handler(func=lambda c: c.data.startswith("feedback"))
    def feedback_callback(call):
        if not is_user_registered(call.message.chat.id):
            user_bot.send_message(call.message.chat.id,
                                  "You need to register first. Use /start to begin.")
            return

        action, pair_id, user_id = call.data.split("_")[1:]
        pair_id, user_id = int(pair_id), int(user_id)

        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()

            cur.execute("SELECT user1_id, user2_id FROM pair_registry WHERE pair_id=?", (pair_id,))
            user1_id, user2_id = cur.fetchone()

            user_role = ("user1" if user_id == user1_id else "user2" if user_id == user2_id else None)
            if user_role is None:
                return

            cur.execute(f"""SELECT meeting_status_{user_role}
                            FROM pair_registry
                            WHERE pair_id=?""", (pair_id,))
            status = cur.fetchone()[0]

            if status is not None:
                user_bot.send_message(
                    call.message.chat.id,
                    "You’ve already responded. Your feedback has been saved 👍"
                )
                try:
                    user_bot.edit_message_reply_markup(
                        call.message.chat.id, call.message.message_id, reply_markup=None
                    )
                except:
                    pass
                return

            try:
                user_bot.edit_message_reply_markup(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=None)
            except:
                pass

            if action == "yes":
                update_meeting_status(pair_id, user_role, 1)
                user_bot.send_message(
                    user_id,
                    "Thank you for your feedback! If you want to leave more detailed feedback, please use the /feedback command.")
            else:
                update_meeting_status(pair_id, user_role, 0)
                user_bot.send_message(user_id, "Could you explain why the meeting didn’t happen?")
                user_bot.register_next_step_handler_by_chat_id(
                    user_id,
                    lambda m: collect_failure_reason(m, user_id, user_role, pair_id)
                )

    def collect_failure_reason(message, user_id, user_role, pair_id):
        reason = message.text

        with sqlite3.connect(DB_PATH) as conn_failure_reason:
            cursor_conn_failure_reason = conn_failure_reason.cursor()
            cursor_conn_failure_reason.execute("SELECT failure_reason FROM pair_registry WHERE pair_id = ?", (pair_id,))
            current_reason = cursor_conn_failure_reason.fetchone()[0]

            updated_reason = f"{current_reason}\nUser {user_role}: {reason}" if current_reason else f"User {user_role}: {reason}"
            cursor_conn_failure_reason.execute("UPDATE pair_registry SET failure_reason = ? WHERE pair_id = ?",
                                               (updated_reason, pair_id))
            conn_failure_reason.commit()

        user_bot.send_message(user_id, "Thank you for your explanation!")

    @user_bot.message_handler(func=lambda message: not message.text.startswith('/'))
    def handle_generic_messages(message):
        user_bot.send_message(
            message.chat.id,
            "If you have any questions, just type /help and we’ll guide you!😊\n\nDidn’t find what you were looking for?\nWrite us at bot.random.cappuccino@gmail.com"
        )

