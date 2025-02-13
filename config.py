import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), 'config.env'))

ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS').split(',')))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TOKEN = os.getenv("TOKEN")

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465

PROD_DB_PATH = '/data/random_cappuccino.db'

# Относительный путь для локальной разработки
DEV_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/random_cappuccino.db'))

# Логика определения пути
if os.path.exists('/data'):
    DB_PATH = PROD_DB_PATH
else:
    DB_PATH = DEV_DB_PATH