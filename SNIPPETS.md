# 📚 Telegram Bot Code Snippets Library

ספריית קטעי קוד לבניית בוטים בטלגרם - מוכן להעתקה והדבקה.  
**סניפטים ייחודיים שלא קיימים בספרייה הראשית**

---

## 🚀 אתחול והגדרות

### 1. אתחול בוט מלא עם כל ה-Handlers

**למה זה שימושי:** תבנית מלאה לבוט עם כל סוגי ה-handlers בסדר הנכון.

```python
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Conversation handlers (מוסיפים לפני callback handlers)
    application.add_handler(save_conversation_handler)
    application.add_handler(search_conversation_handler)
    
    # Callback handlers (בסדר ספציפי לכללי)
    application.add_handler(CallbackQueryHandler(view_details, pattern="^view_"))
    application.add_handler(CallbackQueryHandler(copy_item, pattern="^copy_"))
    application.add_handler(CallbackQueryHandler(button_handler))  # catch-all
    
    # Message handlers
    application.add_handler(MessageHandler(
        filters.Regex(r"^/view_[0-9a-fA-F]{24}$"), 
        handle_view_command_text
    ))
    
    # Error handler (אחרון!)
    application.add_error_handler(error_handler)
    
    logger.info("🚀 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
```

---

### 2. Health Check עם HEAD Support

**למה זה שימושי:** תמיכה גם ב-HEAD requests לבדיקות בריאות יעילות יותר.

```python
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._send_response()
    
    def do_HEAD(self):
        self._send_response(send_body=False)
    
    def _send_response(self, send_body: bool = True):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        if send_body:
            self.wfile.write(b"ok")
    
    def log_message(self, format, *args):
        return

def start_healthcheck_server():
    port = int(os.getenv('PORT', 8000))
    health_server = HTTPServer(("", port), HealthHandler)
    thread = threading.Thread(
        target=health_server.serve_forever,
        daemon=True
    )
    thread.start()
    logger.info(f"Health-check listening on port {port}")
```

---

### 3. טעינת הגדרות עם Fallbacks

**למה זה שימושי:** הגדרות ברירת מחדל כשמשתנה סביבה חסר.

```python
import os
from dotenv import load_dotenv

load_dotenv()

# הגדרות חובה
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required!")

# הגדרות אופציונליות עם fallback
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'mybot')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# Boolean מ-string
ENABLE_HEALTHCHECK = os.getenv('ENABLE_HEALTHCHECK', 'true').lower() not in {
    'false', '0', 'no', 'off'
}

# Int עם try/except
try:
    HEALTHCHECK_PORT = int(os.getenv('PORT') or os.getenv('HEALTHCHECK_PORT') or 8000)
except (TypeError, ValueError):
    HEALTHCHECK_PORT = 8000
```

---

## 🗄️ MongoDB ומסדי נתונים

### 4. Multi-Collection Index Setup

**למה זה שימושי:** יצירת אינדקסים על כל ה-collections בפעם אחת.

```python
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT

class Database:
    def __init__(self, mongo_uri, db_name):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.prompts = self.db.prompts
        self.users = self.db.users
        self.collections = self.db.collections
        self.stats = self.db.stats
        self._create_indexes()
    
    def _create_indexes(self):
        # אינדקסים לפרומפטים
        self.prompts.create_index([("user_id", ASCENDING)])
        self.prompts.create_index([("category", ASCENDING)])
        self.prompts.create_index([("tags", ASCENDING)])
        self.prompts.create_index([("created_at", DESCENDING)])
        self.prompts.create_index([("title", TEXT), ("content", TEXT)])
        self.prompts.create_index([("is_deleted", ASCENDING)])
        
        # אינדקס ייחודי למשתמשים
        self.users.create_index([("user_id", ASCENDING)], unique=True)
```

---

### 5. Get or Create עם Settings ברירת מחדל

**למה זה שימושי:** משתמש חדש מקבל הגדרות מוכנות מראש.

```python
from datetime import datetime

def get_or_create_user(self, user_id: int, username: str = None, 
                      first_name: str = None):
    user = self.users.find_one({"user_id": user_id})
    
    if not user:
        user = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "created_at": datetime.utcnow(),
            "settings": {
                "show_ids": False,
                "short_titles": True,
                "show_tags": True,
                "copy_confirmation": True,
                "theme": "dark"
            },
            "stats": {
                "total_prompts": 0,
                "total_uses": 0,
                "total_collections": 0
            }
        }
        self.users.insert_one(user)
    
    return user
```

---

### 6. חיפוש מתקדם עם מספר פילטרים

**למה זה שימושי:** חיפוש גמיש עם קטגוריה, תגיות ומועדפים.

