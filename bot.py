"""
PromptTracker Bot - בוט לניהול פרומפטים
"""
import logging
from datetime import datetime
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

import config
from database import db
from keyboards import main_menu_keyboard, back_button
from handlers.save import (
    start_save_prompt,
    receive_prompt_content,
    receive_prompt_title,
    receive_prompt_category,
    cancel_save,
    WAITING_FOR_PROMPT,
    WAITING_FOR_TITLE,
    WAITING_FOR_CATEGORY
)
from handlers.manage import (
    view_my_prompts,
    view_prompt_details,
    handle_view_command_text,
    copy_prompt,
    toggle_favorite,
    start_edit_prompt,
    start_edit_content,
    receive_new_content,
    start_edit_title,
    receive_new_title,
    delete_prompt,
    confirm_delete,
    cancel_delete,
    view_favorites,
    EDITING_CONTENT,
    EDITING_TITLE,
    start_change_category,
    apply_new_category,
    cancel_change_category,
    CHANGING_CATEGORY
)
from handlers.search import (
    start_search,
    receive_search_query,
    filter_by_category,
    show_categories_menu,
    show_tags_menu,
    show_popular_prompts,
    cancel_search,
    exit_search_mode_on_callback
)
from handlers.tags import (
    manage_tags,
    start_add_tag,
    receive_new_tag,
    remove_tag,
    cancel_add_tag,
    WAITING_FOR_NEW_TAG
)

# הגדרת logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

health_server = None


class HealthHandler(BaseHTTPRequestHandler):
    """שרת HTTP קטן כדי להחזיק פורט פתוח לרנדר"""

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
        # לא לרשום כל בקשה לכלוג
        return


def start_healthcheck_server():
    """הפעלת שרת בריאות מינימלי כדי שלרנדר יהיה פורט פתוח"""
    global health_server

    if not config.ENABLE_HEALTHCHECK_SERVER:
        logger.info("Health-check server disabled via ENABLE_HEALTHCHECK_SERVER env var")
        return

    port = config.HEALTHCHECK_PORT
    try:
        health_server = HTTPServer(("", port), HealthHandler)
    except OSError as exc:
        logger.warning("Failed to start health-check server on port %s: %s", port, exc)
        return

    thread = threading.Thread(
        target=health_server.serve_forever,
        name="render-healthcheck-server",
        daemon=True
    )
    thread.start()
    logger.info("Health-check server is listening on port %s", port)

# ========== פקודות בסיס ==========

async def start_command(update: Update, context):
    """פקודת /start"""
    user = update.effective_user
    
    # יצירת/עדכון משתמש
    db.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    from utils import escape_html
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

async def help_command(update: Update, context):
    """פקודת /help"""
    help_text = (
        "📚 <b>עזרה - PromptTracker</b>\n\n"
        "<b>פקודות זמינות:</b>\n\n"
        "🔹 /start - תפריט ראשי\n"
        "🔹 /save - שמור פרומפט חדש\n"
        "🔹 /list - הצג את כל הפרומפטים\n"
        "🔹 /search - חיפוש פרומפטים\n"
        "🔹 /favorites - פרומפטים מועדפים\n"
        "🔹 /stats - סטטיסטיקות\n"
        "🔹 /categories - קטגוריות\n"
        "🔹 /tags - תגיות\n"
        "🔹 /trash - סל מחזור\n"
        "🔹 /settings - הגדרות\n\n"
        "<b>טיפים:</b>\n"
        "💡 אתה יכול להעביר (Forward) הודעות עם פרומפטים\n"
        "💡 השתמש בתגיות כדי לארגן טוב יותר\n"
        "💡 הפרומפטים הכי משומשים מופיעים בראש ברשימה\n\n"
        "יש שאלות? צור קשר: @YourUsername"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode='HTML',
        reply_markup=main_menu_keyboard()
    )

