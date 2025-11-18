"""
מטפלי שמירת פרומפטים
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from urllib.parse import unquote_plus
from database import db
from keyboards import category_keyboard, prompt_actions_keyboard, back_button
import config
from utils import escape_html

# States for conversation
WAITING_FOR_PROMPT, WAITING_FOR_TITLE, WAITING_FOR_CATEGORY = range(3)

async def start_save_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """התחלת תהליך שמירת פרומפט"""
    query = update.callback_query
    text = (
        "📝 <b>שמירת פרומפט חדש</b>\n\n"
        "שלח לי את הפרומפט שברצונך לשמור.\n"
        "אתה יכול גם להעביר (Forward) הודעה קיימת.\n\n"
        "💡 <i>טיפ: הפרומפט יכול להיות עד 4000 תווים</i>"
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
    return WAITING_FOR_PROMPT

async def receive_prompt_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """קבלת תוכן הפרומפט"""
    user = update.effective_user
    content = update.message.text or update.message.caption
    
    if not content:
        await update.message.reply_text(
            "⚠️ לא התקבל טקסט. אנא שלח טקסט או הודעה עם כיתוב."
        )
        return WAITING_FOR_PROMPT
    
    if len(content) > config.MAX_PROMPT_LENGTH:
        await update.message.reply_text(
            f"⚠️ הפרומפט ארוך מדי!\n"
            f"אורך נוכחי: {len(content)} תווים\n"
            f"מקסימום: {config.MAX_PROMPT_LENGTH} תווים\n\n"
            f"אנא קצר את הטקסט ונסה שוב."
        )
        return WAITING_FOR_PROMPT
    
    # שמירה בהקשר
    context.user_data['new_prompt_content'] = content
    
    # בקשת כותרת
    preview = content[:100] + "..." if len(content) > 100 else content
    
    await update.message.reply_text(
        f"✅ הפרומפט התקבל!\n\n"
        f"📄 <b>תצוגה מקדימה:</b>\n"
        f"<i>{escape_html(preview)}</i>\n\n"
        f"📋 כעת, שלח כותרת לפרומפט (או שלח דלג):",
        parse_mode='HTML'
    )
    
    return WAITING_FOR_TITLE

async def receive_prompt_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """קבלת כותרת לפרומפט"""
    title = update.message.text
    user = update.effective_user
    
    if title.strip() in ['/skip', 'דלג']:
        # שימוש בכותרת אוטומטית
        content = context.user_data.get('new_prompt_content', '')
        title = content[:50] + "..." if len(content) > 50 else content
    
    context.user_data['new_prompt_title'] = title
    
    # בקשת קטגוריה
    categories = db.get_user_categories(user.id)
    
    await update.message.reply_text(
        f"✅ הכותרת נשמרה: <b>{escape_html(title)}</b>\n\n"
        f"📁 כעת, בחר קטגוריה:",
        parse_mode='HTML',
        reply_markup=category_keyboard(categories, include_all=False)
    )
    
    return WAITING_FOR_CATEGORY

async def receive_prompt_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """קבלת קטגוריה ושמירת הפרומפט"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    raw_value = query.data.replace('cat_', '', 1)
    if raw_value == 'all':
        await query.answer("אנא בחר קטגוריה ספציפית", show_alert=True)
        return WAITING_FOR_CATEGORY
    category = unquote_plus(raw_value)
    category = db.ensure_category_name(user.id, category)
    
    # שמירת הפרומפט
    content = context.user_data.get('new_prompt_content')
    title = context.user_data.get('new_prompt_title')
    
    prompt = db.save_prompt(
        user_id=user.id,
        content=content,
        title=title,
        category=category
    )
    
    # ניקוי ההקשר
    context.user_data.clear()
    
    # הצגת הפרומפט החדש
    emoji_map = db.get_category_lookup(user.id)
    emoji = emoji_map.get(category, '📁')
    
    await query.edit_message_text(
        f"✅ <b>הפרומפט נשמר בהצלחה!</b>\n\n"
        f"📋 <b>{escape_html(title)}</b>\n"
        f"📁 קטגוריה: {emoji} {escape_html(category)}\n"
        f"📏 אורך: {len(content)} תווים\n"
        f"🆔 מזהה: <code>{str(prompt['_id'])}</code>\n\n"
        f"<i>הפרומפט זמין לשימוש!</i>",
        parse_mode='HTML',
        reply_markup=prompt_actions_keyboard(str(prompt['_id']))
    )
    
    return ConversationHandler.END

async def cancel_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ביטול תהליך השמירה"""
    context.user_data.clear()
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "❌ תהליך השמירה בוטל."
        )
    else:
        await update.message.reply_text(
            "❌ תהליך השמירה בוטל."
        )
    
    return ConversationHandler.END

# Quick save - שמירה מהירה מהודעה רגילה
async def quick_save_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """שמירה מהירה של הודעה שהועברה"""
    user = update.effective_user
    content = update.message.text or update.message.caption
    
    if not content or len(content) < 10:
        return  # לא מספיק ארוך להיחשב כפרומפט
    
    # בדיקה אם זה נראה כמו פרומפט
    prompt_indicators = ['you are', 'act as', 'imagine', 'create', 'write', 'generate']
    
    if any(indicator in content.lower() for indicator in prompt_indicators):
        # זה נראה כמו פרומפט - הצעה לשמירה
        await update.message.reply_text(
            "🤔 זה נראה כמו פרומפט!\n\n"
            "רוצה לשמור אותו?\n\n"
            "השתמש ב-/save כדי לשמור עם כל הפרטים.",
            reply_markup=back_button("new_prompt")
        )
