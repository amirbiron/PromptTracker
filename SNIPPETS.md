# 📚 Telegram Bot Code Snippets Library

ספריית קטעי קוד לבניית בוטים בטלגרם - מוכן להעתקה והדבקה.

---

## 🚀 אתחול והגדרות

### 1. אתחול בוט בסיסי עם Application Builder

**למה זה שימושי:** נקודת התחלה מהירה לכל בוט טלגרם מבוסס python-telegram-bot.

```python
from telegram.ext import Application, CommandHandler
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    application = Application.builder().token("YOUR_BOT_TOKEN").build()
    
    # הוספת handlers
    application.add_handler(CommandHandler("start", start_command))
    
    # הפעלת הבוט
    logger.info("🚀 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
```

---

### 2. טעינת הגדרות מסביבה (Environment Variables)

**למה זה שימושי:** ניהול הגדרות בטוח ללא חשיפת מידע רגיש בקוד.

```python
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'mybot')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
```

---

### 3. Error Handler גלובלי

**למה זה שימושי:** תפיסת שגיאות מרכזית שמונעת מהבוט לקרוס.

```python
import logging

logger = logging.getLogger(__name__)

async def error_handler(update: Update, context):
    """טיפול בשגיאות"""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ אירעה שגיאה. אנא נסה שוב."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

# שימוש:
application.add_error_handler(error_handler)
```

---

### 4. Health Check Server למארחים כמו Render

**למה זה שימושי:** שומר על הבוט פעיל בשירותי hosting שדורשים פורט HTTP פתוח.

```python
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ok")
    
    def log_message(self, format, *args):
        return  # ללא לוג מיותר

def start_healthcheck_server(port=8000):
    health_server = HTTPServer(("", port), HealthHandler)
    thread = threading.Thread(
        target=health_server.serve_forever,
        daemon=True
    )
    thread.start()
    logger.info(f"Health-check server listening on port {port}")
```

---

## 🗄️ MongoDB ומסדי נתונים

### 5. חיבור MongoDB עם אינדקסים

**למה זה שימושי:** חיבור מאובטח למסד נתונים עם אינדוקסים לביצועים מהירים.

```python
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT

class Database:
    def __init__(self, mongo_uri, db_name):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.users = self.db.users
        self.prompts = self.db.prompts
        self._create_indexes()
    
    def _create_indexes(self):
        # אינדקסים בסיסיים
        self.prompts.create_index([("user_id", ASCENDING)])
        self.prompts.create_index([("created_at", DESCENDING)])
        self.prompts.create_index([("title", TEXT), ("content", TEXT)])
        self.users.create_index([("user_id", ASCENDING)], unique=True)
```

---

### 6. Get or Create User Pattern

**למה זה שימושי:** יצירה אוטומטית של משתמש חדש בפעם הראשונה שהוא משתמש בבוט.

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
            "settings": {},
            "stats": {
                "total_prompts": 0,
                "total_uses": 0
            }
        }
        self.users.insert_one(user)
    
    return user
```

---

### 7. עדכון סטטיסטיקות עם $inc

**למה זה שימושי:** עדכון מונים בצורה אטומית וביצועית.

```python
def update_user_stats(self, user_id: int, stat_name: str, increment: int = 1):
    """עדכון סטטיסטיקות משתמש"""
    self.users.update_one(
        {"user_id": user_id},
        {"$inc": {f"stats.{stat_name}": increment}}
    )

# שימוש:
update_user_stats(user_id, "total_prompts")
update_user_stats(user_id, "total_uses", 5)
```

---

### 8. Soft Delete Pattern (מחיקה רכה)

**למה זה שימושי:** מחיקה שניתן לשחזר - חיוני לחווית משתמש טובה.

```python
from datetime import datetime

def delete_prompt(self, prompt_id: str, user_id: int, permanent: bool = False):
    """מחיקת פרומפט (רכה או קשה)"""
    from bson import ObjectId
    try:
        if permanent:
            result = self.prompts.delete_one({
                "_id": ObjectId(prompt_id),
                "user_id": user_id
            })
        else:
            result = self.prompts.update_one(
                {"_id": ObjectId(prompt_id), "user_id": user_id},
                {"$set": {
                    "is_deleted": True,
                    "deleted_at": datetime.utcnow()
                }}
            )
        return result.modified_count > 0 or result.deleted_count > 0
    except:
        return False