async def show_settings(update: Update, context):
    """תפריט הגדרות בסיסי"""
    query = update.callback_query
    if query:
        await query.answer()
    user = update.effective_user
    user_doc = db.get_or_create_user(user.id, user.username, user.first_name)

    settings = user_doc.get('settings', {})
    text = (
        "⚙️ *הגדרות*\n\n"
        f"הצגת מזהים: {'מופעל' if settings.get('show_ids') else 'כבוי'}\n"
        f"קיצור כותרות: {'מופעל' if settings.get('short_titles') else 'כבוי'}\n"
        f"הצגת תגיות: {'מופעל' if settings.get('show_tags') else 'כבוי'}\n"
        f"אישור העתקה: {'מופעל' if settings.get('copy_confirmation') else 'כבוי'}\n"
        f"ערכת נושא: {settings.get('theme', 'dark')}\n\n"
        "(שינויים מתקדמים יגיעו בקרוב)"
    )

    await (query.edit_message_text if query else update.message.reply_text)(
        text,
        parse_mode='HTML',
        reply_markup=back_button("back_main")
    )

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
            text,
            parse_mode='HTML',
            reply_markup=back_button("back_main")
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode='HTML',
            reply_markup=back_button("back_main")
        )

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
                text,
                parse_mode='HTML',
                reply_markup=back_button("back_main")
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode='HTML',
                reply_markup=back_button("back_main")
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
            # Avoid reliance on Mongo server_info['localTime'] which may be missing
            try:
                days_ago = (datetime.utcnow() - deleted_at).days
            except Exception:
                days_ago = 0
            text += f"{i}. {emoji} <b>{title}</b>\n"
            text += f"   נמחק לפני {days_ago} ימים\n"
            text += f"   /restore_{str(prompt['_id'])}\n\n"
    if query:
        await query.answer()
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=back_button("back_main")
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode='HTML',
            reply_markup=back_button("back_main")
        )

async def restore_command(update: Update, context):
    """שחזור פרומפט מהאשפה"""
    if not context.args:
        await update.message.reply_text(
            "⚠️ שימוש: /restore_<prompt_id>"
        )
        return
    
    user = update.effective_user
    prompt_id = context.args[0].replace('_', '')
    
    success = db.restore_prompt(prompt_id, user.id)
    
    if success:
        await update.message.reply_text(
            "✅ הפרומפט שוחזר בהצלחה!",
            reply_markup=back_button("my_prompts")
        )
    else:
        await update.message.reply_text(
            "⚠️ לא ניתן לשחזר את הפרומפט"
        )

# ========== Callback handlers ==========

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
    
    # noop - כפתור לא פעיל
    if data == "noop":
        await query.answer()
        return
    
    # הפניה לפונקציות אחרות תתבצע דרך ה-handlers

async def back_to_main_from_conv(update: Update, context):
    """יציאה מכל שיחה והחזרה לתפריט הראשי."""
    from telegram.ext import ConversationHandler
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
        await query.edit_message_text(
            "📋 <b>PromptTracker</b>\n\nבחר פעולה:",
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )
    elif update.effective_message:
        await update.effective_message.reply_text(
            "📋 <b>PromptTracker</b>\n\nבחר פעולה:",
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )
    return ConversationHandler.END

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

