import os
from pathlib import Path
from dotenv import load_dotenv

dotenv_path = Path(__file__).parent / 'config.env'
load_dotenv(dotenv_path)

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DB_HOST = os.getenv('HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('PASSWORD')
DB_NAME = os.getenv('DATABASE')