```

---

### 9. חיפוש מלא טקסט (Full-Text Search)

**למה זה שימושי:** חיפוש מתקדם בכל שדות הטקסט במסד הנתונים.

```python
def search_prompts(self, user_id: int, query: str = None, 
                  category: str = None, skip: int = 0, limit: int = 10):
    """חיפוש פרומפטים עם סינון"""
    filter_query = {
        "user_id": user_id,
        "is_deleted": False
    }
    
    if query:
        filter_query["$text"] = {"$search": query}
    
    if category:
        filter_query["category"] = category
    
    prompts = list(self.prompts.find(filter_query)
                  .sort("created_at", DESCENDING)
                  .skip(skip)
                  .limit(limit))
    
    return prompts
```

---

### 10. MongoDB Aggregation לסטטיסטיקות

**למה זה שימושי:** חישובים מורכבים על הנתונים - מהיר וביצועי.

```python
def get_category_stats(self, user_id: int, limit: int = 5):
    """קבלת קטגוריות פופולריות"""
    pipeline = [
        {"$match": {"user_id": user_id, "is_deleted": False}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]
    return list(self.prompts.aggregate(pipeline))
```

---

## ⌨️ Inline Keyboards (מקלדות)

### 11. תפריט ראשי עם אייקונים

**למה זה שימושי:** תפריט ברור ואטרקטיבי שמקל על ניווט.

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("💾 שמור", callback_data="save"),
            InlineKeyboardButton("📋 רשימה", callback_data="list")
        ],
        [
            InlineKeyboardButton("🔍 חיפוש", callback_data="search"),
            InlineKeyboardButton("⭐ מועדפים", callback_data="favorites")
        ],
        [
            InlineKeyboardButton("⚙️ הגדרות", callback_data="settings")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
```

---

### 12. דפדוף (Pagination Keyboard)

**למה זה שימושי:** ניווט בין עמודים בצורה מקצועית.

```python
def pagination_keyboard(current_page: int, total_pages: int, prefix: str = "page"):
    keyboard = []
    nav_buttons = []
    
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(
            "« הקודם", 
            callback_data=f"{prefix}_{current_page - 1}"
        ))
    
    nav_buttons.append(InlineKeyboardButton(
        f"{current_page + 1}/{total_pages}",
        callback_data="noop"
    ))
    
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            "הבא »",
            callback_data=f"{prefix}_{current_page + 1}"
        ))
    
    keyboard.append(nav_buttons)
    keyboard.append([
        InlineKeyboardButton("« חזרה", callback_data="back_main")
    ])
    
    return InlineKeyboardMarkup(keyboard)
```

---

### 13. כפתור אישור (Confirm Dialog)

**למה זה שימושי:** אישור פעולות רגישות כמו מחיקה.

```python
def confirm_keyboard(action: str, item_id: str):
    keyboard = [
        [
            InlineKeyboardButton("✅ כן", callback_data=f"confirm_{action}_{item_id}"),
            InlineKeyboardButton("❌ לא", callback_data=f"cancel_{action}_{item_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
```

---

### 14. כפתור חזרה פשוט

**למה זה שימושי:** מאפשר חזרה למסך קודם בכל מקום.

```python
def back_button(callback_data: str = "back_main"):
    keyboard = [[InlineKeyboardButton("« חזרה", callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)
```

---

### 15. תפריט פעולות על פריט

**למה זה שימושי:** תפריט מקיף לכל הפעולות האפשריות על פריט.

```python
def item_actions_keyboard(item_id: str, is_favorite: bool = False):
    fav_text = "💔 הסר מועדפים" if is_favorite else "⭐ הוסף למועדפים"
    
    keyboard = [
        [
            InlineKeyboardButton("📋 העתק", callback_data=f"copy_{item_id}"),
            InlineKeyboardButton(fav_text, callback_data=f"fav_{item_id}")
        ],
        [
            InlineKeyboardButton("✏️ ערוך", callback_data=f"edit_{item_id}"),
            InlineKeyboardButton("🗑️ מחק", callback_data=f"delete_{item_id}")
        ],
        [
            InlineKeyboardButton("« חזרה", callback_data="back_list")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
```

---

## 💬 פקודות ו-Handlers

### 16. פקודת Start מקצועית

**למה זה שימושי:** פקודת פתיחה ידידותית עם רישום משתמש.

```python
from utils import escape_html

async def start_command(update: Update, context):
    user = update.effective_user
    
    # רישום המשתמש
    db.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    welcome_text = (
        f"👋 שלום {escape_html(user.first_name)}!\n\n"
        f"ברוך הבא ל-<b>הבוט שלי</b> 🚀\n\n"
        f"📋 <b>מה אני יכול לעשות?</b>\n"
        f"• 💾 תכונה 1\n"
        f"• 🔍 תכונה 2\n"
        f"• ⭐ תכונה 3\n\n"
        f"בחר פעולה מהתפריט למטה:"
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=main_menu_keyboard()
    )
```

---

### 17. טיפול ב-Callback Query בצורה נכונה

**למה זה שימושי:** תבנית נכונה שמונעת timeout ושגיאות.

```python
async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()  # חובה! מונע "loading" אינסופי
    
    data = query.data
    
    if data == "back_main":
        await query.edit_message_text(
            "📋 <b>תפריט ראשי</b>\n\nבחר פעולה:",
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )
        return
    
    if data == "noop":
        # כפתור לא פעיל
        return
```

---

### 18. ConversationHandler Setup (שיחה רב-שלבית)

**למה זה שימושי:** בניית זרימות מורכבות עם מספר שלבים.

```python
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# הגדרת States
WAITING_FOR_INPUT, WAITING_FOR_CONFIRMATION = range(2)

save_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_save, pattern="^save$"),
        CommandHandler("save", start_save)
    ],
    states={
        WAITING_FOR_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_input)
        ],
        WAITING_FOR_CONFIRMATION: [
            CallbackQueryHandler(receive_confirmation, pattern="^confirm_")
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

### 19. ניהול State עם context.user_data

**למה זה שימושי:** שמירת מידע זמני במהלך שיחה.

```python
async def start_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    item_id = query.data.replace('edit_', '')
    context.user_data['editing_item_id'] = item_id
    
    await query.edit_message_text(
        "📝 שלח את הערך החדש:"
    )
    return EDITING_STATE

async def receive_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_value = update.message.text
    item_id = context.user_data.get('editing_item_id')
    
    # עדכון במסד הנתונים
    db.update_item(item_id, new_value)
    
    context.user_data.clear()  # ניקוי המטמון
    return ConversationHandler.END
```

---

## 🛡️ אבטחה ותצוגה

### 20. HTML Escape לטלגרם

**למה זה שימושי:** מניעת שגיאות parse_mode והזרקת קוד זדוני.

```python
def escape_html(value) -> str:
    """Escape &, <, > for Telegram HTML parse mode"""
    if value is None:
        return ""
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

# שימוש:
await update.message.reply_text(
    f"<b>שם:</b> {escape_html(user_input)}",
    parse_mode='HTML'
)
```

---

### 21. תצוגת קוד (Code Blocks)

**למה זה שימושי:** הצגת קוד או טקסט ארוך בפורמט קריא.

```python
def code_inline(value) -> str:
    """Wrap as inline code"""
    return f"<code>{escape_html(value)}</code>"

def code_block(value) -> str:
    """Wrap in a pre/code block"""
    return f"<pre><code>{escape_html(value)}</code></pre>"

# שימוש:
text = f"מזהה: {code_inline(item_id)}\n\n"
text += f"תוכן:\n{code_block(content)}"
```

---

## 📊 תצוגת רשימות ונתונים

### 22. הצגת רשימה עם דפדוף

**למה זה שימושי:** תצוגה מסודרת של רשימות ארוכות עם ניווט.

```python
async def view_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    
    user = update.effective_user
    
    # קבלת מספר העמוד
    page = 0
    if query and query.data.startswith('page_'):
        page = int(query.data.split('_')[1])
    
    # קבלת פריטים
    ITEMS_PER_PAGE = 10
    skip = page * ITEMS_PER_PAGE
    items = db.get_items(user.id, skip=skip, limit=ITEMS_PER_PAGE)
    total_count = db.count_items(user.id)
    
    if not items:
        text = "אין פריטים להצגה."
    else:
        text = f"📋 <b>הפריטים שלי</b> ({total_count} סה״כ)\n\n"
        
        for i, item in enumerate(items, start=skip + 1):
            text += f"{i}. <b>{escape_html(item['name'])}</b>\n"
            text += f"   /view_{str(item['_id'])}\n\n"
    
    total_pages = (total_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    keyboard = pagination_keyboard(page, total_pages, "page")
    
    if query:
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=keyboard)
```

---

### 23. הצגת פרטי פריט מלא

**למה זה שימושי:** תצוגה מסודרת עם כל הפרטים והפעולות.

```python
async def view_item_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    item_id = query.data.replace('view_', '')
    
    item = db.get_item(item_id, user.id)
    
    if not item:
        await query.edit_message_text("⚠️ הפריט לא נמצא")
        return
    
    text = f"<b>{escape_html(item['title'])}</b>\n"
    text += f"{'━' * 30}\n\n"
    text += f"{escape_html(item['content'])}\n\n"
    text += f"{'━' * 30}\n"
    text += f"📊 <b>פרטים:</b>\n"
    text += f"• מזהה: {code_inline(item_id)}\n"
    text += f"• נוצר: {item['created_at'].strftime('%d/%m/%Y')}\n"
    
    keyboard = item_actions_keyboard(item_id, item.get('is_favorite', False))
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=keyboard
    )
