from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import time

from utils.pairing import run_pairing_process, check_bot_status_and_get_feedback
from utils.db import get_bot_status
from config import ADMIN_IDS

def check_bot_status_and_run(bot):
    status = get_bot_status()
    if status == 1:
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id,
                                 'Запускается подбор пар в рамках пилота (10:00 по Милану каждый день)')
            except Exception as e:
                print(f"Не удалось уведомить администратора {admin_id}: {e}")
        run_pairing_process(bot)
    else:
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id,
                                 'Подбор пар не запускается, бот выключен (status = 0).')
            except Exception as e:
                print(f"Не удалось уведомить администратора {admin_id}: {e}")
        print("Статус бота = 0, не запускаем run_pairing_process")

def check_bot_status_and_feedback(bot):
    check_bot_status_and_get_feedback(bot)

def start_scheduler(bot):
    italy_tz = pytz.timezone("Europe/Rome")
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        lambda: check_bot_status_and_run(bot),
        CronTrigger(day_of_week='mon', hour=10, minute=0, timezone=italy_tz)
    )

    scheduler.add_job(
        lambda: check_bot_status_and_feedback(bot),
        CronTrigger(day_of_week='sun', hour=10, minute=0, timezone=italy_tz)
    )

    time.sleep(5)
    scheduler.start()
    print("Планировщик запущен. Ожидание выполнения задачи...")