import sqlite3
import telebot
from code.config import *

bot = telebot.TeleBot(TOKEN)

def initialize_database():
    """
    Инициализирует базу данных SQLite и создаёт необходимые таблицы, если они ещё не существуют.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Создание таблицы пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT,
                username TEXT DEFAULT '',
                name TEXT DEFAULT '',
                gender INTEGER,
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

        # Создание таблицы отзывов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создание таблицы пар
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pair_registry (
                pair_id INTEGER PRIMARY KEY,
                creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user1_id INTEGER NOT NULL,
                user2_id INTEGER NOT NULL,
                common_interests INTEGER DEFAULT 0,
                meeting_status_user1 INTEGER DEFAULT NULL,
                meeting_status_user2 INTEGER DEFAULT NULL,
                failure_reason TEXT DEFAULT '',
                is_unpaired INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ban_list (
                id INTEGER PRIMARY KEY,       -- User ID
                ban_status INTEGER DEFAULT 0  -- Ban status: 0 - not banned, 1 - banned
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status INTEGER NOT NULL DEFAULT 1
            )
        ''')

        conn.commit()

def is_user_registered(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone() is not None

# Функция для получения данных пользователей из БД
def get_users_from_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.interests, u.previous_pairs
            FROM users u
            LEFT JOIN ban_list b ON u.id = b.id
            WHERE u.status = 1 AND (b.ban_status = 0)
        ''')  # добавить в where: AND (b.ban_status = 0)
        users = cursor.fetchall()

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

# Функция для сохранения пары в базу данных
def save_pairs_to_db(pairs):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for pair in pairs:
        user1_id, user2_id = pair
        cursor.execute("UPDATE users SET previous_pairs = previous_pairs || ? WHERE id = ?", (f",{user2_id}", user1_id))
        cursor.execute("UPDATE users SET previous_pairs = previous_pairs || ? WHERE id = ?", (f",{user1_id}", user2_id))

    conn.commit()
    conn.close()

def update_meeting_status(pair_id, user_role, status):
    """
    Обновляет статус встречи для конкретного пользователя (user1 или user2).
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        if user_role == "user1":
            cursor.execute(
                "UPDATE pair_registry SET meeting_status_user1 = ? WHERE pair_id = ?",
                (status, pair_id)
            )
        elif user_role == "user2":
            cursor.execute(
                "UPDATE pair_registry SET meeting_status_user2 = ? WHERE pair_id = ?",
                (status, pair_id)
            )
        conn.commit()

def is_email_in_use(email):
    # Создаем соединение и курсор локально
    with sqlite3.connect(DB_PATH) as conn_email:
        cursor_email = conn_email.cursor()  # Локальный курсор
        cursor_email.execute("SELECT COUNT(*) FROM users WHERE email = ?", (email,))
        result = cursor_email.fetchone()[0]
    # После выполнения команды соединение автоматически закрывается
    return result > 0

def get_bot_status():
    # Используем 'with as', чтобы автоматически закрыть соединение по выходу из блока
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM bot_status LIMIT 1")
        row = cursor.fetchone()

        if row is not None:
            return row[0]  # Возвращаем значение поля status
        else:
            return None  # Если таблица пуста или нет записей

