# Built-in libraries
import random
import itertools

# Third-party libraries
import numpy as np
from telebot import types
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Local modules
from utils.db import *
from utils.utils import *

model = SentenceTransformer('all-MiniLM-L6-v2')

# Алгоритм подбора пар
def generate_pairs():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
                SELECT u.id, u.occupation, u.interests, u.previous_pairs
                FROM users u
                LEFT JOIN ban_list b ON u.id = b.id
                WHERE u.status = 1 AND (b.ban_status = 0)
            ''')
        users = cursor.fetchall()

    user_ids = []
    profile_texts = []
    previous_pairs_dict = {}

    # 1. Подготовка текстов и парсинг previous_pairs
    for user in users:
        user_id, description, interests, previous = user
        full_text = f"{description}. Interests: {interests}"
        user_ids.append(user_id)
        profile_texts.append(full_text)

        if previous:
            cleaned = previous.lstrip(',')  # удаляем начальную запятую
            previous_pairs = set(map(int, cleaned.split(','))) if cleaned else set()
        else:
            previous_pairs = set()
        previous_pairs_dict[user_id] = previous_pairs

    # 2. Векторизация
    embeddings = model.encode(profile_texts, normalize_embeddings=True)

    # 3. Матрица схожести
    sim_matrix = cosine_similarity(embeddings)
    np.fill_diagonal(sim_matrix, -1)

    # 4. Жадный подбор НОВЫХ пар
    used = set()
    pairs = []

    while len(used) < len(user_ids) - 1:
        max_sim = -1
        best_pair = (None, None)

        for i, j in itertools.combinations(range(len(user_ids)), 2):
            if i in used or j in used:
                continue

            id_i = user_ids[i]
            id_j = user_ids[j]

            if (id_j in previous_pairs_dict[id_i]) or (id_i in previous_pairs_dict[id_j]):
                continue  # если такая пара уже была — пропускаем

            if sim_matrix[i][j] > max_sim:
                max_sim = sim_matrix[i][j]
                best_pair = (i, j)

        i, j = best_pair
        if i is None or j is None:
            break  # не осталось новых допустимых пар

        used.add(i)
        used.add(j)
        pairs.append((user_ids[i], user_ids[j]))

    # 5. Рандомные пары из оставшихся, если ничего не подошло
    remaining_indices = [idx for idx in range(len(user_ids)) if idx not in used]
    random.shuffle(remaining_indices)

    while len(remaining_indices) >= 2:
        i = remaining_indices.pop()
        j = remaining_indices.pop()
        pairs.append((user_ids[i], user_ids[j]))

    # 6. Один остался без пары?
    remaining_user = user_ids[remaining_indices[0]] if remaining_indices else None

    return pairs, remaining_user

# Функция для уведомления пользователей о новых парах
def notify_pairs(pairs):
    """
    Уведомляет пользователей о новой паре, отправляет карточку партнёра и фото профиля.
    """
    def send_profile(user_id, match_id, match_profile, gender):
        """
        Отправляет карточку профиля и фото.
        """
        profile_message = "Profile details are unavailable."

        # Пути к директории изображений
        images_dir_prod = '/data/images'
        images_dir_dev = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data/images'))
        images_dir = images_dir_prod if os.path.exists('/data') else images_dir_dev

        if match_profile:
            name, city, occupation, interests, contacts = match_profile

            try:
                chat = bot.get_chat(match_id)
                telegram_username = f"@{chat.username}" if chat.username else "Telegram username not set"
            except Exception:
                telegram_username = "Telegram username not set"

            profile_message = (
                f"🎉 You have a new match! 🎉\n\n"
                f"👤 *Name*: {escape_markdown_v1(name)}\n"
                f"🌆 *City*: {escape_markdown_v1(city)}\n"
                f"📝 *About me*: {escape_markdown_v1(occupation)}\n"
                f"💡 *Interests*: {escape_markdown_v1(interests)}\n"
                f"📞 *Contacts*: {escape_markdown_v1(contacts)}\n"
                f"🔗 *Telegram*: {escape_markdown_v1(telegram_username)}"
            )

        photo_path = os.path.join(images_dir, f'user{match_id}_photo.jpg')

        try:
            if os.path.exists(photo_path):
                with open(photo_path, 'rb') as photo:
                    bot.send_photo(user_id, photo, caption=profile_message, parse_mode="Markdown")
            else:
                # Пробуем получить фото пользователя через Telegram API
                photos = bot.get_user_profile_photos(match_id, limit=1)
                if photos.total_count > 0:
                    photo_id = photos.photos[0][0].file_id
                    bot.send_photo(user_id, photo_id, caption=profile_message, parse_mode="Markdown")
                else:
                    # Используем дефолтное фото
                    default_filename = 'male_photo.jpg' if gender == 0 else 'female_photo.jpg'
                    default_photo_path = os.path.join(images_dir, default_filename)
                    if os.path.exists(default_photo_path):
                        with open(default_photo_path, 'rb') as default_photo:
                            bot.send_photo(user_id, default_photo, caption=profile_message, parse_mode="Markdown")
                    else:
                        bot.send_message(user_id, "Profile photo is not available and default photo is missing.")
        except Exception as e:
            error_text = str(e)
            if "bot was blocked by the user" in error_text or "403" in error_text:
                print(f"[WARN] User {user_id} blocked the bot. Skipping...")
            else:
                print(f"[ERROR] Failed to send profile to user {user_id}: {error_text}")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        for user1_id, user2_id in pairs:
            # Получаем профиль user2 для user1
            cursor.execute("""
                SELECT name, city, occupation, interests, contacts, gender
                FROM users WHERE id = ?
            """, (user2_id,))
            user2_profile = cursor.fetchone()

            # Получаем профиль user1 для user2
            cursor.execute("""
                SELECT name, city, occupation, interests, contacts, gender
                FROM users WHERE id = ?
            """, (user1_id,))
            user1_profile = cursor.fetchone()

            if user2_profile:
                send_profile(user1_id, user2_id, user2_profile[:-1], user2_profile[-1])
            if user1_profile:
                send_profile(user2_id, user1_id, user1_profile[:-1], user1_profile[-1])

# Основной процесс подбора пар
def run_pairing_process():
    pairs, remaining_user = generate_pairs()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if pairs:
        save_pairs_to_db(pairs)
        notify_pairs(pairs)
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

            starter_id = random.choice([user1_id, user2_id])
            bot.send_message(starter_id, "This time, you write first 👆")

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
        notify_admins_about_unpaired_user(remaining_user)

def notify_admins_about_unpaired_user(user_id):
    # Отправляем уведомление администраторам
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"User {user_id} did not get a match this time.")

def check_bot_status_and_get_feedback():
    status = get_bot_status()
    if status == 1:
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id,
                                 'Weekly feedback collection has started (every Sunday at 10:00 AM, Milan time).')
            except Exception as e:
                print(f"Failed to notify administrator {admin_id}: {e}")
        request_pair_feedback()
    else:
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id,
                                 'Feedback collection not started — the bot is turned off (set_status = 0).')
            except Exception as e:
                print(f"Failed to notify administrator {admin_id}: {e}")
        print("Bot status = 0, request_pair_feedback will not be executed")

def request_pair_feedback():
    # First, finalize all old pairs
    finalize_all_old_pairs()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT pair_id, user1_id, user2_id FROM pair_registry "
            "WHERE creation_date = (SELECT MAX(creation_date) FROM pair_registry) "
            "AND user1_id <> -1 AND user2_id <> -1"
        )
        pairs = cursor.fetchall()

        for pair_id, user1_id, user2_id in pairs:
            for user_id in [user1_id, user2_id]:
                try:
                    markup = types.InlineKeyboardMarkup()
                    yes_button = types.InlineKeyboardButton("Yes", callback_data=f"feedback_yes_{pair_id}_{user_id}")
                    no_button = types.InlineKeyboardButton("No", callback_data=f"feedback_no_{pair_id}_{user_id}")
                    markup.add(yes_button, no_button)

                    bot.send_message(user_id, "Did the meeting happen?", reply_markup=markup)

                except Exception as e:
                    # Notify all admins about the failure
                    for admin_id in ADMIN_IDS:
                        try:
                            bot.send_message(admin_id,
                                f"❗️Failed to send feedback message to user {user_id} for pair {pair_id}.\nError: {e}")
                        except Exception as admin_error:
                            print(f"Failed to notify admin {admin_id}: {admin_error}")
