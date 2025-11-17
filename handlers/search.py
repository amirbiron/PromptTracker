"""
מטפלי חיפוש וסינון
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from keyboards import category_keyboard, back_button, main_menu_keyboard
import config
from utils import escape_html

# States
WAITING_FOR_SEARCH_QUERY = 0

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """התחלת חיפוש"""
    query = update.callback_query
    text = (
        "🔍 <b>חיפוש פרומפטים</b>\n\n"
        "שלח מילת חיפוש או ביטוי לחיפוש בכל הפרומפטים שלך.\n\n"
        "💡 <i>טיפ: החיפוש מתבצע בכותרת ובתוכן הפרומפט</i>\n\n"
        "או שלח /cancel לביטול או לחץ « חזרה לתפריט הראשי."
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
    
    return WAITING_FOR_SEARCH_QUERY

async def receive_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """קבלת שאילתת חיפוש"""
    user = update.effective_user
    query_text = update.message.text
    
    if query_text == '/cancel':
        await update.message.reply_text(
            "❌ החיפוש בוטל.",
            reply_markup=back_button("back_main")
        )
        return ConversationHandler.END
    
    # חיפוש
    results = db.search_prompts(user.id, query=query_text, limit=20)
    
    if not results:
        await update.message.reply_text(
            f"🔍 לא נמצאו תוצאות עבור: <b>{escape_html(query_text)}</b>\n\n"
            f"נסה מילות חיפוש אחרות.",
            parse_mode='HTML',
            reply_markup=back_button("back_main")
        )
        return ConversationHandler.END
    
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
        text += f"   /view_{str(prompt['_id'])}\n\n"
    
    await update.message.reply_text(
        text,
        parse_mode='HTML',
        reply_markup=back_button("back_main")
    )
    
    return ConversationHandler.END

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
        text += f"   /view_{str(prompt['_id'])}\n\n"
    
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
            text += f"   /view_{str(prompt['_id'])}\n\n"
    
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
    """ביטול מצב החיפוש והחזרה לתפריט."""
    query = update.callback_query

    if query:
        await query.answer()
        await query.edit_message_text(
            "📋 <b>PromptTracker</b>\n\nבחר פעולה:",
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ החיפוש בוטל.",
            reply_markup=main_menu_keyboard()
        )

    return ConversationHandler.END