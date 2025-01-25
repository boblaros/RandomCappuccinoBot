import schedule
import time
import threading
from code.utils.pairing import run_pairing_process, check_bot_status_and_get_feedback
from code.utils.db import get_bot_status

def check_bot_status_and_run(bot):
    status = get_bot_status()
    if status == 1:
        run_pairing_process(bot)
    else:
        print("Статус бота = 0, не запускаем run_pairing_process")

def check_bot_status_and_feedback(bot):
    check_bot_status_and_get_feedback(bot)

def schedule_pairing(bot):
    # Планируем запуск check_bot_status_and_run каждый день в 10:00
    schedule.every().day.at("10:00").do(lambda: check_bot_status_and_run(bot))

    # Планируем запуск check_bot_status_and_feedback каждый день в 21:00
    schedule.every().day.at("21:00").do(lambda: check_bot_status_and_feedback(bot))

    while True:
        schedule.run_pending()  # Проверяет и запускает задачи
        time.sleep(1)  # Пауза на 1 секунду

def start_scheduler(bot):
    thread = threading.Thread(target=schedule_pairing, args=(bot,))
    thread.start()