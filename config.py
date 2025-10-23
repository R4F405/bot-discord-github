import os
from dotenv import load_dotenv

# Carga las variables del archivo .env
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
# Convertimos el ID del canal a entero
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID", 0))

if not DISCORD_TOKEN or not GITHUB_WEBHOOK_SECRET or TARGET_CHANNEL_ID == 0:
    raise ValueError("Error: Faltan variables de entorno críticas (TOKEN, SECRET o CHANNEL_ID).")