import telebot
from config import TOKEN
from code.utils.db import initialize_database
from handlers.user_handlers import register_user_handlers
from handlers.admin_handlers import register_admin_handlers
from scheduler import start_scheduler

def main():
    initialize_database()  # Создать таблицы, если их нет
    bot = telebot.TeleBot(TOKEN)

    bot.set_my_commands([
        telebot.types.BotCommand("/start", "Register and get started"),
        telebot.types.BotCommand("/help", "Show available commands"),
        telebot.types.BotCommand("/profile", "View your profile"),
        telebot.types.BotCommand("/about", "Learn about this bot"),
        telebot.types.BotCommand("/rules", "Read the usage rules"),
        telebot.types.BotCommand("/faq", "Frequently Asked Questions"),
        telebot.types.BotCommand("/pause", "Pause current activities"),
        telebot.types.BotCommand("/resume", "Resume activities"),
        telebot.types.BotCommand("/edit_profile", "Edit your profile"),
        telebot.types.BotCommand("/delete_profile", "Delete your profile"),
        telebot.types.BotCommand("/feedback", "Provide your feedback"),
        telebot.types.BotCommand("/skip", "Skip the current step")
    ])

    verification_codes = {}
    user_feedback = {}

    # Регистрируем пользовательские handlers
    register_user_handlers(bot, verification_codes, user_feedback)
    # Регистрируем admin handlers
    register_admin_handlers(bot)

    # Запуск планировщика в отдельном потоке
    start_scheduler(bot)

    # Запуск бота
    bot.polling(none_stop=True)

if __name__ == "__main__":
    main()