def main():
    """הפעלת הבוט"""
    # בדיקת הגדרות
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set!")
        return
    
    # יצירת האפליקציה
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # פקודות בסיס
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", view_my_prompts))
    application.add_handler(CommandHandler("view", handle_view_command_text))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("trash", trash_command))
    application.add_handler(CommandHandler("restore", restore_command))
    application.add_handler(CommandHandler("search", start_search))
    application.add_handler(CommandHandler("cancel", cancel_search))
    # תמיכה גם בצורה /view_<id> (ObjectId) וגם /view_<SHORT>
    application.add_handler(MessageHandler(filters.Regex(r"^/view_([0-9a-fA-F]{24}|[0-9a-fA-F]{4,8})$"), handle_view_command_text))
    
    # Conversation Handler לשמירת פרומפט
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
            CallbackQueryHandler(back_to_main_from_conv, pattern="^back_main$")
        ]
    )
    application.add_handler(save_conv)
    
    # Conversation Handler לעריכת תוכן
    edit_content_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_edit_content, pattern="^edit_content_")
        ],
        states={
            EDITING_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_content)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_save),
            CallbackQueryHandler(back_to_main_from_conv, pattern="^back_main$")
        ]
    )
    application.add_handler(edit_content_conv)
    
    # Conversation Handler לעריכת כותרת
    edit_title_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_edit_title, pattern="^edit_title_")
        ],
        states={
            EDITING_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_title)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_save),
            CallbackQueryHandler(back_to_main_from_conv, pattern="^back_main$")
        ]
    )
    application.add_handler(edit_title_conv)

    # Conversation Handler לשינוי קטגוריה
    change_cat_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_change_category, pattern="^chcat_")
        ],
        states={
            CHANGING_CATEGORY: [
                CallbackQueryHandler(apply_new_category, pattern="^cat_")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_change_category),
            CallbackQueryHandler(back_to_main_from_conv, pattern="^back_main$")
        ]
    )
    application.add_handler(change_cat_conv)
    
    # Callback handlers
    # חזרה לתפריט ראשי בכל מקום שאינו בשיחה
    application.add_handler(CallbackQueryHandler(back_to_main_from_conv, pattern="^back_main$"))
    application.add_handler(CallbackQueryHandler(view_my_prompts, pattern="^my_prompts$"))
    application.add_handler(CallbackQueryHandler(view_my_prompts, pattern="^page_"))
    application.add_handler(CallbackQueryHandler(view_prompt_details, pattern="^view_"))
    application.add_handler(CallbackQueryHandler(copy_prompt, pattern="^copy_"))
    application.add_handler(CallbackQueryHandler(toggle_favorite, pattern="^fav_"))
    application.add_handler(CallbackQueryHandler(start_edit_prompt, pattern="^edit_"))
    application.add_handler(CallbackQueryHandler(delete_prompt, pattern="^delete_"))
    application.add_handler(CallbackQueryHandler(confirm_delete, pattern="^confirm_"))
    application.add_handler(CallbackQueryHandler(cancel_delete, pattern="^cancel_"))
    application.add_handler(CallbackQueryHandler(view_favorites, pattern="^favorites$"))
    application.add_handler(CallbackQueryHandler(show_categories_menu, pattern="^categories$"))
    application.add_handler(CallbackQueryHandler(filter_by_category, pattern="^cat_"))
    application.add_handler(CallbackQueryHandler(show_tags_menu, pattern="^tags$"))
    application.add_handler(CallbackQueryHandler(manage_tags, pattern="^tags_"))
    application.add_handler(CallbackQueryHandler(remove_tag, pattern="^rmtag_"))
    application.add_handler(CallbackQueryHandler(show_settings, pattern="^settings$"))
    application.add_handler(CallbackQueryHandler(trash_command, pattern="^trash$"))
    application.add_handler(CallbackQueryHandler(start_search, pattern="^search$"))

    # Conversation Handler להוספת תגית
    tags_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_add_tag, pattern="^addtag_")
        ],
        states={
            WAITING_FOR_NEW_TAG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_tag)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_add_tag),
            CallbackQueryHandler(back_to_main_from_conv, pattern="^back_main$")
        ]
    )
    application.add_handler(tags_conv)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_search_query))
    application.add_handler(CallbackQueryHandler(stats_command, pattern="^stats$"))
    # ניקוי מצב החיפוש לאחר שטופלו שאר ה-handlers הספציפיים
    application.add_handler(CallbackQueryHandler(exit_search_mode_on_callback, block=False))
    
    # Callback כללי
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # הפעלת הבוט
    start_healthcheck_server()
    logger.info("🚀 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
