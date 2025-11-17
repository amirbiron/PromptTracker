"""
מטפלי חיפוש וסינון
"""
from telegram import Update
from telegram.ext import ContextTypes
from database import db
from keyboards import category_keyboard, back_button, main_menu_keyboard
import config
from utils import escape_html

SEARCH_FLAG = "awaiting_search_query"

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """התחלת חיפוש"""
    query = update.callback_query
    context.user_data[SEARCH_FLAG] = True
    text = (
        "🔍 <b>חיפוש פרומפטים</b>\n\n"
        "שלח מילת חיפוש או ביטוי לחיפוש בכל הפרומפטים שלך.\n\n"
        "💡 <i>טיפ: החיפוש מתבצע בכותרת ובתוכן הפרומפט</i>\n\n"
        "ליציאה – שלח /cancel או פשוט לחץ על כל כפתור אחר."
    )
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

async def receive_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """קבלת שאילתת חיפוש כאשר מצב החיפוש פעיל"""
    if not context.user_data.get(SEARCH_FLAG):
        return

    message = update.message
    if not message:
        return

    query_text = message.text
    if not query_text:
        return

    user = update.effective_user

    # חיפוש
    results = db.search_prompts(user.id, query=query_text, limit=20)
    context.user_data.pop(SEARCH_FLAG, None)
    
    if not results:
        await message.reply_text(
            f"🔍 לא נמצאו תוצאות עבור: <b>{escape_html(query_text)}</b>\n\n"
            f"נסה מילות חיפוש אחרות.",
            parse_mode='HTML',
            reply_markup=back_button("back_main")
        )
        return
    
    # הצגת תוצאות
    text = f"🔍 <b>תוצאות חיפוש:</b> \"{escape_html(query_text)}\"\n"
    text += f"נמצאו {len(results)} תוצאות\n\n"
    
    for i, prompt in enumerate(results, 1):
        emoji = config.CATEGORY_EMOJIS.get(prompt['category'], '📄')
        fav = "⭐ " if prompt.get('is_favorite') else ""
        
        title = prompt['title']
        if len(title) > 40:
            title = title[:40] + "..."
        
        text += f"{i}. {fav}{emoji} <b>{escape_html(title)}</b>\n"
        text += f"   📁 {escape_html(prompt['category'])}\n"
        text += f"   /view_{escape_html(prompt.get('short_code', str(prompt['_id'])))}\n\n"
    
    await message.reply_text(
        text,
        parse_mode='HTML',
        reply_markup=back_button("back_main")
    )

async def filter_by_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """סינון לפי קטגוריה"""
    query = update.callback_query
    await query.answer()
    
    category = query.data.replace('cat_', '')
    user = update.effective_user
    
    if category == 'all':
        # הצגת כל הפרומפטים
        from handlers.manage import view_my_prompts
        return await view_my_prompts(update, context)
    
    # סינון לפי קטגוריה
    prompts = db.search_prompts(user.id, category=category, limit=50)
    
    if not prompts:
        emoji = config.CATEGORY_EMOJIS.get(category, '📄')
        await query.edit_message_text(
            f"📁 <b>{emoji} {escape_html(category)}</b>\n\n"
            f"אין פרומפטים בקטגוריה זו.",
            parse_mode='HTML',
            reply_markup=back_button("categories")
        )
        return
    
    # הצגת תוצאות
    emoji = config.CATEGORY_EMOJIS.get(category, '📄')
    text = f"📁 <b>{emoji} {escape_html(category)}</b>\n"
    text += f"נמצאו {len(prompts)} פרומפטים\n\n"
    
    for i, prompt in enumerate(prompts[:20], 1):
        fav = "⭐ " if prompt.get('is_favorite') else ""
        
        title = prompt['title']
        if len(title) > 40:
            title = title[:40] + "..."
        
        text += f"{i}. {fav}<b>{escape_html(title)}</b>\n"
        text += f"   🔢 {prompt['use_count']} שימושים\n"
        text += f"   /view_{escape_html(prompt.get('short_code', str(prompt['_id'])))}\n\n"
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=back_button("categories")
    )

async def show_categories_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הצגת תפריט קטגוריות"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # ספירת פרומפטים לכל קטגוריה
    text = "📁 <b>קטגוריות</b>\n\n"
    text += "בחר קטגוריה לצפייה:\n\n"
    
    for emoji, category in config.CATEGORIES.items():
        count = db.count_prompts(user.id, category=category)
        if count > 0:
            text += f"{emoji} <b>{escape_html(category)}</b>: {count} פרומפטים\n"
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=category_keyboard(include_all=True)
    )

async def show_tags_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הצגת תפריט תגיות"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    tags = db.get_all_tags(user.id)
    
    if not tags:
        await query.edit_message_text(
            "🏷️ <b>תגיות</b>\n\n"
            "אין עדיין תגיות.\n\n"
            "הוסף תגיות לפרומפטים שלך כדי לארגן אותם טוב יותר!",
            parse_mode='HTML',
            reply_markup=back_button("back_main")
        )
        return
    
    text = "🏷️ <b>התגיות שלי</b>\n\n"
    text += "התגיות הפופולריות ביותר:\n\n"
    
    for i, tag in enumerate(tags[:20], 1):
        # ספירת שימושים
        count = len(db.search_prompts(user.id, tags=[tag], limit=100))
        text += f"{i}. #{escape_html(tag)} ({count})\n"
    
    text += f"\n<i>סה״כ {len(tags)} תגיות</i>"
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=back_button("back_main")
    )

async def show_popular_prompts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הצגת פרומפטים פופולריים"""
    user = update.effective_user
    prompts = db.get_popular_prompts(user.id, limit=10)
    
    if not prompts:
        text = "🔥 <b>פרומפטים פופולריים</b>\n\n"
        text += "אין עדיין נתונים על שימוש.\n\n"
        text += "השתמש בפרומפטים שלך (העתק) כדי לאסוף נתונים."
    else:
        text = "🔥 <b>הפרומפטים הפופולריים ביותר</b>\n\n"
        
        for i, prompt in enumerate(prompts, 1):
            emoji = config.CATEGORY_EMOJIS.get(prompt['category'], '📄')
            fav = "⭐ " if prompt.get('is_favorite') else ""
            
            title = prompt['title']
            if len(title) > 40:
                title = title[:40] + "..."
            
            text += f"{i}. {fav}{emoji} <b>{escape_html(title)}</b>\n"
            text += f"   🔢 {prompt['use_count']} שימושים\n"
            text += f"   /view_{escape_html(prompt.get('short_code', str(prompt['_id'])))}\n\n"
    
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


async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ביטול מצב החיפוש והחזרה לתפריט, כאשר המשתמש שולח /cancel או לוחץ חזרה."""
    query = update.callback_query
    message = update.message
    was_waiting = context.user_data.pop(SEARCH_FLAG, None)

    if not was_waiting:
        if message:
            await message.reply_text(
                "ℹ️ אין חיפוש פעיל כרגע.",
                reply_markup=back_button("back_main")
            )
        return

    if query:
        await query.answer()
        await query.edit_message_text(
            "📋 <b>PromptTracker</b>\n\nבחר פעולה:",
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )
    else:
        await message.reply_text(
            "❌ החיפוש בוטל.",
            reply_markup=main_menu_keyboard()
        )


async def exit_search_mode_on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ניקוי מצב החיפוש בלחיצה על כפתורים אחרים כדי שלא ימשיכו ליירט הודעות."""
    if context.user_data.get(SEARCH_FLAG):
        context.user_data.pop(SEARCH_FLAG, None)