```

---

### 24. סטטיסטיקות משתמש

**למה זה שימושי:** הצגת נתונים מעניינים למשתמש.

```python
async def stats_command(update: Update, context):
    user = update.effective_user
    stats = db.get_user_statistics(user.id)
    
    text = "📊 <b>הסטטיסטיקות שלך</b>\n\n"
    text += f"📋 סה״כ פריטים: <b>{stats['total_items']}</b>\n"
    text += f"🔢 סה״כ שימושים: <b>{stats['total_uses']}</b>\n"
    text += f"⭐ מועדפים: <b>{stats['favorites']}</b>\n\n"
    
    if stats['top_categories']:
        text += "📁 <b>קטגוריות מובילות:</b>\n"
        for cat in stats['top_categories'][:5]:
            text += f"  • {cat['_id']}: {cat['count']}\n"
    
    await update.message.reply_text(
        text,
        parse_mode='HTML',
        reply_markup=back_button("back_main")
    )
```

---

## 🏷️ ניהול תגיות ומטא-דאטה

### 25. הוספת תגית עם ולידציה

**למה זה שימושי:** הוספת תגיות בצורה מבוקרת עם בדיקות.

```python
MAX_TAGS = 10

async def receive_new_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tag = update.message.text.strip().lower().replace('#', '')
    item_id = context.user_data.get('adding_tag_to')
    
    # ולידציה
    if not tag or len(tag) < 2:
        await update.message.reply_text("⚠️ התגית קצרה מדי (מינימום 2 תווים)")
        return WAITING_FOR_TAG
    
    if len(tag) > 30:
        await update.message.reply_text("⚠️ התגית ארוכה מדי (מקסימום 30 תווים)")
        return WAITING_FOR_TAG
    
    item = db.get_item(item_id, user.id)
    existing_tags = item.get('tags', [])
    
    if tag in existing_tags:
        await update.message.reply_text(f"⚠️ התגית #{tag} כבר קיימת!")
        return WAITING_FOR_TAG
    
    if len(existing_tags) >= MAX_TAGS:
        await update.message.reply_text(f"⚠️ הגעת למקסימום של {MAX_TAGS} תגיות")
        return ConversationHandler.END
    
    # הוספת התגית
    existing_tags.append(tag)
    db.update_item(item_id, user.id, {'tags': existing_tags})
    
    await update.message.reply_text(
        f"✅ התגית #{tag} נוספה!",
        parse_mode='HTML'
    )
    
    context.user_data.clear()
    return ConversationHandler.END
