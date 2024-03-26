import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dadata import Dadata

import requests
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

SECRET_AUTH = os.environ.get("SECRET_AUTH")

SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = int(os.environ.get("SMTP_PORT"))
SMTP_SSL = os.environ.get("SMTP_SSL")
SMTP_LOGIN = os.environ.get("SMTP_LOGIN")
SMTP_PASS = os.environ.get("SMTP_PASS")

DADATA_KEY = os.environ.get("DADATA_KEY")

MANAGER_EMAIL = os.environ.get("MANAGER_EMAIL")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")


class Settings(BaseModel):
    authjwt_secret_key: str = SECRET_AUTH
    authjwt_algorithm: str = "HS256"
    authjwt_access_token_expires: int = 60 * 60 * 72  # default 15 minute
    authjwt_refresh_token_expires: int = 31000000  # default 30 days


def send_email(recipient_email, subject, message):
    msg = MIMEMultipart()
    msg['From'] = SMTP_LOGIN
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_LOGIN, SMTP_PASS)
        smtp.send_message(msg)


def send_tg(telegram_id, message):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    params = {
        'chat_id': telegram_id,
        'text': message,
    }
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        print(f"Сообщение успешно отправлено в Telegram для пользователя с ID {telegram_id}")
        return 0
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при отправке сообщения в Telegram: {e}")
        return 0


def get_address_data(address):
    dadata = Dadata(DADATA_KEY)
    try:
        data = dadata.suggest("address", address)
        return {
            'lat': float(data[0]['data']['geo_lat']),
            'lon': float(data[0]['data']['geo_lon']),
            'country': data[0]['data']['country'],
        }
    except Exception as e:
        print(f"An error occurred: {e}")
        return {
            'lat': None,
            'lon': None,
            'country': None,
        }
