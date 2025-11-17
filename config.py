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

# Health-check server (לרנדר)
ENABLE_HEALTHCHECK_SERVER = os.getenv('ENABLE_HEALTHCHECK_SERVER', 'true').lower() not in {'false', '0', 'no', 'off'}
try:
    HEALTHCHECK_PORT = int(os.getenv('PORT') or os.getenv('HEALTHCHECK_PORT') or 8000)
except (TypeError, ValueError):
    HEALTHCHECK_PORT = 8000

# Distributed lock (Mongo-based)
# Service identity
SERVICE_ID = os.getenv('SERVICE_ID', 'telegram-bot')
RENDER_SERVICE_NAME = os.getenv('RENDER_SERVICE_NAME', os.getenv('RENDER_SERVICE_ID', 'render-service'))
RENDER_INSTANCE_ID = os.getenv('RENDER_INSTANCE_ID')  # may be None; will fallback to hostname:pid

# Lease/heartbeat settings
def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default

LOCK_LEASE_SECONDS = _int_env('LOCK_LEASE_SECONDS', 60)
_hb_default = max(5, int(LOCK_LEASE_SECONDS * 0.4))
LOCK_HEARTBEAT_INTERVAL = _int_env('LOCK_HEARTBEAT_INTERVAL', _hb_default)

# Acquire behavior
def _bool_env(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).lower() not in {'false', '0', 'no', 'off', ''}

LOCK_WAIT_FOR_ACQUIRE = _bool_env('LOCK_WAIT_FOR_ACQUIRE', False)
LOCK_ACQUIRE_MAX_WAIT = _int_env('LOCK_ACQUIRE_MAX_WAIT', 0)  # 0 = no limit

# Passive wait backoff window (seconds)
LOCK_WAIT_MIN_SECONDS = _int_env('LOCK_WAIT_MIN_SECONDS', 15)
LOCK_WAIT_MAX_SECONDS = _int_env('LOCK_WAIT_MAX_SECONDS', 45)