def insert_feedback(user_id, rating, comment):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feedback (user_id, rating, comment)
            VALUES (?, ?, ?)
        ''', (user_id, rating, comment))
        conn.commit()

def process_ban_status_change(message):
        try:
            user_id = int(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "Invalid ID. Please enter the command again and provide a numeric ID.")
            return

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Проверяем текущий статус пользователя
            cursor.execute("SELECT ban_status FROM ban_list WHERE id = ?", (user_id,))
            result = cursor.fetchone()

            if result is None:
                # Если пользователь отсутствует в таблице, добавляем его с ban_status = 1 (banned)
                bot.send_message(message.chat.id,"User is not found. Please enter the command again and provide a correct ID.")
                return
            else:
                # Если пользователь найден, меняем статус на противоположный
                current_status = result[0]
                new_status = 1 if current_status == 0 else 0
                cursor.execute("UPDATE ban_list SET ban_status = ? WHERE id = ?", (new_status, user_id))
                conn.commit()

                if new_status == 1:
                    bot.send_message(message.chat.id, f"User with ID {user_id} has been banned.")
                else:
                    bot.send_message(message.chat.id, f"User with ID {user_id} has been unbanned.")

def get_bot_statistics():
    """
    Выполняет запросы к базе данных и возвращает
    все показатели, необходимые для формирования статистики:
      - total_users
      - gender_stats (список [(gender, count), ...])
      - top_cities
      - top_programs
      - top_occupations
      - avg_age
      - active_users
      - total_pairs
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Total registered users
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        # Gender distribution
        cursor.execute("SELECT gender, COUNT(*) FROM users GROUP BY gender")
        gender_stats = cursor.fetchall()

        # Top 3 popular cities
        cursor.execute("SELECT city, COUNT(*) as count FROM users GROUP BY city ORDER BY count DESC LIMIT 3")
        top_cities = cursor.fetchall()

        # Top 3 popular universities
        cursor.execute("SELECT program, COUNT(*) as count FROM users GROUP BY program ORDER BY count DESC LIMIT 3")
        top_programs = cursor.fetchall()

        # Top 3 popular occupations
        cursor.execute("SELECT occupation, COUNT(*) as count FROM users GROUP BY occupation ORDER BY count DESC LIMIT 3")
        top_occupations = cursor.fetchall()

        # Average age
        cursor.execute("SELECT AVG(age) FROM users WHERE age IS NOT NULL")
        avg_age = cursor.fetchone()[0]

        # Active users
        cursor.execute("SELECT COUNT(*) FROM users WHERE status = 1")
        active_users = cursor.fetchone()[0]

        # Total pairs in pair_registry
        cursor.execute("SELECT COUNT(*) FROM pair_registry")
        total_pairs = cursor.fetchone()[0]

    return {
        'total_users': total_users,
        'gender_stats': gender_stats,
        'top_cities': top_cities,
        'top_programs': top_programs,
        'top_occupations': top_occupations,
        'avg_age': avg_age,
        'active_users': active_users,
        'total_pairs': total_pairs
    }

def delete_user_from_db(user_id=None, username=None):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            if user_id is not None:
                cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            elif username is not None:
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            else:
                return "error: Invalid parameters."

            user_to_delete = cursor.fetchone()
            if user_to_delete:
                user_id_to_delete = user_to_delete[0]

                # Удаление из основной таблицы users
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id_to_delete,))

                # Удаление из таблицы ban_list
                cursor.execute("DELETE FROM ban_list WHERE id = ?", (user_id_to_delete,))

                conn.commit()
                return "deleted"
            else:
                return "not_found"
    except Exception as e:
        return f"error: {e}"

def get_user_by_username(username):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, name, city, occupation
            FROM users WHERE username = ?
        """, (username,))
        return cursor.fetchone()

def get_user_by_id(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, name, city, occupation
            FROM users WHERE id = ?
        """, (user_id,))
        return cursor.fetchone()

def get_users_by_name(name):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, name, city, occupation
            FROM users WHERE name LIKE ?
        """, (f"%{name}%",))
        return cursor.fetchall()

def initialize_bot_status():
    """
    Инициализирует таблицу bot_status, если она пуста.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bot_status")
        row_count = cursor.fetchone()[0]

        if row_count == 0:
            cursor.execute("INSERT INTO bot_status (status) VALUES (1)")
            print("Таблица была пустой, добавлена строка со статусом = 1")

def update_bot_status(new_status):
    """
    Обновляет статус в таблице bot_status.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE bot_status SET status = ? WHERE id = 1", (new_status,))