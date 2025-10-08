import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")  # токен из .env
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))  # ID из .env

GOOGLE_CREDENTIALS_FILE = "credentials.json"
GOOGLE_SHEET_NAME = "RealEstateAcademy_Leads"