```python
from typing import List, Optional

def search_prompts(self, user_id: int, query: str = None, 
                  category: str = None, tags: List[str] = None,
                  favorites_only: bool = False, 
                  skip: int = 0, limit: int = 10):
    """חיפוש פרומפטים עם סינון מתקדם"""
    filter_query = {
        "user_id": user_id,
        "is_deleted": False
    }
    
    # חיפוש טקסט מלא
    if query:
        filter_query["$text"] = {"$search": query}
    
    # סינון לפי קטגוריה
    if category:
        filter_query["category"] = category
    
    # סינון לפי תגיות (OR)
    if tags:
        filter_query["tags"] = {"$in": tags}
    
    # מועדפים בלבד
    if favorites_only:
        filter_query["is_favorite"] = True
    
    prompts = list(self.prompts.find(filter_query)
                  .sort("created_at", DESCENDING)
                  .skip(skip)
                  .limit(limit))
    
    return prompts
```

---

### 7. Restore מהאשפה

**למה זה שימושי:** שחזור פריט שנמחק בטעות.

```python
def restore_prompt(self, prompt_id: str, user_id: int) -> bool:
    """שחזור פרומפט מהאשפה"""
    from bson import ObjectId
    try:
        result = self.prompts.update_one(
            {"_id": ObjectId(prompt_id), "user_id": user_id},
            {
                "$set": {"is_deleted": False}, 
                "$unset": {"deleted_at": ""}
            }
        )
        if result.modified_count > 0:
            self.update_user_stats(user_id, "total_prompts", 1)
            return True
        return False
    except:
        return False
```

---

### 8. Increment Use Count (מעקב שימוש)

**למה זה שימושי:** ספירת כמה פעמים פריט שומש - לפופולריות.

```python
def increment_use_count(self, prompt_id: str, user_id: int):
    """הגדלת מונה שימושים"""
    from bson import ObjectId
    try:
        self.prompts.update_one(
            {"_id": ObjectId(prompt_id), "user_id": user_id},
            {"$inc": {"use_count": 1}}
        )
        self.update_user_stats(user_id, "total_uses")
    except:
        pass

# שימוש:
# כשמשתמש מעתיק פרומפט
db.increment_use_count(prompt_id, user.id)
```

---

### 9. Aggregation עם Unwind (תגיות פופולריות)

**למה זה שימושי:** פירוק מערכים וספירת תגיות הכי נפוצות.

```python
def get_popular_tags(self, user_id: int, limit: int = 5):
    """קבלת תגיות פופולריות"""
    pipeline = [
        {"$match": {"user_id": user_id, "is_deleted": False}},
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]
    
    results = list(self.prompts.aggregate(pipeline))
    return [r['_id'] for r in results]
```

---

### 10. ניקוי אוטומטי של Trash עם Threshold

**למה זה שימושי:** מחיקה אוטומטית של פריטים ישנים מהאשפה.

```python
from datetime import datetime, timedelta

def cleanup_old_trash(self, retention_days: int = 30):
    """מחיקה סופית של פרומפטים ישנים באשפה"""
    threshold = datetime.utcnow() - timedelta(days=retention_days)
    result = self.prompts.delete_many({
        "is_deleted": True,
        "deleted_at": {"$lt": threshold}
    })
    return result.deleted_count

# הפעלה יומית (cron או scheduler):
deleted_count = db.cleanup_old_trash(retention_days=30)
logger.info(f"Cleaned up {deleted_count} old items from trash")
```

---

## ⌨️ Inline Keyboards (מקלדות)

### 11. Dynamic Category Keyboard (בניה אוטומטית)

**למה זה שימושי:** בניית מקלדת קטגוריות דינמית משמירת dict.

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CATEGORIES = {
    '🤖': 'Bots',
    '🎨': 'Design',
    '📚': 'Documentation',
    '💻': 'Code',
    '✍️': 'Writing',
    '📊': 'Data',
    '⚙️': 'Other'
}

def category_keyboard(include_all: bool = True):
    """מקלדת בחירת קטגוריה"""
    keyboard = []
    categories = list(CATEGORIES.items())
    
    # שתי קטגוריות בשורה
    for i in range(0, len(categories), 2):
        row = []
        for j in range(2):
            if i + j < len(categories):
                emoji, name = categories[i + j]
                row.append(InlineKeyboardButton(
                    f"{emoji} {name}",
                    callback_data=f"cat_{name}"
                ))
        keyboard.append(row)
    
    if include_all:
        keyboard.append([
            InlineKeyboardButton("📋 כל הקטגוריות", callback_data="cat_all")
        ])
    
    keyboard.append([
        InlineKeyboardButton("« חזרה", callback_data="back_main")
    ])
    
    return InlineKeyboardMarkup(keyboard)
