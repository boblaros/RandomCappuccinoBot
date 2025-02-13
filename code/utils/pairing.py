import random
from collections import defaultdict
from telebot import types
from utils.db import *
from config import ADMIN_IDS, DB_PATH
import sqlite3
from utils.utils import *
import os

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

            if common_count > 0 and str(user2_id) not in users[i]['previous_pairs'] and str(user1_id) not in users[j]['previous_pairs']:
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

    # Найти всех пользователей, у которых нет пары
    all_user_ids = set(user['id'] for user in users)
    paired_user_ids = set(user_id for pair in pairs for user_id in pair)
    unpaired_user_ids = list(all_user_ids - paired_user_ids)

    # Случайно формируем пары из оставшихся
    random.shuffle(unpaired_user_ids)
    while len(unpaired_user_ids) > 1:
        user1 = unpaired_user_ids.pop()
        user2 = unpaired_user_ids.pop()
        pairs.append((user1, user2))

    # Если остался один пользователь
    remaining_user = None
    if unpaired_user_ids:
        remaining_user = unpaired_user_ids[0]
        del unpaired_user_ids  # Удаляем переменную

    return pairs, remaining_user

# Функция для уведомления пользователей о новых парах
def notify_pairs(bot, pairs):
    """
    Уведомляет пользователей о новой паре, отправляет карточку партнёра и фото профиля.
    """
    def send_profile(user_id, match_id, match_profile, gender):
        """
        Отправляет карточку профиля и фото.
        """
        profile_message = "Profile details are unavailable."  # Default profile message
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

        if match_profile:
            name, city, occupation, interests, contacts = match_profile
            telegram_link = f"@{bot.get_chat(match_id).username}" if bot.get_chat(match_id).username else "Telegram username not set"
            profile_message = (
                f"🎉 You have a new match! 🎉\n\n"
                f"👤 *Name*: {name}\n"
                f"🌆 *City*: {city}\n"
                f"💼 *Occupation*: {occupation}\n"
                f"💡 *Interests*: {interests}\n"
                f"📞 *Contacts*: {contacts}\n"
                f"🔗 *Telegram*: {telegram_link}"
            )

            # Check if a local profile photo exists
        images_dir = os.path.join(base_dir, 'data', 'images')
        photo_path = os.path.join(images_dir, f'user{match_id}_photo.jpg')
        try:
            with open(photo_path, 'rb') as photo:
                bot.send_photo(user_id, photo, caption=profile_message, parse_mode="Markdown")
        except FileNotFoundError:
            # Fall back to the existing logic
            photos = bot.get_user_profile_photos(match_id, limit=1)
            if photos.total_count > 0:
                photo_id = photos.photos[0][0].file_id
                bot.send_photo(user_id, photo_id, caption=profile_message, parse_mode="Markdown")
            else:
                default_photo_path = os.path.join(base_dir, 'data', 'male_photo.jpg' if gender == 0 else 'female_photo.jpg')
                bot.send_photo(user_id, open(default_photo_path, 'rb'), caption=profile_message, parse_mode="Markdown")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        for user1_id, user2_id in pairs:
            # Получаем данные обоих пользователей
            cursor.execute("""
                SELECT name, city, occupation, interests, contacts, gender
                FROM users WHERE id = ?
            """, (user2_id,))
            user2_profile = cursor.fetchone()

            cursor.execute("""
                SELECT name, city, occupation, interests, contacts, gender
                FROM users WHERE id = ?
            """, (user1_id,))
            user1_profile = cursor.fetchone()

            # Отправляем профили, включая gender для выбора фото по умолчанию
            if user2_profile:
                send_profile(user1_id, user2_id, user2_profile[:-1], user2_profile[-1])  # user2 -> user1
            if user1_profile:
                send_profile(user2_id, user1_id, user1_profile[:-1], user1_profile[-1])  # user1 -> user2

# Основной процесс подбора пар
def run_pairing_process(bot):
    pairs, remaining_user = generate_pairs()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if pairs:
        save_pairs_to_db(pairs)
        notify_pairs(bot, pairs)
        for user1_id, user2_id in pairs:
            # Получаем интересы обоих пользователей
            cursor.execute("SELECT interests FROM users WHERE id = ?", (user1_id,))
            user1_interests = set(cursor.fetchone()[0].split(','))

            cursor.execute("SELECT interests FROM users WHERE id = ?", (user2_id,))
            user2_interests = set(cursor.fetchone()[0].split(','))

            # Вычисляем общие интересы с использованием существующей функции
            common_count = common_interests(user1_interests, user2_interests)

            # Сохраняем данные в таблицу pair_registry
            cursor.execute('''
                INSERT INTO pair_registry (user1_id, user2_id, common_interests, is_unpaired)
                VALUES (?, ?, ?, ?)
            ''', (user1_id, user2_id, common_count, 0))
        print("Pairs saved to the registry.")
    else:
        print("No available matches for pairing")

    if remaining_user:
        cursor.execute('''
                INSERT INTO pair_registry (user1_id, user2_id, common_interests, is_unpaired)
                VALUES (?, -1, ?, ?)
            ''', (remaining_user, 0, 1))
        print(f"Remaining user {remaining_user} saved to the registry.")

    conn.commit()
    conn.close()

    if remaining_user:
        notify_admins_about_unpaired_user(bot, remaining_user)

def notify_admins_about_unpaired_user(bot, user_id):
    # Отправляем уведомление администраторам
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"User {user_id} did not get a match this time.")

def check_bot_status_and_get_feedback(bot):
    status = get_bot_status()
    if status == 1:
        request_pair_feedback(bot)
    else:
        print("Статус бота = 0, не запускаем request_pair_feedback")

def request_pair_feedback(bot):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT pair_id, user1_id, user2_id FROM pair_registry WHERE creation_date = (SELECT MAX(creation_date) FROM pair_registry)  AND user1_id <> -1 AND user2_id <> -1")

        pairs = cursor.fetchall()

        for pair in pairs:
            pair_id, user1_id, user2_id = pair
            for user_id in [user1_id, user2_id]:
                markup = types.InlineKeyboardMarkup()
                yes_button = types.InlineKeyboardButton("Yes", callback_data=f"feedback_yes_{pair_id}_{user_id}")
                no_button = types.InlineKeyboardButton("No", callback_data=f"feedback_no_{pair_id}_{user_id}")
                markup.add(yes_button, no_button)

                bot.send_message(user_id, "Did the meeting happen?", reply_markup=markup)