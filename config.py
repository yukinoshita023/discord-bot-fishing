import os
from dotenv import load_dotenv

# 環境変数をロード
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

ADMIN_ROLE_ID = 946432769242845224  # 管理課ロール