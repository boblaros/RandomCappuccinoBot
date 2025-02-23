from telebot import types
from utils.db import *
from utils.pairing import run_pairing_process
from config import ADMIN_IDS
from utils.utils import *

def register_admin_handlers(admin_bot):
    @admin_bot.message_handler(commands=['start_pairing'])
    def handle_start_pairing(message):
        if message.chat.id in ADMIN_IDS:
            admin_bot.send_message(message.chat.id, "Starting pair matching... ⏳")
            run_pairing_process(bot)
            admin_bot.send_message(message.chat.id, "Pair matching completed!")
        else:
            admin_bot.send_message(message.chat.id, "You do not have permission to execute this command.")

    @admin_bot.message_handler(commands=['delete_user'])
    def delete_user(message):
        # Проверяем, является ли отправитель администратором
        if message.chat.id not in ADMIN_IDS:
            admin_bot.send_message(message.chat.id, "You do not have permission to execute this command.")
            return

        # Запрашиваем ID или Telegram username пользователя
        admin_bot.send_message(message.chat.id, "Please enter the user ID or Telegram username (e.g., @username) to delete:")
        admin_bot.register_next_step_handler(message, lambda msg: process_user_deletion(admin_bot, msg))

    @admin_bot.message_handler(commands=['user_info'])
    def user_info(message):
        """
        Allows admins to edit a user profile by selecting search criteria.
        """
        if not is_user_registered(message.chat.id):
            admin_bot.send_message(message.chat.id, "Please register before using this command.")
            return

        # Check if the user is an admin
        if message.chat.id not in ADMIN_IDS:
            admin_bot.send_message(message.chat.id, "🚨 You do not have permission to use this command.")
            return

        # Create buttons for search criteria
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Search by Username", callback_data="search_username"))
        markup.add(types.InlineKeyboardButton("Search by ID", callback_data="search_id"))
        markup.add(types.InlineKeyboardButton("Search by Name", callback_data="search_name"))

        admin_bot.send_message(message.chat.id, "How would you like to search for the user?", reply_markup=markup)

    @admin_bot.message_handler(commands=['change_ban_status'])
    def change_ban_status(message):
        """
        Проверяет права администратора и запрашивает ID пользователя.
        """
        if not is_user_registered(message.chat.id):
            admin_bot.send_message(
                message.chat.id,
                escape_markdown_v2("Please register before using this command."),
                parse_mode="MarkdownV2"
            )
            return

        if message.chat.id not in ADMIN_IDS:
            admin_bot.send_message(
                message.chat.id,
                escape_markdown_v2("You do not have permission to execute this command."),
                parse_mode="MarkdownV2"
            )
            return

        admin_bot.send_message(
            message.chat.id,
            escape_markdown_v2("Please enter the user ID:"),
            parse_mode="MarkdownV2"
        )
        admin_bot.register_next_step_handler(message, lambda msg: handle_ban_status_input(bot, msg))

    @admin_bot.message_handler(commands=['stats'])
    def stats(message):
        """
        Provides admin statistics about users and pair_registry tables.
        """
        # Проверка, зарегистрирован ли пользователь
        if not is_user_registered(message.chat.id):
            admin_bot.send_message(message.chat.id, "Please register before using this command.")
            return

        # Проверка, является ли пользователь админом
        if message.chat.id not in ADMIN_IDS:
            admin_bot.send_message(message.chat.id, "You do not have permission to use this command.")
            return

        # Получаем статистику из БД
        stats_data = get_bot_statistics()

        # Распаковываем нужные поля
        total_users      = stats_data['total_users']
        gender_stats     = stats_data['gender_stats']
        top_cities       = stats_data['top_cities']
        top_programs     = stats_data['top_programs']
        top_occupations  = stats_data['top_occupations']
        avg_age          = stats_data['avg_age']
        active_users     = stats_data['active_users']
        total_pairs      = stats_data['total_pairs']

        # Обрабатываем часть о gender
        gender_mapping = {0: "Male", 1: "Female", -1: "Skipped"}
        gender_summary = [
            f"   - {gender_mapping.get(row[0], 'Unknown')}: {row[1]} users"
            for row in gender_stats
        ]

        # Считаем процент активных
        active_percentage = (active_users / total_users) * 100 if total_users > 0 else 0

        # Формируем итоговое сообщение
        stats_message = (
                f"📊 *Bot Statistics*\n\n"
                f"👥 Total Registered Users: {escape_markdown_v2(total_users)}\n"
                f"🚻 Gender Distribution:\n" + ''.join([f"{escape_markdown_v2(line)}\n" for line in gender_summary]) +
                f"🏙️ Top 3 Cities:\n" + ''.join(
            [f"   \- {escape_markdown_v2(city[0])}: {escape_markdown_v2(city[1])} users\n" for city in top_cities]) +
                f"🎓 Top 3 Programs:\n" + ''.join(
            [f"   \- {escape_markdown_v2(program[0])}: {escape_markdown_v2(program[1])} users\n" for program in
             top_programs]) +
                f"💼 Top 3 Occupations:\n" + ''.join(
            [f"   \- {escape_markdown_v2(occupation[0])}: {escape_markdown_v2(occupation[1])} users\n" for occupation in
             top_occupations]) +
                f"📈 Average Age: {escape_markdown_v2(f'{avg_age:.1f}')}\n"
                f"🟢 Active Users: {escape_markdown_v2(active_users)} \({escape_markdown_v2(f'{active_percentage:.1f}')}% of total\)\n"
                f"🤝 Total Pairs: {escape_markdown_v2(total_pairs)}"
        )

        admin_bot.send_message(message.chat.id, stats_message, parse_mode="MarkdownV2")

    @admin_bot.message_handler(commands=['broadcast_message'])
    def send_broadcast_message_ask(message):
        """
        Рассылает сообщение всем пользователям и уведомляет администраторов.
        """
        if message.chat.id not in ADMIN_IDS:
            admin_bot.send_message(message.chat.id, "You do not have permission to use this command.")
            return

        admin_bot.send_message(message.chat.id, "Please enter your message:")
        admin_bot.register_next_step_handler(message, lambda msg: send_broadcast_message(bot, msg))

    @admin_bot.callback_query_handler(func=lambda call: call.data.startswith("search_"))
    def handle_search_criteria(call):
        """
        Handles the selected search criteria.
        """
        search_options = {
            "search_username": "Search by Username",
            "search_id": "Search by ID",
            "search_name": "Search by Name"
        }

        selected_option = search_options.get(call.data, "Unknown option")

        # Убираем кнопки и заменяем текст сообщения
        admin_bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"How would you like to search for the user?\n\n👉 *{selected_option}*",
            parse_mode="Markdown"
        )


        if call.data == "search_username":
            admin_bot.send_message(call.message.chat.id, "Please enter the username (e.g., @username):")
            admin_bot.register_next_step_handler(call.message, lambda msg: search_by_username(bot, msg))
        elif call.data == "search_id":
            admin_bot.send_message(call.message.chat.id, "Please enter the user ID:")
            admin_bot.register_next_step_handler(call.message, lambda msg: search_by_id(bot, msg))
        elif call.data == "search_name":
            admin_bot.send_message(call.message.chat.id, "Please enter the name or part of the name:")
            admin_bot.register_next_step_handler(call.message, lambda msg: search_by_name(bot, msg))

    @admin_bot.message_handler(commands=['set_status'])
    def set_bot_status(message):
        """
        Устанавливает статус бота (только 0 или 1) в таблице bot_status.
        """
        if message.chat.id not in ADMIN_IDS:
            admin_bot.send_message(message.chat.id, "You do not have permission to do that.")
            return

        admin_bot.send_message(message.chat.id, "Enter new status:")
        admin_bot.register_next_step_handler(message, lambda msg: process_bot_status_change(bot, msg))