```

---

## 🎯 תבניות מתקדמות

### 26. Toggle Favorite (העברה בין מצבים)

**למה זה שימושי:** החלפת מצב בלחיצת כפתור אחת.

```python
async def toggle_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    item_id = query.data.replace('fav_', '')
    
    item = db.get_item(item_id, user.id)
    
    if not item:
        await query.answer("⚠️ הפריט לא נמצא", show_alert=True)
        return
    
    new_fav_status = not item.get('is_favorite', False)
    db.update_item(item_id, user.id, {'is_favorite': new_fav_status})
    
    if new_fav_status:
        await query.answer("⭐ נוסף למועדפים!")
    else:
        await query.answer("💔 הוסר ממועדפים")
    
    # רענון התצוגה
    context.user_data['callback_data'] = f"view_{item_id}"
    await view_item_details(update, context)
```

---

### 27. קטגוריות עם אמוג'ים (Category Mapping)

**למה זה שימושי:** הוספת ויזואליה נעימה עם אמוג'ים.

```python
CATEGORIES = {
    '🤖': 'Bots',
    '🎨': 'Design',
    '📚': 'Documentation',
    '💻': 'Code',
    '✍️': 'Writing',
    '📊': 'Data',
    '⚙️': 'Other'
}

CATEGORY_EMOJIS = {v: k for k, v in CATEGORIES.items()}

