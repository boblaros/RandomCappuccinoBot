import re
import smtplib
import ssl
import telebot
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import SMTP_SERVER, SMTP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD, ADMIN_IDS
from utils.db import (get_users_from_db,
                get_user_by_username,
                get_user_by_id,
                get_users_by_name,
                update_bot_status,
                initialize_bot_status,
                delete_user_from_db,
                process_ban_status_change)

email_pattern = re.compile(
    r"^[a-zA-Z0-9._%+-]+@(?:"
    r"studbocconi\.it|"                # Bocconi
    r"studenti\.unibocconi\.it|"       # Bocconi
    r"studenti\.unimi\.it|"            # Università degli Studi di Milano (UniMi)
    r"mail\.polimi\.it|"               # Politecnico di Milano (PoliMi)
    r"icatt\.it|"                      # Università Cattolica del Sacro Cuore (Cattolica)
    r"studenti\.uniroma1\.it|"         # Sapienza Università di Roma
    r"studenti\.unibo\.it|"            # Università di Bologna
    r"studenti\.unito\.it|"            # Università degli Studi di Torino
    r"studenti\.unina\.it|"            # Università degli Studi di Napoli Federico II
    r"studenti\.unipd\.it|"            # Università degli Studi di Padova
    r"studenti\.unipi\.it|"            # Università di Pisa
    r"studenti\.unisa\.it|"            # Università degli Studi di Salerno
    r"studenti\.unica\.it"             # Università degli Studi di Cagliari
    r")$"
)

def common_interests(user1_interests, user2_interests):
    # Приводим интересы к нижнему регистру и убираем пробелы
    normalized_user1_interests = {interest.strip().lower() for interest in user1_interests}
    normalized_user2_interests = {interest.strip().lower() for interest in user2_interests}

    # Выполняем пересечение и возвращаем количество общих элементов
    return len(normalized_user1_interests & normalized_user2_interests)

def send_verification_code(email, code):
    print('EMAIL_ADDRESS', EMAIL_ADDRESS)
    try:
        # Создаём контекст SSL
        context = ssl.create_default_context()

        # Подключаемся к SMTP-серверу
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

            # Формируем письмо с помощью MIME
            message = MIMEMultipart()
            message['From'] = 'Random Cappuccino Bot'
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

def check_message_for_command(bot, message):
    if message.text in ['/skip', '/start', '/admin', '/help', '/faq', '/about', '/rules', '/feedback', '/profile',
                        '/edit_profile', '/pause', '/resume', '/start_pairing', '/delete_profile']:
        bot.send_message(message.chat.id, f"Command interrupted")
        return False
    return True

def escape_markdown(text):
    """Экранирует специальные символы для MarkdownV2"""
    if not isinstance(text, str):  # Проверяем, что text — это строка
        return str(text)  # Преобразуем в строку, если это число или None

    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

def send_user_details(bot, chat_id, users):
    """
    Sends details of the user(s) to the admin.
    """
    for user in users:
        user_id = escape_markdown_v2(user[0])
        email = escape_markdown_v2(user[1])
        username = f"@{escape_markdown_v2(user[2])}" if user[2] else "Not set"
        name = escape_markdown_v2(user[3])
        gender = escape_markdown_v2(user[4])
        city = escape_markdown_v2(user[5])
        occupation = escape_markdown_v2(user[6])
        program = escape_markdown_v2(user[7])
        interests = escape_markdown_v2(user[8])
        age = escape_markdown_v2(user[9])
        contacts = escape_markdown_v2(user[10])
        status = escape_markdown_v2(user[11])
        previous_pairs = escape_markdown_v2(user[12])

        user_details = (
            f"👤 *User Details*\n\n"
            f"🆔 ID: `{user_id}`\n"
            f"📧 Email: `{email}`\n"
            f"🔗 Username: {username}\n"
            f"👤 Name: {name}\n"
            f"🚻 Gender: `{gender}`\n"
            f"🌆 City: `{city}`\n"
            f"💼 About: `{occupation}`\n"
            f"🎓 Program: `{program}`\n"
            f"💡 Interests: `{interests}`\n"
            f"🎂 Age: `{age}`\n"
            f"📞 Contacts: `{contacts}`\n"
            f"📌 Status: `{status}`\n"
            f"🤝 Previous Pairs: `{previous_pairs}`"
        )

        bot.send_message(chat_id, user_details, parse_mode="MarkdownV2")

def send_broadcast_message(bot, message):
    """
    Рассылает сообщение всем пользователям и уведомляет администраторов.
    """
    admin_ids = ADMIN_IDS
    users_list = get_users_from_db()  # Получаем список пользователей
    success_count = 0
    fail_count = 0

    # Экранируем текст перед отправкой
    message_text = escape_markdown_v2(message.text)

    # Подтверждение для отправителя
    bot.send_message(
        message.chat.id, 
        f"You are broadcasting the following message:\n\n{message_text}",
        parse_mode="MarkdownV2"
    )

    for user in users_list:
        user_id = None  # Инициализация переменной
        try:
            user_id = user['id']  # Присваиваем значение из словаря
            print(user_id, message_text)
            bot.send_message(user_id, message_text, parse_mode="MarkdownV2")  # Отправляем сообщение пользователю
            success_count += 1
        except KeyError:
            fail_count += 1
            print("Не удалось отправить сообщение: отсутствует ключ 'id' в user.")
        except telebot.apihelper.ApiTelegramException as e:
            fail_count += 1
            print(f"Не удалось отправить сообщение пользователю {user_id if user_id else 'unknown'}: {e}")
        except Exception as e:
            fail_count += 1
            print(f"Неизвестная ошибка при отправке сообщения пользователю {user_id if user_id else 'unknown'}: {e}")

    # Формируем итоговое сообщение для администраторов
    admin_message = (
        f"Рассылка завершена.\n"
        f"✅ *Успешно отправлено*: {success_count}\n"
        f"❌ *Не удалось отправить*: {fail_count}"
    )

    # Отправляем сообщение администраторам
    for admin_id in admin_ids:
        try:
            bot.send_message(admin_id, admin_message, parse_mode="Markdown")
        except Exception as e:
            print(f"Не удалось уведомить администратора {admin_id}: {e}")


