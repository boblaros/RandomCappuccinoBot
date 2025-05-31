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
                                 'Weekly pairing has started (every Monday at 10:00 AM, Milan time).')
            except Exception as e:
                print(f"Failed to notify administrator {admin_id}: {e}")
        run_pairing_process()
    else:
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id,
                                 'Pairing was not started because the bot is turned off (status = 0).')
            except Exception as e:
                print(f"Failed to notify administrator {admin_id}: {e}")
        print("Bot status = 0, run_pairing_process will not be executed")


def check_bot_status_and_feedback():
    check_bot_status_and_get_feedback()

def start_scheduler(bot):
    italy_tz = pytz.timezone("Europe/Rome")
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        lambda: check_bot_status_and_run(bot),
        CronTrigger(day_of_week='mon', hour=10, minute=0, timezone=italy_tz)
    )

    scheduler.add_job(
        lambda: check_bot_status_and_feedback(),
        CronTrigger(day_of_week='sun', hour=10, minute=0, timezone=italy_tz)
    )

    time.sleep(5)
    scheduler.start()
    print("The scheduler has started. Waiting for the task to execute...")