# שימוש:
emoji = CATEGORY_EMOJIS.get(item['category'], '📄')
text = f"{emoji} {escape_html(item['category'])}"
```

---

### 28. מחיקה עם אישור (Two-Step Delete)

**למה זה שימושי:** מניעת מחיקות בטעות.

```python
async def delete_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    item_id = query.data.replace('delete_', '')
    
    await query.edit_message_text(
        "⚠️ <b>מחיקת פריט</b>\n\n"
        "האם אתה בטוח שברצונך למחוק?\n"
        "ניתן יהיה לשחזר אותו תוך 30 יום.",
        parse_mode='HTML',
        reply_markup=confirm_keyboard('delete', item_id)
    )

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    _, action, item_id = query.data.split('_', 2)
    
    if action == 'delete':
        success = db.delete_item(item_id, user.id, permanent=False)
        
        if success:
            await query.edit_message_text(
                "✅ הפריט הועבר לסל המחזור",
                reply_markup=back_button("list")
            )
        else:
            await query.edit_message_text("⚠️ שגיאה במחיקה")
```

---

### 29. ניקוי אוטומטי של זבל ישן

**למה זה שימושי:** שמירה על מסד הנתונים נקי וחסכוני.

```python
from datetime import datetime, timedelta

def cleanup_old_trash(self, retention_days: int = 30):
    """מחיקה סופית של פריטים ישנים"""
    threshold = datetime.utcnow() - timedelta(days=retention_days)
    result = self.items.delete_many({
        "is_deleted": True,
        "deleted_at": {"$lt": threshold}
    })
    return result.deleted_count

# הפעלה יומית (בסקריפט נפרד או cron):
# deleted = db.cleanup_old_trash()
# logger.info(f"Cleaned up {deleted} old items")
```

---

### 30. Copy to Clipboard (העתקה נוחה)

**למה זה שימושי:** שליחת תוכן שקל להעתיק עם לחיצה ארוכה.

```python
async def copy_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    item_id = query.data.replace('copy_', '')
    
    item = db.get_item(item_id, user.id)
    
    if not item:
        await query.answer("⚠️ הפריט לא נמצא", show_alert=True)
        return
    
    # עדכון מונה שימושים
    db.increment_use_count(item_id, user.id)
    
    # שליחת הפריט כהודעה נפרדת
    await context.bot.send_message(
        chat_id=user.id,
        text=(
            f"📋 <b>{escape_html(item['title'])}</b>\n\n"
            f"{code_block(item['content'])}\n\n"
            f"<i>לחץ על הטקסט להעתקה</i>"
        ),
        parse_mode='HTML'
    )
    
    await query.answer("✅ נשלח! לחץ על הטקסט להעתקה")
```

---

## 📝 הערות חשובות

### טיפים לשימוש:

1. **תמיד השתמש ב-`escape_html()`** כשאתה מציג קלט של משתמש ב-parse_mode='HTML'
2. **קרא ל-`query.answer()`** מיד בתחילת כל callback_query handler
3. **נקה את `context.user_data`** בסוף כל ConversationHandler
4. **השתמש ב-try/except** סביב פעולות מסד נתונים
5. **צור אינדקסים** על שדות שמשמשים לחיפוש וסינון תכוף
6. **הוסף logging** לכל פעולה חשובה לדיבאג

### דפוסי Best Practices:

- ✅ שמור מידע רגיש ב-Environment Variables
- ✅ השתמש ב-Soft Delete לפני מחיקה סופית
- ✅ אפשר לביטול (Cancel) בכל זרימה
- ✅ הצג הודעות שגיאה ידידותיות
- ✅ הוסף confirmation לפעולות הרסניות
- ✅ השתמש ב-pagination לרשימות ארוכות

---

**נוצר עבור מפתחי בוטים בטלגרם 🤖**  
*עודכן לאחרונה: 2025*
