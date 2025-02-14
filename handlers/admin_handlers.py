from telebot import TeleBot, types
from utils.db import *
from utils.pairing import run_pairing_process
from config import ADMIN_IDS
from utils.utils import *

def register_admin_handlers(bot: TeleBot):
    @bot.message_handler(commands=['start_pairing'])
    def handle_start_pairing(message):
        if message.chat.id in ADMIN_IDS:
            bot.send_message(message.chat.id, escape_markdown("Starting pair matching... ⏳"), parse_mode="MarkdownV2")
            run_pairing_process(bot)
            bot.send_message(message.chat.id, escape_markdown("Pair matching completed!"), parse_mode="MarkdownV2")
        else:
            bot.send_message(message.chat.id, escape_markdown("You do not have permission to execute this command."), parse_mode="MarkdownV2")

    @bot.message_handler(commands=['delete_user'])
    def delete_user(message):
        # Проверяем, является ли отправитель администратором
        if message.chat.id not in ADMIN_IDS:
            bot.send_message(message.chat.id, escape_markdown("You do not have permission to execute this command."), parse_mode="MarkdownV2")
            return

        # Запрашиваем ID или Telegram username пользователя
        bot.send_message(message.chat.id, escape_markdown("Please enter the user ID or Telegram username (e.g., @username) to delete:"), parse_mode="MarkdownV2")
        bot.register_next_step_handler(message, lambda msg: process_user_deletion(bot, msg))

    @bot.message_handler(commands=['user_info'])

    def user_info(message):
        """
        Allows admins to edit a user profile by selecting search criteria.
        """
        if not is_user_registered(message.chat.id):
            bot.send_message(message.chat.id, escape_markdown("Please register before using this command."), parse_mode="MarkdownV2")
            return

        # Check if the user is an admin
        if message.chat.id not in ADMIN_IDS:
            bot.send_message(message.chat.id, escape_markdown("🚨 You do not have permission to use this command."), parse_mode="MarkdownV2")
            return

        # Create buttons for search criteria
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Search by Username", callback_data="search_username"))
        markup.add(types.InlineKeyboardButton("Search by ID", callback_data="search_id"))
        markup.add(types.InlineKeyboardButton("Search by Name", callback_data="search_name"))

        bot.send_message(message.chat.id, escape_markdown("How would you like to search for the user?"), reply_markup=markup, parse_mode="MarkdownV2")

    @bot.message_handler(commands=['change_ban_status'])
    def change_ban_status(message):
        # Проверяем, является ли отправитель администратором
        if not is_user_registered(message.chat.id):
            bot.send_message(message.chat.id, escape_markdown("Please register before using this command."), parse_mode="MarkdownV2")
            return

        if message.chat.id not in ADMIN_IDS:
            bot.send_message(message.chat.id, escape_markdown("You do not have permission to execute this command."), parse_mode="MarkdownV2")
            return

        # Запрашиваем ID пользователя
        bot.send_message(message.chat.id, escape_markdown("Please enter the user ID:"), parse_mode="MarkdownV2")
        bot.register_next_step_handler(message, process_ban_status_change)

    @bot.message_handler(commands=['stats'])
    def stats(message):
        """
        Provides admin statistics about users and pair_registry tables.
        """
        # Проверка, зарегистрирован ли пользователь
        if not is_user_registered(message.chat.id):
            bot.send_message(message.chat.id, escape_markdown("Please register before using this command."), parse_mode="MarkdownV2")
            return

        # Проверка, является ли пользователь админом
        if message.chat.id not in ADMIN_IDS:
            bot.send_message(message.chat.id, escape_markdown("You do not have permission to use this command."), parse_mode="MarkdownV2")
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
            f"👥 Total Registered Users: {total_users}\n"
            f"🚻 Gender Distribution:\n" + ''.join([f"{line}\n" for line in gender_summary]) +
            f"🏙️ Top 3 Cities:\n" + ''.join([f"   - {city[0]}: {city[1]} users\n" for city in top_cities]) +
            f"🎓 Top 3 Programs:\n" + ''.join([f"   - {program[0]}: {program[1]} users\n" for program in top_programs]) +
            f"💼 Top 3 Occupations:\n" + ''.join([f"   - {occupation[0]}: {occupation[1]} users\n" for occupation in top_occupations]) +
            f"📈 Average Age: {avg_age:.1f}\n"
            f"🟢 Active Users: {active_users} ({active_percentage:.1f}% of total)\n"
            f"🤝 Total Pairs: {total_pairs}"
        )

        bot.send_message(message.chat.id, stats_message, parse_mode="Markdown")

    @bot.message_handler(commands=['broadcast_message'])
    def send_broadcast_message_ask(message):
        """
        Рассылает сообщение всем пользователям и уведомляет администраторов.
        """
        if message.chat.id not in ADMIN_IDS:
            bot.send_message(message.chat.id, escape_markdown("You do not have permission to use this command."), parse_mode="MarkdownV2")
            return

        bot.send_message(message.chat.id, escape_markdown("Please enter your message:"), parse_mode="MarkdownV2")
        bot.register_next_step_handler(message, lambda msg: send_broadcast_message(bot, msg))

    @bot.callback_query_handler(func=lambda call: call.data.startswith("search_"))
    def handle_search_criteria(call):
        """
        Handles the selected search criteria.
        """
        if call.data == "search_username":
            bot.send_message(call.message.chat.id, escape_markdown("Please enter the username (e.g., @username):"), parse_mode="MarkdownV2")
            bot.register_next_step_handler(call.message, lambda msg: search_by_username(bot, msg))
        elif call.data == "search_id":
            bot.send_message(call.message.chat.id, escape_markdown("Please enter the user ID:"), parse_mode="MarkdownV2")
            bot.register_next_step_handler(call.message, lambda msg: search_by_id(bot, msg))
        elif call.data == "search_name":
            bot.send_message(call.message.chat.id, escape_markdown("Please enter the name or part of the name:"), parse_mode="MarkdownV2")
            bot.register_next_step_handler(call.message, lambda msg: search_by_name(bot, msg))

    @bot.message_handler(commands=['set_status'])
    def set_bot_status(message):
        """
        Устанавливает статус бота (только 0 или 1) в таблице bot_status.
        """
        if message.chat.id not in ADMIN_IDS:
            bot.send_message(message.chat.id, escape_markdown("You do not have permission to do that."), parse_mode="MarkdownV2")
            return

        bot.send_message(message.chat.id, escape_markdown("Enter new status:"), parse_mode="MarkdownV2")
        bot.register_next_step_handler(message, lambda msg: process_bot_status_change(bot, msg))

