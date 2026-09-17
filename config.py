import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
BASE=Path(__file__).parent; DATA=BASE/'data'; DATA.mkdir(exist_ok=True)
BOT_TOKEN=os.getenv('BOT_TOKEN','').strip(); BOT_NAME=os.getenv('BOT_NAME','PIT DIVERSÃO')
DATABASE_PATH=os.getenv('DATABASE_PATH',str(DATA/'pit_diversao.db'))
CHALLENGE_POINTS=int(os.getenv('DEFAULT_CHALLENGE_POINTS','10')); WEEKLY_PRIZE=os.getenv('DEFAULT_WEEKLY_PRIZE','Banca/prêmio configurável')
TIMEZONE=os.getenv('TIMEZONE','America/Sao_Paulo'); MORNING_HOUR=int(os.getenv('MORNING_HOUR','8')); NIGHT_HOUR=int(os.getenv('NIGHT_HOUR','22')); AUTO_CHALLENGE_HOUR=int(os.getenv('AUTO_CHALLENGE_HOUR','12'))

BACKUP_INTERVAL = int(os.getenv('BACKUP_INTERVAL','21600'))  # 6 horas