def search_by_username(bot, message):
    if not check_message_for_command(bot, message): return

    username = message.text.strip().lstrip("@")
    user = get_user_by_username(username)

    if user:
        send_user_details(bot, message.chat.id, [user])
    else:
        bot.send_message(message.chat.id, "No user found with the given username.")

def search_by_id(bot, message):
    if not check_message_for_command(bot, message): return
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "Invalid ID. Please enter a numeric value.")
        return

    user_id = int(message.text.strip())
    user = get_user_by_id(user_id)

    if user:
        send_user_details(bot, message.chat.id, [user])
    else:
        bot.send_message(message.chat.id, "No user found with the given ID.")

def search_by_name(bot, message):
    if not check_message_for_command(bot, message): return

    name = message.text.strip()
    users = get_users_by_name(name)

    if users:
        send_user_details(bot, message.chat.id, users)
    else:
        bot.send_message(message.chat.id, "No users found with the given name or part of the name.")

def process_user_deletion(bot, message):
    if not check_message_for_command(bot, message): return
    user_input = message.text.strip()

    if user_input.isdigit():
        user_id = int(user_input)
        result = delete_user_from_db(user_id=user_id)
    elif user_input.startswith("@"):
        telegram_username = user_input.lstrip("@")
        result = delete_user_from_db(username=telegram_username)
    else:
        bot.send_message(
            message.chat.id,
            "Invalid input. Repeat the command and enter a numeric ID or a valid Telegram username (e.g., @username)."
        )
        return

    if result == "deleted":
        bot.send_message(
            message.chat.id, f"User has been successfully deleted."
        )
    elif result == "not_found":
        bot.send_message(
            message.chat.id, "No user found with the given ID or Telegram username.")
    elif result.startswith("error"):
        bot.send_message(
            message.chat.id, f"Error: {result.split(':', 1)[1]}"
        )

def process_bot_status_change(bot, message):
    """
    Proceed bot status change
    """
    if not check_message_for_command(bot, message): return

    try:
        new_status = int(message.text)
        if new_status not in (0, 1):
            bot.send_message(message.chat.id, "Invalid number. 0 or 1 are required.")
            return
        else:
            # Проверяем и инициализируем статус в БД, если нужно
            initialize_bot_status()

            # Update status in DB
            update_bot_status(new_status)
            bot.send_message(message.chat.id, f"Status is changed to {new_status}.")
            return
    except ValueError:
        bot.send_message(message.chat.id, "Invalid format. 0 or 1 are required.")

def escape_markdown_v2(text):
    """
    Экранирует специальные символы для MarkdownV2.
    """
    if not isinstance(text, str):
        text = str(text)  # Преобразуем в строку, если передано число

    # Все спецсимволы MarkdownV2, требующие экранирования
    escape_chars = r'_*[]()~`>#+-=|{.}!@'

    # Заменяем все зарезервированные символы на экранированные
    return re.sub(r'([{}])'.format(re.escape(escape_chars)), r'\\\1', text)

def escape_markdown_v1(text):
    """
    Экранирует специальные символы для MarkdownV2.
    """
    if not isinstance(text, str):
        text = str(text)  # Преобразуем в строку, если передано число

    # Все спецсимволы MarkdownV2, требующие экранирования
    escape_chars = r'_*[]()~`>#+-=|{}!'

    # Заменяем все зарезервированные символы на экранированные
    return re.sub(r'([{}])'.format(re.escape(escape_chars)), r'\\\1', text)

def handle_ban_status_input(bot, message):

    """
    Обрабатывает введенный ID и передает его в функцию смены статуса.
    """
    try:
        user_id = int(message.text.strip())
    except ValueError:
        bot.send_message(
            message.chat.id,
            escape_markdown_v2("Invalid ID. Please enter the command again and provide a numeric ID."),
            parse_mode="MarkdownV2"
        )
        return

    # Change ban status in DB
    new_status = process_ban_status_change(user_id)

    # Отправляем ответ в зависимости от результата
    if new_status is None:
        bot.send_message(
            message.chat.id,
            escape_markdown_v2("User is not found. Please enter the command again and provide a correct ID."),
            parse_mode="MarkdownV2"
        )
    else:
        status_text = "banned" if new_status == 1 else "unbanned"
        bot.send_message(
            message.chat.id,
            escape_markdown_v2(f"User with ID {user_id} has been {status_text}."),
            parse_mode="MarkdownV2"
        )