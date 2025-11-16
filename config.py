"""
הגדרות הבוט - Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))

# MongoDB
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'prompttracker')

# Redis (אופציונלי)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

# Environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# Categories
CATEGORIES = {
    '🤖': 'Bots',
    '🎨': 'Design',
    '📚': 'Documentation',
    '💻': 'Code',
    '✍️': 'Writing',
    '📊': 'Data',
    '🔍': 'Research',
    '📧': 'Communication',
    '🎓': 'Education',
    '⚙️': 'Other'
}

CATEGORY_EMOJIS = {v: k for k, v in CATEGORIES.items()}

# הגדרות כלליות
MAX_PROMPT_LENGTH = 4000  # אורך מקסימלי לפרומפט
PROMPTS_PER_PAGE = 10     # כמה פרומפטים בעמוד
MAX_TAGS = 10             # מקסימום תגיות לפרומפט
TRASH_RETENTION_DAYS = 30 # כמה ימים לשמור פרומפטים במחיקה
