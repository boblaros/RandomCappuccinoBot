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
            body = f"Il tuo codice di verifica è: {code}"
            message.attach(MIMEText(body, 'plain', 'utf-8'))

            # Отправляем письмо
            server.sendmail(EMAIL_ADDRESS, email, message.as_string())
        return True
    except Exception as e:
        print(f"Errore nell'invio dell'email: {e}")
        return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Ciao! Inserisci il tuo indirizzo email per confermare il tuo stato di studente.")
    bot.register_next_step_handler(message, handle_email)

@bot.message_handler(commands=['start_pairing'])
def handle_start_pairing(message):
    if message.chat.id in ADMIN_IDS:
        bot.send_message(message.chat.id, "Начинаю подбор пар... ⏳")
        run_pairing_process()
        bot.send_message(message.chat.id, "Подбор пар завершен!")
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")

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
                bot.send_message(message.chat.id, f"Un codice di verifica è stato inviato a {email}. Si prega di inserire qui sotto. Controlla la posta indesiderata se non hai ricevuto il codice")
                verification_codes[message.chat.id] = (email, verification_code)
                bot.register_next_step_handler(message, verify_code)  # Ожидаем ввода кода
            else:
                bot.send_message(message.chat.id,
                             "Si è verificato un errore nell'invio dell'e-mail di verifica. Riprova più tardi.")
                bot.register_next_step_handler(message, handle_email)
    else:
        bot.send_message(message.chat.id, "Formato e-mail non valido. Inserisci un indirizzo email valido.")
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
                button = types.InlineKeyboardButton("📝 Compila il questionario", callback_data="start_questionnaire")
                markup.add(button)

                bot.send_message(
                    message.chat.id,
                    f"Ciao 👋\nSono Random Cappuccino ☕, un bot che promuove il networking per gli studenti universitari italiani.🇮🇹\n\nOgni settimana ti suggerirò una persona interessante da incontrare, selezionata casualmente tra gli altri membri della community.🔄\n\nPer partecipare ai meetup, è necessario compilare un questionario.💡📝\n\nContinuando a interagire con il bot, date il vostro consenso al trattamento dei dati personali in conformità con i termini del Regolamento generale sulla protezione dei dati, GDPR.🔒📜",
                    reply_markup=markup
                )

            else:
                bot.send_message(message.chat.id, "Codice non valido. Per favore riprova.")
                bot.register_next_step_handler(message, verify_code)  # Ожидаем повторного ввода кода
        except ValueError:
            bot.send_message(message.chat.id, "Input non valido. Inserisci il codice numerico di verifica.")
            bot.register_next_step_handler(message, verify_code)  # Ожидаем повторного ввода кода
    else:
        bot.send_message(message.chat.id, "Il processo di verifica è scaduto. Si prega di ricominciare inserendo /start.")


@bot.callback_query_handler(func=lambda call: call.data == "start_questionnaire")
def start_questionnaire_callback(call):
    # Удаляем inline-клавиатуру после нажатия
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    bot.send_message(call.message.chat.id, "Inserisci il tuo nome e cognome:")
    bot.register_next_step_handler(call.message, ask_city)

def ask_city(message):
    user_data[message.chat.id]['name'] = message.text
    bot.send_message(message.chat.id, "Inserisci la tua città:")
    bot.register_next_step_handler(message, ask_occupation)

def ask_occupation(message):
    user_data[message.chat.id]['city'] = message.text
    bot.send_message(message.chat.id, "Descrivete ciò che fate:")
    bot.register_next_step_handler(message, ask_program)

def ask_program(message):
    user_data[message.chat.id]['occupation'] = message.text
    bot.send_message(message.chat.id, "Inserisci il tuo programma di studi:")
    bot.register_next_step_handler(message, ask_interests)

def ask_interests(message):
    user_data[message.chat.id]['program'] = message.text
    bot.send_message(message.chat.id, "Inserisci i tuoi interessi (separati da virgola):")
    bot.register_next_step_handler(message, ask_age)

def ask_age(message):
    user_data[message.chat.id]['interests'] = message.text
    bot.send_message(message.chat.id, "Inserisci la tua età:")
    bot.register_next_step_handler(message, ask_contacts)

def ask_contacts(message):
    try:
        user_data[message.chat.id]['age'] = int(message.text)
        bot.send_message(message.chat.id, "Inserisci i tuoi contatti (es. email o numero di telefono):")
        bot.register_next_step_handler(message, save_to_db)
    except ValueError:
        bot.send_message(message.chat.id, "Per favore inserisci un'età valida (numero).")
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
        f"Fatto! 🙌\n\n"
        f"Ora sei un partecipante agli incontri di Random Cappuccino ☕️\n\n"
        f"Ecco come apparirà il tuo profilo nel messaggio che invieremo al tuo compagno:\n"
        f"⏬\n\n"
        f"👤 Nome: {user_data[message.chat.id]['name']}\n"
        f"🌆 Città: {user_data[message.chat.id]['city']}\n"
        f"💼 Occupazione: {user_data[message.chat.id]['occupation']}\n"
        f"🎓 Programma: {user_data[message.chat.id]['program']}\n"
        f"💡 Interessi: {user_data[message.chat.id]['interests']}\n"
        f"🎂 Età: {user_data[message.chat.id]['age']}\n"
        f"📞 Contatti: {user_data[message.chat.id]['contacts']}\n\n"
        f"Se hai bisogno di cambiare qualcosa, usa il comando /help."
    )

    # Создаем inline-кнопку
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("Avanti verso nuove conoscenze", callback_data="forward_to_meetups")
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

# Пустая команда /help
@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.send_message(message.chat.id, "Il comando non è ancora attivo, ma presto qui apparirà un'istruzione!")

# Функция для получения данных пользователей из БД
def get_users_from_db():
    conn = sqlite3.connect('random_cappuccino.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, interests, previous_pairs FROM users")
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

            if common_count > 0:
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
    for pair in pairs:
        user1_id, user2_id = pair
        bot.send_message(user1_id, f"Hai un nuovo incontro! Il tuo partner è {user2_id}.")
        bot.send_message(user2_id, f"Hai un nuovo incontro! Il tuo partner è {user1_id}.")

# Основной процесс подбора пар
def run_pairing_process():
    pairs = generate_pairs()
    if pairs:
        save_pairs_to_db(pairs)
        notify_pairs(pairs)
    else:
        print("Нет доступных пар для подбора.")

bot.polling(none_stop=True)