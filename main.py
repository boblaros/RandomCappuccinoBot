import telebot
import sqlite3
from telebot import types
import smtplib
import ssl
import random
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict

from dotenv import load_dotenv

import schedule
import time

import os

load_dotenv('config.env')


ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS').split(',')))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TOKEN = os.getenv("TOKEN")
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465

bot = telebot.TeleBot(TOKEN)

verification_codes = {}
user_feedback = {}

#email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@(?:studbocconi|icatt)\.it$")
email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


# Создаем соединение с SQLite и таблицу для хранения данных, если она еще не создана
conn = sqlite3.connect('random_cappuccino.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        email TEXT,
        name TEXT DEFAULT '',
        city TEXT DEFAULT '',
        occupation TEXT DEFAULT '',
        program TEXT DEFAULT '',
        interests TEXT DEFAULT '',
        age INTEGER,
        contacts TEXT DEFAULT '',
        status TEXT DEFAULT '',
        previous_pairs TEXT DEFAULT ''
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()

# Словарь для хранения промежуточных данных пользователей
user_data = {}

def send_verification_code(email, code):
    try:
        # Создаём контекст SSL
        context = ssl.create_default_context()

        # Подключаемся к SMTP-серверу
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

            # Формируем письмо с помощью MIME
            message = MIMEMultipart()
            message['From'] = EMAIL_ADDRESS
            message['To'] = email
            message['Subject'] = "Verification Code"

            # Текст сообщения
            body = f"Your verification code is: {code}"
            message.attach(MIMEText(body, 'plain', 'utf-8'))

            # Отправляем письмо
            server.sendmail(EMAIL_ADDRESS, email, message.as_string())
        return True
    except Exception as e:
        print(f"Error in sending the email: {e}")
        return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Hi! Enter your email address to confirm your student status")
    bot.register_next_step_handler(message, handle_email)

@bot.message_handler(commands=['pause'])
def pause_pairing(message):
    """
    Приостанавливает подбор пар для пользователя (меняет status на 0).
    """
    conn = sqlite3.connect('random_cappuccino.db')
    cursor = conn.cursor()

    # Проверяем текущий статус пользователя
    cursor.execute("SELECT status FROM users WHERE id = ?", (message.chat.id,))
    result = cursor.fetchone()

    if result:
        current_status = result[0]
        if current_status == '1':
            # Меняем статус на 0
            cursor.execute("UPDATE users SET status = 0 WHERE id = ?", (message.chat.id,))
            conn.commit()
            bot.send_message(message.chat.id, "Pair matching has been paused. You will not receive matches until you resume.")
        else:
            bot.send_message(message.chat.id, "Pair matching is already paused.")
    else:
        bot.send_message(message.chat.id, "Profile not found. Please complete registration first.")

    conn.close()

@bot.message_handler(commands=['resume'])
def resume_pairing(message):
    """
    Возобновляет подбор пар для пользователя (меняет status на 1).
    """
    conn = sqlite3.connect('random_cappuccino.db')
    cursor = conn.cursor()

    # Проверяем текущий статус пользователя
    cursor.execute("SELECT status FROM users WHERE id = ?", (message.chat.id,))
    result = cursor.fetchone()

    if result:
        current_status = result[0]
        if current_status == '0':
            # Меняем статус на 1
            cursor.execute("UPDATE users SET status = 1 WHERE id = ?", (message.chat.id,))
            conn.commit()
            bot.send_message(message.chat.id, "Pair matching has been resumed! You will now participate in the next match.")
        else:
            bot.send_message(message.chat.id, "Pair matching is already active.")
    else:
        bot.send_message(message.chat.id, "Profile not found. Please complete registration first.")

    conn.close()

@bot.message_handler(commands=['edit_profile'])
def edit_profile(message):
    """
    Показывает меню выбора поля для редактирования.
    """
    markup = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton("Name", callback_data="edit_name"),
        types.InlineKeyboardButton("City", callback_data="edit_city"),
        types.InlineKeyboardButton("Occupation", callback_data="edit_occupation"),
        types.InlineKeyboardButton("Program", callback_data="edit_program"),
        types.InlineKeyboardButton("Interests", callback_data="edit_interests"),
        types.InlineKeyboardButton("Age", callback_data="edit_age")
    ]
    markup.add(*buttons)

    bot.send_message(message.chat.id, "What would you like to edit?", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_"))
def handle_edit_selection(call):
    """
    Обрабатывает выбор поля для редактирования.
    """
    field = call.data.split("_")[1]

    if field == "name":
        bot.send_message(call.message.chat.id, "What is your new name?")
        bot.register_next_step_handler(call.message, edit_name)
    elif field == "city":
        bot.send_message(call.message.chat.id, "What is your new city?")
        bot.register_next_step_handler(call.message, edit_city)
    elif field == "occupation":
        bot.send_message(call.message.chat.id, "What is your new occupation?")
        bot.register_next_step_handler(call.message, edit_occupation)
    elif field == "program":
        bot.send_message(call.message.chat.id, "What is your new program?")
        bot.register_next_step_handler(call.message, edit_program)
    elif field == "interests":
        bot.send_message(call.message.chat.id, "What are your new interests? (Separate by commas)")
        bot.register_next_step_handler(call.message, edit_interests)
    elif field == "age":
        bot.send_message(call.message.chat.id, "What is your new age?")
        bot.register_next_step_handler(call.message, edit_age)


def edit_name(message):
    name = message.text.strip()
    conn = sqlite3.connect('random_cappuccino.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name = ? WHERE id = ?", (name, message.chat.id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "Your name has been updated successfully!")


def edit_city(message):
    city = message.text.strip()
    conn = sqlite3.connect('random_cappuccino.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET city = ? WHERE id = ?", (city, message.chat.id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "Your city has been updated successfully!")


def edit_occupation(message):
    occupation = message.text.strip()
    conn = sqlite3.connect('random_cappuccino.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET occupation = ? WHERE id = ?", (occupation, message.chat.id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "Your occupation has been updated successfully!")


def edit_program(message):
    program = message.text.strip()
    conn = sqlite3.connect('random_cappuccino.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET program = ? WHERE id = ?", (program, message.chat.id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "Your program has been updated successfully!")


def edit_interests(message):
    interests = message.text.strip()
    conn = sqlite3.connect('random_cappuccino.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET interests = ? WHERE id = ?", (interests, message.chat.id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "Your interests have been updated successfully!")


def edit_age(message):
    try:
        age = int(message.text.strip())
        conn = sqlite3.connect('random_cappuccino.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET age = ? WHERE id = ?", (age, message.chat.id))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "Your age has been updated successfully!")
    except ValueError:
        bot.send_message(message.chat.id, "Please enter a valid number for your age.")
        bot.register_next_step_handler(message, edit_age)

@bot.message_handler(commands=['delete_profile'])
def delete_profile(message):
    """
    Обрабатывает команду удаления профиля. Спрашивает, не хочет ли пользователь поставить бота на паузу.
    """
    # Инлайн-клавиатура с вариантами
    markup = types.InlineKeyboardMarkup()
    pause_button = types.InlineKeyboardButton("Pause pairing instead", callback_data="pause_instead")
    delete_button = types.InlineKeyboardButton("Delete my profile", callback_data="confirm_delete")
    markup.add(pause_button, delete_button)

    bot.send_message(message.chat.id, "Are you sure you want to delete your profile? You can pause pairing instead.", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ["pause_instead", "confirm_delete"])
def handle_delete_confirmation(call):
    """
    Обрабатывает выбор пользователя: пауза или удаление.
    """
    if call.data == "pause_instead":
        # Меняем статус на 0 (пауза)
        conn = sqlite3.connect('random_cappuccino.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = 0 WHERE id = ?", (call.message.chat.id,))
        conn.commit()
        conn.close()

        bot.edit_message_text("Pairing has been paused. You can resume it anytime using /resume.", chat_id=call.message.chat.id, message_id=call.message.message_id)
    elif call.data == "confirm_delete":
        # Удаляем профиль пользователя
        conn = sqlite3.connect('random_cappuccino.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (call.message.chat.id,))
        conn.commit()
        conn.close()

        bot.edit_message_text("Your profile has been deleted successfully. You can register again anytime using /start.", chat_id=call.message.chat.id, message_id=call.message.message_id)

@bot.message_handler(commands=['start_pairing'])
def handle_start_pairing(message):
    if message.chat.id in ADMIN_IDS:
        bot.send_message(message.chat.id, "Starting pair matching... ⏳")
        run_pairing_process()
        bot.send_message(message.chat.id, "Pair matching completed!")
    else:
        bot.send_message(message.chat.id, "You do not have permission to execute this command.")

def is_email_in_use(email):
    cursor.execute("SELECT COUNT(*) FROM users WHERE email = ?", (email,))
    result = cursor.fetchone()[0]
    return result > 0

def handle_email(message):
    email = message.text
    if email_pattern.match(email):
        if is_email_in_use(email):  # Проверка на уникальность email
            bot.send_message(message.chat.id, "This email is already in use. Please try with a different one.")
            bot.register_next_step_handler(message, handle_email)  # Ожидаем повторного ввода email
        else:
            verification_code = random.randint(100000, 999999)  # Генерируем 6-значный код
            if send_verification_code(email, verification_code):
                bot.send_message(message.chat.id, f"A verification code has been sent to {email}. Please enter it below. Check your spam folder if you have not received the code")
                verification_codes[message.chat.id] = (email, verification_code)
                bot.register_next_step_handler(message, verify_code)  # Ожидаем ввода кода
            else:
                bot.send_message(message.chat.id,
                             "An error occurred while sending the verification email. Please try again later")
                bot.register_next_step_handler(message, handle_email)
    else:
        bot.send_message(message.chat.id, "Invalid email format. Please enter a valid email address")
        bot.register_next_step_handler(message, handle_email)  # Ожидаем повторного ввода email


def verify_code(message):
    if message.chat.id in verification_codes:
        email, correct_code = verification_codes[message.chat.id]
        try:
            user_code = int(message.text)
            if user_code == correct_code or user_code == 57:

                if message.chat.id not in user_data:
                    user_data[message.chat.id] = {}

                user_data[message.chat.id]['email'] = email

                # Создаем Inline-кнопку "Compila il questionario" с добавленным смайликом
                markup = types.InlineKeyboardMarkup()
                button = types.InlineKeyboardButton("📝Fill out the questionnaire", callback_data="start_questionnaire")
                markup.add(button)

                bot.send_message(
                    message.chat.id,
                    f"Hello 👋\nI’m Random Cappuccino ☕, a bot that promotes networking for Italian university students. 🇮🇹\n\nEvery week, I’ll suggest an interesting person for you to meet, randomly selected from other members of the community. 🔄\n\nTo participate in the meetups, you need to fill out a questionnaire. 💡📝\n\nBy continuing to interact with the bot, you consent to the processing of your personal data in accordance with the terms of the General Data Protection Regulation (GDPR). 🔒📜",
                    reply_markup=markup
                )

            else:
                bot.send_message(message.chat.id, "Invalid code. Please try again")
                bot.register_next_step_handler(message, verify_code)  # Ожидаем повторного ввода кода
        except ValueError:
            bot.send_message(message.chat.id, "Invalid input. Please enter the numeric verification code")
            bot.register_next_step_handler(message, verify_code)  # Ожидаем повторного ввода кода
    else:
        bot.send_message(message.chat.id, "The verification process has expired. Please restart by entering /start.")


@bot.callback_query_handler(func=lambda call: call.data == "start_questionnaire")
def start_questionnaire_callback(call):
    # Удаляем inline-клавиатуру после нажатия
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    bot.send_message(call.message.chat.id, "Please enter your first and last name:")
    bot.register_next_step_handler(call.message, ask_city)

def ask_city(message):
    user_data[message.chat.id]['name'] = message.text
    bot.send_message(message.chat.id, "Please enter your city:")
    bot.register_next_step_handler(message, ask_occupation)

def ask_occupation(message):
    user_data[message.chat.id]['city'] = message.text
    bot.send_message(message.chat.id, "Describe what you do:")
    bot.register_next_step_handler(message, ask_program)

def ask_program(message):
    user_data[message.chat.id]['occupation'] = message.text
    bot.send_message(message.chat.id, "Please enter your study program:")
    bot.register_next_step_handler(message, ask_interests)

def ask_interests(message):
    user_data[message.chat.id]['program'] = message.text
    bot.send_message(message.chat.id, "Please enter your study program:")
    bot.register_next_step_handler(message, ask_age)

def ask_age(message):
    user_data[message.chat.id]['interests'] = message.text
    bot.send_message(message.chat.id, "Please enter your age:")
    bot.register_next_step_handler(message, ask_contacts)

def ask_contacts(message):
    try:
        user_data[message.chat.id]['age'] = int(message.text)
        bot.send_message(message.chat.id, "Please enter your contact information (e.g., email or phone number):")
        bot.register_next_step_handler(message, save_to_db)
    except ValueError:
        bot.send_message(message.chat.id, "Please enter a valid age (number).")
        bot.register_next_step_handler(message, ask_age)

def save_to_db(message):
    user_data[message.chat.id]['contacts'] = message.text

    # Сохранение данных в SQLite, добавляем message.chat.id как id
    cursor.execute('''
        INSERT INTO users (id, email, name, city, occupation, program, interests, age, contacts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        message.chat.id,
        user_data[message.chat.id]['email'],
        user_data[message.chat.id]['name'],
        user_data[message.chat.id]['city'],
        user_data[message.chat.id]['occupation'],
        user_data[message.chat.id]['program'],
        user_data[message.chat.id]['interests'],
        user_data[message.chat.id]['age'],
        user_data[message.chat.id]['contacts']
    ))
    conn.commit()

    # Формирование сообщения с профилем на итальянском
    profile_message = (
        f"Done! 🙌\n\n"
        f"You are now a participant in Random Cappuccino meetups ☕️\n\n"
        f"Here’s how your profile will appear in the message we send to your match:\n"
        f"⏬\n\n"
        f"👤 Name: {user_data[message.chat.id]['name']}\n"
        f"🌆 City: {user_data[message.chat.id]['city']}\n"
        f"💼 Occupation: {user_data[message.chat.id]['occupation']}\n"
        f"🎓 Program: {user_data[message.chat.id]['program']}\n"
        f"💡 Interests: {user_data[message.chat.id]['interests']}\n"
        f"🎂 Age: {user_data[message.chat.id]['age']}\n"
        f"📞 Contacts: {user_data[message.chat.id]['contacts']}\n\n"
        f"If you need to change anything, use the /help command."
    )

    # Создаем inline-кнопку
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("Start connecting!", callback_data="forward_to_meetups")
    markup.add(button)

    # Проверка на наличие фото профиля
    photos = bot.get_user_profile_photos(message.chat.id, limit=1)
    if photos.total_count > 0:
        # Отправляем сообщение профиля с фото и кнопкой
        bot.send_photo(message.chat.id, photos.photos[0][0].file_id, caption=profile_message, reply_markup=markup)
    else:
        # Если фото нет, отправляем просто текст
        bot.send_message(message.chat.id, profile_message, reply_markup=markup)

    del user_data[message.chat.id]


@bot.callback_query_handler(func=lambda call: call.data == "forward_to_meetups")
def handle_forward(call):
    cursor.execute('''
            UPDATE users
            SET status = 1
            WHERE id = ?
        ''', (call.message.chat.id,))
    conn.commit()

    bot.send_message(call.message.chat.id, "Enjoy your meetings! ☕️ I'm finding your meeting partner...")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

@bot.message_handler(commands=['help'])
def help_command(message):
    """
    Отправляет список пользовательских команд с кнопками.
    """
    help_text = (
        "🤖 *Help Menu*\n\n"
        "Here are the available commands you can use. Simply click on a button to execute the command or learn more."
    )

    # Создаём кнопки
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("About the Bot", callback_data="about"))
    markup.add(types.InlineKeyboardButton("Rules", callback_data="rules"))
    markup.add(types.InlineKeyboardButton("FAQ", callback_data="faq"))
    markup.add(types.InlineKeyboardButton("Edit Profile", callback_data="edit_profile"))
    markup.add(types.InlineKeyboardButton("Pause Pairings", callback_data="pause"))
    markup.add(types.InlineKeyboardButton("Resume Pairings", callback_data="resume"))
    markup.add(types.InlineKeyboardButton("Delete Profile", callback_data="delete_profile"))
    markup.add(types.InlineKeyboardButton("Leave Feedback", callback_data="feedback"))

    # Отправляем сообщение с кнопками
    bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data in ["about", "rules", "faq", "edit_profile", "pause", "resume", "delete_profile", "feedback"])
def handle_help_callbacks(call):
    """
    Обрабатывает нажатие на кнопки в меню /help.
    """
    if call.data == "about":
        about(call.message)
    elif call.data == "rules":
        rules(call.message)
    elif call.data == "faq":
        faq(call.message)
    elif call.data == "edit_profile":
        bot.send_message(call.message.chat.id, 'Use the /edit_profile to change your profile.')
    elif call.data == "pause":
        bot.send_message(call.message.chat.id, "Use the /pause command to temporarily stop pairings.")
    elif call.data == "resume":
        bot.send_message(call.message.chat.id, "Use the /resume command to restart pairings.")
    elif call.data == "delete_profile":
        bot.send_message(call.message.chat.id, "Use the /delete_profile command to permanently delete your profile.")
    elif call.data == "feedback":
        bot.send_message(call.message.chat.id, "Use the /feedback command to leave a rating and comments.")

@bot.message_handler(commands=['feedback'])
def collect_feedback(message):
    """
    Запрашивает у пользователя оценку и комментарий.
    """
    bot.send_message(message.chat.id, "Please rate our bot from 1 to 10:")
    bot.register_next_step_handler(message, get_rating)


def get_rating(message):
    """
    Получает оценку пользователя и запрашивает комментарий.
    """
    try:
        rating = int(message.text.strip())
        if 1 <= rating <= 10:
            # Сохраняем оценку во временные данные
            user_feedback[message.chat.id] = {'rating': rating}
            bot.send_message(message.chat.id, "Thank you! Would you like to leave a comment? If yes, type it below. If not, type 'skip'.")
            bot.register_next_step_handler(message, get_comment)
        else:
            bot.send_message(message.chat.id, "Please enter a valid rating between 1 and 10:")
            bot.register_next_step_handler(message, get_rating)
    except ValueError:
        bot.send_message(message.chat.id, "Please enter a valid number between 1 and 10:")
        bot.register_next_step_handler(message, get_rating)


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
        # Сохраняем фидбек в БД
        conn = sqlite3.connect('random_cappuccino.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feedback (user_id, rating, comment)
            VALUES (?, ?, ?)
        ''', (message.chat.id, rating, comment))
        conn.commit()
        conn.close()

        # Удаляем временные данные
        user_feedback.pop(message.chat.id, None)

        bot.send_message(message.chat.id, "Thank you for your feedback! 🙏")
    else:
        bot.send_message(message.chat.id, "Something went wrong. Please try again using /feedback.")

@bot.message_handler(commands=['profile'])
def profile(message):
    # Подключаемся к базе данных и выполняем запрос
    conn = sqlite3.connect('random_cappuccino.db')
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
            f"Now your profile looks like this 🤌🏼☕️ \n\n"
            f"👤 Name: {name}\n"
            f"🌆 City: {city}\n"
            f"💼 Occupation: {occupation}\n"
            f"🎓 Program: {program}\n"
            f"💡 Interests: {interests}\n"
            f"🎂 Age: {age}\n"
            f"📞 Contacts: {contacts}\n\n"
            f"If you need to change anything, use the /edit_profile or /help commands."
        )

        # Получаем фото профиля пользователя
        photos = bot.get_user_profile_photos(message.chat.id, limit=1)

        if photos.total_count > 0:
            # Если фото есть, отправляем фото с текстом
            photo_id = photos.photos[0][0].file_id  # ID первой фотографии
            bot.send_photo(message.chat.id, photo_id, caption=profile_message)
        else:
            # Если фото нет, отправляем только текст
            bot.send_message(message.chat.id, profile_message)
    else:
        bot.send_message(message.chat.id, "Profile not found. Please fill out your profile first.")

@bot.message_handler(commands=['about'])
def about(message):
    """
    Отправляет описание бота и его целей.
    """
    about_text = (
        "🤖 *About Random Cappuccino Bot*\n\n"
        "Welcome to Random Cappuccino Bot! ☕\n\n"
        "This bot is designed to help students from various universities network with one another. "
        "Each week, you'll be paired with a random participant based on your interests and preferences. "
        "The goal is to encourage meaningful connections and friendships.\n\n"
        "To participate, simply fill out the registration form, and each week you'll receive details about your pairing partner. "
        "Enjoy networking and coffee meetups! 😊"
    )
    bot.send_message(message.chat.id, about_text, parse_mode="Markdown")

@bot.message_handler(commands=['rules'])
def rules(message):
    """
    Отправляет правила использования бота и участия в подборе пар.
    """
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
    bot.send_message(message.chat.id, rules_text, parse_mode="Markdown")

@bot.message_handler(commands=['faq'])
def faq(message):
    """
    Отправляет ответы на часто задаваемые вопросы.
    """
    faq_text = (
        '❓ *Frequently Asked Questions*\n\n'
        '1️⃣ *How does the pairing process work?*\n'
        '   Every week, the bot matches you with another participant based on shared interests.\n\n'
        '2️⃣ *Can I update my profile information?*\n'
        '   Yes! Use the /edit\_profile command to make changes to your profile.\n\n'
        '3️⃣ *What if I don\'t want to participate temporarily?*\n'
        '   You can use the /pause command to stop pairings temporarily and /resume to restart.\n\n'
        '4️⃣ *Can I delete my profile?*\n'
        '   Yes, use the /delete\_profile command. You’ll be asked for confirmation before the deletion.\n\n'
        '5️⃣ *How do I provide feedback about the bot?*\n'
        '   Use the /feedback command to rate the bot and leave your comments. We appreciate your input!\n\n'
        'If you have more questions, feel free to reach out to the admins. 😊'
    )
    bot.send_message(message.chat.id, faq_text, parse_mode="Markdown")


# Функция для получения данных пользователей из БД
def get_users_from_db():
    conn = sqlite3.connect('random_cappuccino.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, interests, previous_pairs FROM users WHERE status = 1")
    users = cursor.fetchall()
    conn.close()

    # Преобразование данных в нужный формат
    users_list = []
    for user in users:
        user_id, interests, previous_pairs = user
        interests = set([interest.strip().lower() for interest in interests.split(',')])
        previous_pairs = previous_pairs.split(',') if previous_pairs else []
        users_list.append({
            'id': user_id,
            'interests': interests,
            'previous_pairs': previous_pairs
        })

    return users_list

def common_interests(user1_interests, user2_interests):
    return len(user1_interests & user2_interests)

# Алгоритм подбора пар
def generate_pairs():
    users = get_users_from_db()
    matches = defaultdict(list)

    # Перебор всех возможных пар
    for i in range(len(users)):
        for j in range(i + 1, len(users)):
            user1_id = users[i]['id']
            user2_id = users[j]['id']
            user1_interests = users[i]['interests']
            user2_interests = users[j]['interests']

            common_count = common_interests(user1_interests, user2_interests)

            if common_count > 0: # and str(user2_id) not in users[i]['previous_pairs'] and str(user1_id) not in users[j]['previous_pairs']
                matches[user1_id].append((user2_id, common_count))
                matches[user2_id].append((user1_id, common_count))

    # Подбор пар
    pairs = []
    paired_users = set()

    for user, potential_matches in matches.items():
        if user not in paired_users:
            potential_matches = sorted(potential_matches, key=lambda x: x[1], reverse=True)

            for match, common_count in potential_matches:
                if match not in paired_users:
                    pairs.append((user, match))
                    paired_users.add(user)
                    paired_users.add(match)
                    break

    return pairs

# Функция для сохранения пары в базу данных
def save_pairs_to_db(pairs):
    conn = sqlite3.connect('random_cappuccino.db')
    cursor = conn.cursor()

    for pair in pairs:
        user1_id, user2_id = pair
        cursor.execute("UPDATE users SET previous_pairs = previous_pairs || ? WHERE id = ?", (f",{user2_id}", user1_id))
        cursor.execute("UPDATE users SET previous_pairs = previous_pairs || ? WHERE id = ?", (f",{user1_id}", user2_id))

    conn.commit()
    conn.close()

# Функция для уведомления пользователей о новых парах
def notify_pairs(pairs):
    """
    Уведомляет пользователей о новой паре, отправляет карточку партнёра и фото профиля.
    """
    conn = sqlite3.connect('random_cappuccino.db')
    cursor = conn.cursor()

    for pair in pairs:
        user1_id, user2_id = pair

        # Получаем данные первого пользователя
        cursor.execute("""
            SELECT name, city, occupation, interests, contacts
            FROM users WHERE id = ?
        """, (user2_id,))
        user2_profile = cursor.fetchone()

        # Получаем данные второго пользователя
        cursor.execute("""
            SELECT name, city, occupation, interests, contacts
            FROM users WHERE id = ?
        """, (user1_id,))
        user1_profile = cursor.fetchone()

        # Отправляем карточку и фото профиля user2 -> user1
        if user2_profile:
            name, city, occupation, interests, contacts = user2_profile
            telegram_link = f"@{bot.get_chat(user2_id).username}" if bot.get_chat(user2_id).username else "Telegram username not set"
            profile_message_user2 = (
                f"🎉 You have a new match! 🎉\n\n"
                f"👤 *Name*: {name}\n"
                f"🌆 *City*: {city}\n"
                f"💼 *Occupation*: {occupation}\n"
                f"💡 *Interests*: {interests}\n"
                f"📞 *Contacts*: {contacts}\n"
                f"🔗 *Telegram*: {telegram_link}"
            )

            # Получаем фото профиля user2
            photos = bot.get_user_profile_photos(user2_id, limit=1)
            if photos.total_count > 0:
                photo_id = photos.photos[0][0].file_id
                bot.send_photo(user1_id, photo_id, caption=profile_message_user2, parse_mode="Markdown")
            else:
                bot.send_message(user1_id, profile_message_user2, parse_mode="Markdown")

        # Отправляем карточку и фото профиля user1 -> user2
        if user1_profile:
            name, city, occupation, interests, contacts = user1_profile
            telegram_link = f"@{bot.get_chat(user1_id).username}" if bot.get_chat(user1_id).username else "Telegram username not set"
            profile_message_user1 = (
                f"🎉 You have a new match! 🎉\n\n"
                f"👤 *Name*: {name}\n"
                f"🌆 *City*: {city}\n"
                f"💼 *Occupation*: {occupation}\n"
                f"💡 *Interests*: {interests}\n"
                f"📞 *Contacts*: {contacts}\n"
                f"🔗 *Telegram*: {telegram_link}"
            )

            # Получаем фото профиля user1
            photos = bot.get_user_profile_photos(user1_id, limit=1)
            if photos.total_count > 0:
                photo_id = photos.photos[0][0].file_id
                bot.send_photo(user2_id, photo_id, caption=profile_message_user1, parse_mode="Markdown")
            else:
                bot.send_message(user2_id, profile_message_user1, parse_mode="Markdown")

    conn.close()

# Основной процесс подбора пар
def run_pairing_process():
    pairs = generate_pairs()
    if pairs:
        save_pairs_to_db(pairs)
        notify_pairs(pairs)
    else:
        print("No available matches for pairing")

def schedule_pairing():
    schedule.every().monday.at("10:00").do(run_pairing_process)
    # код который будет отправлять каждую минуту: schedule.every(1).minutes.do(run_pairing_process)

    # Бесконечный цикл для выполнения запланированных задач
    while True:
        schedule.run_pending()  # Проверяет и запускает задачи
        time.sleep(1)  # Пауза на 1 секунду

# Запускаем планировщик в отдельном потоке
import threading
scheduler_thread = threading.Thread(target=schedule_pairing)
scheduler_thread.start()


bot.polling(none_stop=True)