```

---

### 12. Edit Menu (תפריט עריכה מורכב)

**למה זה שימושי:** תפריט מובנה לכל אפשרויות העריכה.

```python
def edit_menu_keyboard(prompt_id: str):
    """תפריט עריכה"""
    keyboard = [
        [
            InlineKeyboardButton("📝 ערוך תוכן", callback_data=f"edit_content_{prompt_id}"),
        ],
        [
            InlineKeyboardButton("📋 ערוך כותרת", callback_data=f"edit_title_{prompt_id}"),
        ],
        [
            InlineKeyboardButton("📁 שנה קטגוריה", callback_data=f"chcat_{prompt_id}"),
        ],
        [
            InlineKeyboardButton("🏷️ נהל תגיות", callback_data=f"tags_{prompt_id}"),
        ],
        [
            InlineKeyboardButton("« חזרה", callback_data=f"view_{prompt_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
```

---

### 13. Tag Management Keyboard (ניהול תגיות)

**למה זה שימושי:** רשימה אינטראקטיבית של תגיות עם כפתור מחיקה.

```python
from typing import List

def tag_management_keyboard(prompt_id: str, existing_tags: List[str]):
    """מקלדת ניהול תגיות"""
    keyboard = []
    
    # תגיות קיימות - כל תגית עם כפתור מחיקה
    for tag in existing_tags:
        keyboard.append([
            InlineKeyboardButton(
                f"🏷️ {tag}",
                callback_data="noop"  # תגית עצמה לא לחיצה
            ),
            InlineKeyboardButton(
                "🗑️",
                callback_data=f"rmtag_{prompt_id}_{tag}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("➕ הוסף תגית חדשה", callback_data=f"addtag_{prompt_id}")
    ])
    
    keyboard.append([
        InlineKeyboardButton("« חזרה", callback_data=f"view_{prompt_id}")
    ])
    
    return InlineKeyboardMarkup(keyboard)
```

---

### 14. Prompt List Item (פריט ברשימה)

**למה זה שימושי:** כפתורים בשורה אחת לכל פריט ברשימה.

```python
def prompt_list_item_keyboard(prompt_id: str):
    """כפתורים לפרומפט ברשימה"""
    keyboard = [
        [
            InlineKeyboardButton("👁️ צפה", callback_data=f"view_{prompt_id}"),
            InlineKeyboardButton("📋 העתק", callback_data=f"copy_{prompt_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
```

---

### 15. Multi-Row Actions (3 שורות פעולות)

**למה זה שימושי:** תפריט פעולות מקיף עם שינוי קטגוריה ותגיות.

```python
def prompt_actions_keyboard(prompt_id: str, is_favorite: bool = False):
    """תפריט פעולות על פרומפט"""
    fav_text = "💔 הסר מועדפים" if is_favorite else "⭐ הוסף למועדפים"
    
    keyboard = [
        [
            InlineKeyboardButton("📋 העתק", callback_data=f"copy_{prompt_id}"),
            InlineKeyboardButton(fav_text, callback_data=f"fav_{prompt_id}")
        ],
        [
            InlineKeyboardButton("✏️ ערוך", callback_data=f"edit_{prompt_id}"),
            InlineKeyboardButton("🗑️ מחק", callback_data=f"delete_{prompt_id}")
        ],
        [
            InlineKeyboardButton("📁 שנה קטגוריה", callback_data=f"chcat_{prompt_id}"),
            InlineKeyboardButton("🏷️ נהל תגיות", callback_data=f"tags_{prompt_id}")
        ],
        [
            InlineKeyboardButton("« חזרה לרשימה", callback_data="my_prompts")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
```

---

## 💬 פקודות ו-Handlers

### 16. פקודת Start עם HTML מלא

**למה זה שימושי:** פקודת פתיחה עשירה עם HTML formatting ורישום משתמש.

```python
from utils import escape_html

async def start_command(update: Update, context):
    """פקודת /start"""
    user = update.effective_user
    
    # יצירת/עדכון משתמש
    db.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    welcome_text = (
        f"👋 שלום {escape_html(user.first_name)}!\n\n"
        f"ברוך הבא ל-<b>PromptTracker</b> 🚀\n\n"
        f"אני אעזור לך לנהל ולארגן את כל הפרומפטים שלך "
        f"למודלים של AI (ChatGPT, Claude, Midjourney ועוד).\n\n"
        f"📋 <b>מה אני יכול לעשות?</b>\n"
        f"• 💾 שמור פרומפטים בקלות\n"
        f"• 🔍 חפש ומצא במהירות\n"
        f"• 📁 ארגן לפי קטגוריות\n"
        f"• 🏷️ סמן עם תגיות\n"
        f"• ⭐ שמור מועדפים\n"
        f"• 📋 העתק בלחיצה אחת\n\n"
        f"בחר פעולה מהתפריט למטה:"
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=main_menu_keyboard()
    )
```

---

### 17. Callback Query Handler עם back_main

**למה זה שימושי:** handler מרכזי שמטפל בכפתור "חזרה" ו-noop.

```python
async def button_handler(update: Update, context):
    """טיפול בלחיצות על כפתורים"""
    query = update.callback_query
    data = query.data
    
    # חזרה לתפריט ראשי
    if data == "back_main":
        await query.answer()
        await query.edit_message_text(
            "📋 <b>PromptTracker</b>\n\nבחר פעולה:",
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )
        return
    
    # noop - כפתור לא פעיל (לתצוגה בלבד)
    if data == "noop":
        await query.answer()
        return
```

---

### 18. ConversationHandler מלא (3 שלבים)

**למה זה שימושי:** זרימה מורכבת עם content → title → category.

```python
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters

WAITING_FOR_PROMPT, WAITING_FOR_TITLE, WAITING_FOR_CATEGORY = range(3)

save_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_save_prompt, pattern="^new_prompt$"),
        CommandHandler("save", start_save_prompt)
    ],
    states={
        WAITING_FOR_PROMPT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prompt_content)
        ],
        WAITING_FOR_TITLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prompt_title)
        ],
        WAITING_FOR_CATEGORY: [
            CallbackQueryHandler(receive_prompt_category, pattern="^cat_")
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_save),
        CallbackQueryHandler(cancel_save, pattern="^back_main$")
    ]
)

application.add_handler(save_conv)
```

---

### 19. Context User Data עם Clear

**למה זה שימושי:** ניהול נכון של state זמני עם ניקוי.

```python
async def start_edit_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """עריכת תוכן"""
    query = update.callback_query
    await query.answer()
    
    prompt_id = query.data.replace('edit_content_', '')
    context.user_data['editing_prompt_id'] = prompt_id
    
    await query.edit_message_text(
        "📝 <b>עריכת תוכן</b>\n\n"
        "שלח את התוכן החדש לפרומפט.\n\n"
        "או שלח /cancel לביטול.",
        parse_mode='HTML'
    )
    
    return EDITING_CONTENT

async def receive_new_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """קבלת תוכן חדש"""
    user = update.effective_user
    new_content = update.message.text
    prompt_id = context.user_data.get('editing_prompt_id')
    
    if not prompt_id:
        await update.message.reply_text("⚠️ שגיאה: לא נמצא פרומפט לעריכה")
        return ConversationHandler.END
    
    success = db.update_prompt(prompt_id, user.id, {
        'content': new_content,
        'length': len(new_content)
    })
    
    if success:
        await update.message.reply_text(
            "✅ התוכן עודכן בהצלחה!",
            reply_markup=back_button(f"view_{prompt_id}")
        )
    else:
        await update.message.reply_text("⚠️ שגיאה בעדכון התוכן")
    
    context.user_data.clear()  # חשוב! ניקוי state
    return ConversationHandler.END
```

---

### 20. Command Text Handler (תמיכה ב-/view_<id>)

**למה זה שימושי:** טיפול בפקודות עם ID משולב בטקסט.

```python
async def handle_view_command_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """תמיכה בפקודת /view וב-/view_<id> הנשלחים כטקסט"""
    message = update.message
    prompt_id = None

    if message and message.text:
        text = message.text.strip()
        # צורה 1: /view_<id>
        if text.startswith('/view_'):
            prompt_id = text.split('/view_', 1)[1].strip()
        # צורה 2: /view <id>
        elif context.args:
            prompt_id = context.args[0]

    if not prompt_id:
        await update.message.reply_text("⚠️ שימוש: /view <prompt_id>")
        return

    # איחוד הזרימה דרך נתיב ה-callback הקיים
    context.user_data['callback_data'] = f"view_{prompt_id}"
    await view_prompt_details(update, context)

# רישום:
application.add_handler(CommandHandler("view", handle_view_command_text))
application.add_handler(MessageHandler(
    filters.Regex(r"^/view_[0-9a-fA-F]{24}$"), 
    handle_view_command_text
))
```

---

## 🛡️ אבטחה ותצוגה

### 21. Utils Module מלא (HTML Escape + Code Formatting)

**למה זה שימושי:** מודול utilities שלם לעיבוד טקסט בטוח.

```python
"""
Utilities for safely rendering text in Telegram with HTML parse mode.
"""
from typing import Any

def escape_html(value: Any) -> str:
    """Escape &, <, > for Telegram HTML parse mode.
    
    Accepts any value and returns a safe string.
    """
    if value is None:
        return ""
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

def code_inline(value: Any) -> str:
    """Wrap a short value as inline code, HTML-escaped."""
    return f"<code>{escape_html(value)}</code>"

def code_block(value: Any) -> str:
    """Wrap a value in a pre/code block, HTML-escaped."""
    return f"<pre><code>{escape_html(value)}</code></pre>"

# שימוש:
text = f"מזהה: {code_inline(item_id)}\n"
text += f"שם: {escape_html(user_input)}\n\n"
text += f"תוכן:\n{code_block(content)}"
```

---

## 📊 תצוגת רשימות ונתונים

### 22. View List עם Emoji וקטגוריות

**למה זה שימושי:** תצוגת רשימה עשירה עם אייקונים, מועדפים, ותגיות.

```python
import config

async def view_my_prompts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הצגת רשימת הפרומפטים"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user = update.effective_user
    
    # קבלת מספר העמוד
    page = 0
    if query and query.data.startswith('page_'):
        page = int(query.data.split('_')[1])
    
    # קבלת פרומפטים
    skip = page * config.PROMPTS_PER_PAGE
    prompts = db.get_all_prompts(user.id, skip=skip, limit=config.PROMPTS_PER_PAGE)
    total_count = db.count_prompts(user.id)
    
    if not prompts:
        text = "📋 <b>הפרומפטים שלי</b>\n\n"
        text += "אין לך פרומפטים שמורים עדיין.\n\n"
        text += "השתמש ב-/save כדי לשמור את הפרומפט הראשון שלך! 💾"
        
        if query:
            await query.edit_message_text(
                text, parse_mode='HTML', reply_markup=back_button("back_main")
            )
        return
    
    # בניית הטקסט
    text = f"📋 <b>הפרומפטים שלי</b> ({total_count} סה״כ)\n\n"
    
    for i, prompt in enumerate(prompts, start=skip + 1):
        emoji = config.CATEGORY_EMOJIS.get(prompt['category'], '📄')
        fav = "⭐ " if prompt.get('is_favorite') else ""
        
        title = prompt['title']
        if len(title) > 40:
            title = title[:40] + "..."
        
        text += f"{i}. {fav}{emoji} <b>{escape_html(title)}</b>\n"
        text += f"   📁 {escape_html(prompt['category'])} | "
        text += f"🔢 {prompt['use_count']} שימושים\n"
        
        # תגיות (עד 3)
        if prompt.get('tags'):
            tags_str = " ".join([f"#{escape_html(tag)}" for tag in prompt['tags'][:3]])
            text += f"   🏷️ {tags_str}\n"
        
        text += f"   /view_{str(prompt['_id'])}\n\n"
    
    # דפדוף
    total_pages = (total_count + config.PROMPTS_PER_PAGE - 1) // config.PROMPTS_PER_PAGE
    
    if query:
        await query.edit_message_text(
            text, parse_mode='HTML', 
            reply_markup=pagination_keyboard(page, total_pages, "page")
        )
    else:
        await update.message.reply_text(
            text, parse_mode='HTML', 
            reply_markup=pagination_keyboard(page, total_pages, "page")
        )
```

---

### 23. View Details עם Context Refresh

**למה זה שימושי:** תצוגת פרטים עם תמיכה ב-refresh מפעולות אחרות.

```python
async def view_prompt_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הצגת פרומפט מלא"""
    query = update.callback_query
    prompt_id = None
    
    if query:
        await query.answer()
        data = query.data
        if isinstance(data, str) and data.startswith('view_'):
            prompt_id = data.replace('view_', '')
    
    # Fallback: כשפעולה אחרת רוצה לרענן
    if not prompt_id:
        cb = context.user_data.get('callback_data')
        if isinstance(cb, str) and cb.startswith('view_'):
            prompt_id = cb.replace('view_', '')
            context.user_data.pop('callback_data', None)
    
    if not prompt_id:
        return
    
    user = update.effective_user
    prompt = db.get_prompt(prompt_id, user.id)
    
    if not prompt:
        text = "⚠️ הפרומפט לא נמצא או שנמחק."
        if query:
            await query.edit_message_text(text)
        return
    
    # בניית ההודעה
    emoji = config.CATEGORY_EMOJIS.get(prompt['category'], '📄')
    fav = "⭐ " if prompt.get('is_favorite') else ""
    
    text = f"{fav}<b>{escape_html(prompt['title'])}</b>\n"
    text += f"{'━' * 30}\n\n"
    text += f"{escape_html(prompt['content'])}\n\n"
    text += f"{'━' * 30}\n"
    text += f"📊 <b>פרטים:</b>\n"
    text += f"• מזהה: {code_inline(prompt_id)}\n"
    text += f"• קטגוריה: {emoji} {escape_html(prompt['category'])}\n"
    text += f"• אורך: {prompt['length']} תווים\n"
    text += f"• שימושים: {prompt['use_count']} פעמים\n"
    text += f"• נוצר: {prompt['created_at'].strftime('%d/%m/%Y')}\n"
    
    if prompt.get('tags'):
        tags_str = " ".join([f"#{escape_html(tag)}" for tag in prompt['tags']])
        text += f"• תגיות: {tags_str}\n"
    
    keyboard = prompt_actions_keyboard(prompt_id, prompt.get('is_favorite', False))
    
    if query:
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=keyboard)
```

---

### 24. Statistics עם Aggregation

**למה זה שימושי:** סטטיסטיקות מפורטות מ-aggregation pipeline.

```python
async def stats_command(update: Update, context):
    """הצגת סטטיסטיקות"""
    user = update.effective_user
    stats = db.get_user_statistics(user.id)
    
    user_stats = stats['user']
    
    text = "📊 <b>הסטטיסטיקות שלך</b>\n\n"
    text += f"📋 סה״כ פרומפטים: <b>{user_stats.get('total_prompts', 0)}</b>\n"
    text += f"🔢 סה״כ שימושים: <b>{user_stats.get('total_uses', 0)}</b>\n"
    text += f"⭐ מועדפים: <b>{db.count_prompts(user.id, is_favorite=True)}</b>\n\n"
    
    # קטגוריות פופולריות
    if stats['categories']:
        text += "📁 <b>קטגוריות מובילות:</b>\n"
        for cat in stats['categories'][:5]:
            emoji = config.CATEGORY_EMOJIS.get(cat['_id'], '📄')
            text += f"  {emoji} {cat['_id']}: {cat['count']}\n"
        text += "\n"
    
    # תגיות פופולריות
    if stats['tags']:
        text += "🏷️ <b>תגיות פופולריות:</b>\n"
        for tag in stats['tags'][:5]:
            text += f"  #{tag['_id']}: {tag['count']}\n"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode='HTML', reply_markup=back_button("back_main")
        )
    else:
        await update.message.reply_text(
            text, parse_mode='HTML', reply_markup=back_button("back_main")
        )
```

---

## 🏷️ ניהול תגיות ומטא-דאטה

### 25. Tag Validation מלאה

**למה זה שימושי:** validation מקיפה לתגיות עם כל הבדיקות.

```python
import config

WAITING_FOR_NEW_TAG = 0

async def receive_new_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """קבלת תגית חדשה"""
    user = update.effective_user
    tag = update.message.text.strip().lower().replace('#', '')
    prompt_id = context.user_data.get('adding_tag_to')
    
    if not prompt_id:
        await update.message.reply_text("⚠️ שגיאה: לא נמצא פרומפט")
        return ConversationHandler.END
    
    # בדיקת תקינות תגית
    if not tag or len(tag) < 2:
        await update.message.reply_text(
            "⚠️ התגית קצרה מדי. אנא שלח תגית של לפחות 2 תווים."
        )
        return WAITING_FOR_NEW_TAG
    
    if len(tag) > 30:
        await update.message.reply_text(
            "⚠️ התגית ארוכה מדי. מקסימום 30 תווים."
        )
        return WAITING_FOR_NEW_TAG
    
    # קבלת הפרומפט
    prompt = db.get_prompt(prompt_id, user.id)
    
    if not prompt:
        await update.message.reply_text("⚠️ הפרומפט לא נמצא")
        return ConversationHandler.END
    
    # בדיקה אם התגית כבר קיימת
    existing_tags = prompt.get('tags', [])
    
    if tag in existing_tags:
        await update.message.reply_text(
            f"⚠️ התגית <code>#{escape_html(tag)}</code> כבר קיימת!",
            parse_mode='HTML'
        )
        return WAITING_FOR_NEW_TAG
    
    # בדיקת מגבלת תגיות
    if len(existing_tags) >= config.MAX_TAGS:
        await update.message.reply_text(
            f"⚠️ הגעת למקסימום של {config.MAX_TAGS} תגיות לפרומפט."
        )
        return ConversationHandler.END
    
    # הוספת התגית
    existing_tags.append(tag)
    db.update_prompt(prompt_id, user.id, {'tags': existing_tags})
    
    await update.message.reply_text(
        f"✅ התגית <code>#{escape_html(tag)}</code> נוספה!",
        parse_mode='HTML',
        reply_markup=back_button(f"tags_{prompt_id}")
    )
    
    context.user_data.clear()
    return ConversationHandler.END
```

---

## 🎯 תבניות מתקדמות

### 26. Toggle Favorite עם Refresh

**למה זה שימושי:** החלפת מצב ורענון מיידי של התצוגה.

```python
async def toggle_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הוספה/הסרה ממועדפים"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    prompt_id = query.data.replace('fav_', '')
    
    prompt = db.get_prompt(prompt_id, user.id)
    
    if not prompt:
        await query.answer("⚠️ הפרומפט לא נמצא", show_alert=True)
        return
    
    new_fav_status = not prompt.get('is_favorite', False)
    db.update_prompt(prompt_id, user.id, {'is_favorite': new_fav_status})
    
    if new_fav_status:
        await query.answer("⭐ נוסף למועדפים!")
    else:
        await query.answer("💔 הוסר ממועדפים")
    
    # רענון התצוגה
    context.user_data['callback_data'] = f"view_{prompt_id}"
    await view_prompt_details(update, context)
```

---

### 27. Category Config עם Reverse Mapping

**למה זה שימושי:** מיפוי דו-כיווני בין emoji לשם קטגוריה.

```python
# config.py
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

# יצירת מיפוי הפוך אוטומטי
CATEGORY_EMOJIS = {v: k for k, v in CATEGORIES.items()}

# שימוש:
emoji = CATEGORY_EMOJIS.get(prompt['category'], '📄')
text = f"{emoji} {escape_html(prompt['category'])}"
```

---

### 28. Two-Step Delete עם Soft Delete

**למה זה שימושי:** מחיקה בטוחה עם אישור ואפשרות שחזור.

```python
async def delete_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """מחיקת פרומפט"""
    query = update.callback_query
    await query.answer()
    
    prompt_id = query.data.replace('delete_', '')
    
    await query.edit_message_text(
        "⚠️ <b>מחיקת פרומפט</b>\n\n"
        "האם אתה בטוח שברצונך למחוק את הפרומפט?\n"
        "ניתן יהיה לשחזר אותו מסל המחזור תוך 30 יום.",
        parse_mode='HTML',
        reply_markup=confirm_keyboard('delete', prompt_id)
    )

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """אישור מחיקה"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    _, action, prompt_id = query.data.split('_', 2)
    
    if action == 'delete':
        success = db.delete_prompt(prompt_id, user.id, permanent=False)
        
        if success:
            await query.edit_message_text(
                "✅ הפרומפט הועבר לסל המחזור.\n\n"
                "ניתן לשחזר אותו דרך /trash",
                reply_markup=back_button("my_prompts")
            )
        else:
            await query.edit_message_text("⚠️ שגיאה במחיקת הפרומפט")

async def cancel_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ביטול מחיקה"""
    query = update.callback_query
    await query.answer()
    
    _, action, prompt_id = query.data.split('_', 2)
    
    # חזרה לצפייה בפרומפט
    context.user_data['callback_data'] = f"view_{prompt_id}"
    await view_prompt_details(update, context)
```

---

### 29. Trash Command עם Restore Links

**למה זה שימושי:** תצוגת סל מחזור עם לינקים ישירים לשחזור.

```python
async def trash_command(update: Update, context):
    """הצגת סל מחזור"""
    user = update.effective_user
    trash_items = db.get_trash(user.id)
    query = update.callback_query
    
    if not trash_items:
        text = "🗑️ <b>סל המחזור</b>\n\nהסל ריק."
        if query:
            await query.answer()
            await query.edit_message_text(
                text, parse_mode='HTML', reply_markup=back_button("back_main")
            )
        else:
            await update.message.reply_text(
                text, parse_mode='HTML', reply_markup=back_button("back_main")
            )
        return
    
    text = f"🗑️ <b>סל המחזור</b> ({len(trash_items)})\n\n"
    text += "<i>פרומפטים נמחקים לצמיתות אחרי 30 יום</i>\n\n"
    
    for i, prompt in enumerate(trash_items[:20], 1):
        emoji = config.CATEGORY_EMOJIS.get(prompt['category'], '📄')
        title = prompt['title']
        if len(title) > 40:
            title = title[:40] + "..."
        
        deleted_at = prompt.get('deleted_at')
        if deleted_at:
            text += f"{i}. {emoji} <b>{escape_html(title)}</b>\n"
            text += f"   /restore_{str(prompt['_id'])}\n\n"
    
    if query:
        await query.answer()
        await query.edit_message_text(
            text, parse_mode='HTML', reply_markup=back_button("back_main")
        )
    else:
        await update.message.reply_text(
            text, parse_mode='HTML', reply_markup=back_button("back_main")
        )
```

---

### 30. Copy with Use Count Tracking

**למה זה שימושי:** העתקה חכמה עם מעקב שימוש לפופולריות.

```python
async def copy_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """העתקת פרומפט"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    prompt_id = query.data.replace('copy_', '')
    
    prompt = db.get_prompt(prompt_id, user.id)
    
    if not prompt:
        await query.answer("⚠️ הפרומפט לא נמצא", show_alert=True)
        return
    
    # עדכון מונה שימושים (חשוב לפופולריות!)
    db.increment_use_count(prompt_id, user.id)
    
    # שליחת הפרומפט כהודעה שניתן להעתיק
    await context.bot.send_message(
        chat_id=user.id,
        text=(
            f"📋 <b>{escape_html(prompt['title'])}</b>\n\n"
            f"{code_block(prompt['content'])}\n\n"
            f"<i>לחץ על הטקסט כדי להעתיק</i>"
        ),
        parse_mode='HTML'
    )
    
    await query.answer("✅ הפרומפט נשלח! העתק את הטקסט מההודעה", show_alert=False)
```

---

## 📝 הערות חשובות

### 🎯 טיפים קריטיים מהפרויקט:

1. **תמיד קרא ל-`query.answer()`** מיד בתחילת כל callback_query handler - מונע "loading" אינסופי
2. **השתמש ב-`escape_html()`** לכל קלט משתמש עם parse_mode='HTML'
3. **נקה `context.user_data.clear()`** בסוף כל ConversationHandler - חובה!
4. **יצירת אינדקסים** על user_id, created_at, is_deleted, tags - ביצועים מהירים יותר
5. **Soft Delete** תמיד לפני מחיקה סופית - חווית משתמש טובה יותר
6. **callback_data פורמט אחיד**: `action_id` (לדוגמה: `view_123`, `copy_456`)

### ⚠️ שגיאות נפוצות להימנע מהן:

- ❌ לשכוח `await query.answer()` → המשתמש רואה loading אינסופי
- ❌ לא לנקות `context.user_data` → state נשאר בין שיחות
- ❌ להשתמש ב-`str(ObjectId)` במקום `ObjectId()` בשאילתות → לא ימצא תוצאות
- ❌ לשכוח `is_deleted: False` בשאילתות → יחזיר גם פריטים נמחקים
- ❌ לא לעשות escape לקלט משתמש → שגיאות parse או חורי אבטחה

### 🏗️ דפוסים ארכיטקטוניים מהפרויקט:

**1. הפרדת Handlers למודולים:**
```
handlers/
  - save.py       # שמירת פרומפטים
  - manage.py     # צפייה, עריכה, מחיקה
  - search.py     # חיפוש וסינון
  - tags.py       # ניהול תגיות
```

**2. ריכוז הגדרות בקובץ אחד:**
- כל הקבועים ב-`config.py`
- טעינה מ-environment variables
- fallbacks לכל הגדרה

**3. Keyboards מרכזיים:**
- כל ה-keyboards ב-`keyboards.py`
- פונקציות שמחזירות `InlineKeyboardMarkup`
- שימוש חוזר בקוד

**4. Utils נפרדים:**
- `escape_html()`, `code_inline()`, `code_block()` ב-`utils.py`
- ייבוא בכל handler שצריך

### 📊 שיפורים מומלצים:

✅ **הוסף ניקוי אוטומטי:** cron job יומי ל-`cleanup_old_trash()`  
✅ **Rate Limiting:** הגבל מספר פרומפטים ליוזר  
✅ **Caching:** שמור תוצאות חיפוש ב-Redis  
✅ **Analytics:** עקוב אחרי שימוש בפרומפטים פופולריים  
✅ **Export/Import:** אפשר לייצא פרומפטים ל-JSON/CSV  

### 🚀 אופטימיזציות ביצועים:

1. **Indexes** - כל השדות שמשמשים ל-find/sort
2. **Projection** - רק שדות נחוצים: `.find({}, {"title": 1, "category": 1})`
3. **Limit** - תמיד הגבל תוצאות: `.limit(100)`
4. **Batch Operations** - `insert_many()` במקום לולאה של `insert_one()`

### 🔐 אבטחה:

- ✅ כל BOT_TOKEN ו-MONGO_URI ב-environment variables
- ✅ בדיקת `user_id` בכל שאילתה למסד נתונים
- ✅ HTML escape לכל קלט משתמש
- ✅ תיקרת אורך (`MAX_PROMPT_LENGTH`, `MAX_TAGS`)
- ✅ Soft delete - לא מוחק סופית ישר

### 📚 משאבים נוספים:

- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [MongoDB Python Driver](https://pymongo.readthedocs.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

---

**🎉 סיכום:**

30 סניפטים ייחודיים מפרויקט אמיתי עובד, מוכנים לשימוש!  
כל הסניפטים נבדקו בייצור ועובדים ✅

**נוצר עבור מפתחי בוטים בטלגרם 🤖**  
*מקור: PromptTracker Bot*  
*עודכן: נובמבר 2025*
