"""
מטפלי ניהול פרומפטים - צפייה, עריכה, מחיקה
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from urllib.parse import unquote_plus
from database import db
from keyboards import (
    prompt_actions_keyboard, 
    pagination_keyboard,
    edit_menu_keyboard,
    confirm_keyboard,
    back_button,
    prompt_list_item_keyboard,
    category_keyboard
)
import config
from bson import ObjectId
from utils import escape_html, code_block, code_inline
from reporter_instance import reporter

# States
EDITING_CONTENT, EDITING_TITLE = range(2)
CHANGING_CATEGORY = 2

async def view_my_prompts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הצגת רשימת הפרומפטים"""
    update.effective_user and reporter.report_activity(update.effective_user.id)
    query = update.callback_query
    if query:
        await query.answer()
    
    user = update.effective_user
    category_lookup = db.get_category_lookup(user.id)
    
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
                text,
                parse_mode='HTML',
                reply_markup=back_button("back_main")
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode='HTML'
            )
        return
    
    # בניית הטקסט
    text = f"📋 <b>הפרומפטים שלי</b> ({total_count} סה״כ)\n\n"
    
    for i, prompt in enumerate(prompts, start=skip + 1):
        emoji = category_lookup.get(prompt['category'], '📁')
        fav = "⭐ " if prompt.get('is_favorite') else ""
        
        title = prompt['title']
        if len(title) > 40:
            title = title[:40] + "..."
        
        text += f"{i}. {fav}📝 <b>{escape_html(title)}</b>\n"
        text += f"   {emoji} {escape_html(prompt['category'])}\n"
        
        # תגיות
        if prompt.get('tags'):
            tags_str = " ".join([f"#{escape_html(tag)}" for tag in prompt['tags'][:3]])
            text += f"   🏷️ {tags_str}\n"
        
        text += f"   /view_{escape_html(prompt.get('short_code', str(prompt['_id'])))}\n\n"
    
    # דפדוף
    total_pages = (total_count + config.PROMPTS_PER_PAGE - 1) // config.PROMPTS_PER_PAGE
    
    if query:
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=pagination_keyboard(page, total_pages, "page")
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode='HTML',
            reply_markup=pagination_keyboard(page, total_pages, "page")
        )

async def view_prompt_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הצגת פרומפט מלא"""
    update.effective_user and reporter.report_activity(update.effective_user.id)
    query = update.callback_query
    prompt_id = None
    if query:
        await query.answer()
        data = query.data
        if isinstance(data, str) and data.startswith('view_'):
            prompt_id = data.replace('view_', '')
    # Fallback: when another action wants to refresh details
    if not prompt_id:
        cb = context.user_data.get('callback_data') if hasattr(context, 'user_data') else None
        if isinstance(cb, str) and cb.startswith('view_'):
            prompt_id = cb.replace('view_', '')
            # clear the helper to avoid stale usage
            try:
                context.user_data.pop('callback_data', None)
            except Exception:
                pass
    # From command argument
    if not prompt_id:
        prompt_id = context.args[0] if getattr(context, 'args', None) else None
    
    if not prompt_id:
        return
    
    user = update.effective_user
    prompt = db.get_prompt(prompt_id, user.id)
    
    if not prompt:
        text = "⚠️ הפרומפט לא נמצא או שנמחק."
        if query:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return
    
    # בניית ההודעה
    category_lookup = db.get_category_lookup(user.id)
    emoji = category_lookup.get(prompt['category'], '📁')
    fav = "⭐ " if prompt.get('is_favorite') else ""
    
    text = f"{fav}<b>{escape_html(prompt['title'])}</b>\n"
    text += f"{'━' * 30}\n\n"
    text += f"{escape_html(prompt['content'])}\n\n"
    text += f"{'━' * 30}\n"
    text += f"📊 <b>פרטים:</b>\n"
    text += f"• קוד: {code_inline(prompt.get('short_code', prompt_id))}\n"
    text += f"• קטגוריה: {emoji} {escape_html(prompt['category'])}\n"
    text += f"• אורך: {prompt['length']} תווים\n"
    text += f"• שימושים: {prompt['use_count']} פעמים\n"
    text += f"• נוצר: {prompt['created_at'].strftime('%d/%m/%Y')}\n"
    
    if prompt.get('tags'):
        tags_str = " ".join([f"#{escape_html(tag)}" for tag in prompt['tags']])
        text += f"• תגיות: {tags_str}\n"
    
    keyboard = prompt_actions_keyboard(str(prompt['_id']), prompt.get('is_favorite', False))
    
    if query:
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode='HTML',
            reply_markup=keyboard
        )

async def handle_view_command_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """תמיכה בפקודת /view וב-/view_<id> הנשלחים כטקסט"""
    update.effective_user and reporter.report_activity(update.effective_user.id)
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

async def copy_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """העתקת פרומפט"""
    update.effective_user and reporter.report_activity(update.effective_user.id)
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    prompt_id = query.data.replace('copy_', '')
    
    prompt = db.get_prompt(prompt_id, user.id)
    
    if not prompt:
        await query.answer("⚠️ הפרומפט לא נמצא", show_alert=True)
        return
    
    # עדכון מונה שימושים
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

async def start_edit_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """התחלת עריכת פרומפט"""
    query = update.callback_query
    await query.answer()
    
    prompt_id = query.data.replace('edit_', '')
    
    await query.edit_message_text(
        "✏️ <b>עריכת פרומפט</b>\n\n"
        "מה תרצה לערוך?",
        parse_mode='HTML',
        reply_markup=edit_menu_keyboard(prompt_id)
    )

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
    
    context.user_data.clear()
    return ConversationHandler.END

async def start_edit_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """עריכת כותרת"""
    query = update.callback_query
    await query.answer()
    
    prompt_id = query.data.replace('edit_title_', '')
    context.user_data['editing_prompt_id'] = prompt_id
    
    await query.edit_message_text(
        "📋 <b>עריכת כותרת</b>\n\n"
        "שלח את הכותרת החדשה.\n\n"
        "או שלח /cancel לביטול.",
        parse_mode='HTML'
    )
    
    return EDITING_TITLE

async def start_change_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """התחלת שינוי קטגוריה"""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    prompt_id = query.data.replace('chcat_', '')
    context.user_data['changing_category_for'] = prompt_id
    categories = db.get_user_categories(user.id)
    await query.edit_message_text(
        "📁 <b>שינוי קטגוריה</b>\n\nבחר קטגוריה חדשה:",
        parse_mode='HTML',
        reply_markup=category_keyboard(categories, include_all=False)
    )
    return CHANGING_CATEGORY

async def apply_new_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """יישום קטגוריה חדשה לפרומפט"""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    prompt_id = context.user_data.get('changing_category_for')
    if not prompt_id:
        await query.edit_message_text("⚠️ שגיאה: לא נמצא פרומפט לשינוי קטגוריה.")
        return ConversationHandler.END
    raw_value = query.data.replace('cat_', '', 1)
    if raw_value == 'all':
        await query.answer("אנא בחר קטגוריה ספציפית", show_alert=True)
        return CHANGING_CATEGORY
    category = db.ensure_category_name(user.id, unquote_plus(raw_value))
    success = db.update_prompt(prompt_id, user.id, {'category': category})
    if success:
        await query.edit_message_text(
            "✅ הקטגוריה עודכנה בהצלחה!",
            reply_markup=back_button(f"view_{prompt_id}")
        )
    else:
        await query.edit_message_text("⚠️ שגיאה בעדכון הקטגוריה")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_change_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ביטול שינוי קטגוריה"""
    prompt_id = context.user_data.get('changing_category_for')
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "❌ שינוי הקטגוריה בוטל.",
            reply_markup=back_button(f"view_{prompt_id}" if prompt_id else "back_main")
        )
    else:
        await update.message.reply_text(
            "❌ שינוי הקטגוריה בוטל.",
            reply_markup=back_button(f"view_{prompt_id}" if prompt_id else "back_main")
        )
    return ConversationHandler.END

async def receive_new_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """קבלת כותרת חדשה"""
    user = update.effective_user
    new_title = update.message.text
    prompt_id = context.user_data.get('editing_prompt_id')
    
    if not prompt_id:
        await update.message.reply_text("⚠️ שגיאה: לא נמצא פרומפט לעריכה")
        return ConversationHandler.END
    
    success = db.update_prompt(prompt_id, user.id, {'title': new_title})
    
    if success:
        await update.message.reply_text(
            "✅ הכותרת עודכנה בהצלחה!",
            reply_markup=back_button(f"view_{prompt_id}")
        )
    else:
        await update.message.reply_text("⚠️ שגיאה בעדכון הכותרת")
    
    context.user_data.clear()
    return ConversationHandler.END

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

async def view_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הצגת מועדפים"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    prompts = db.get_favorites(user.id)
    
    if not prompts:
        await query.edit_message_text(
            "⭐ <b>המועדפים שלי</b>\n\n"
            "אין לך פרומפטים מועדפים עדיין.\n\n"
            "הוסף פרומפטים למועדפים דרך כפתור ⭐",
            parse_mode='HTML',
            reply_markup=back_button("back_main")
        )
        return
    
    text = f"⭐ <b>המועדפים שלי</b> ({len(prompts)})\n\n"
    
    category_lookup = db.get_category_lookup(user.id)
    for i, prompt in enumerate(prompts[:20], 1):  # מגביל ל-20
        emoji = category_lookup.get(prompt['category'], '📁')
        title = prompt['title']
        if len(title) > 40:
            title = title[:40] + "..."
        
        text += f"{i}. {emoji} <b>{escape_html(title)}</b>\n"
        text += f"   /view_{escape_html(prompt.get('short_code', str(prompt['_id'])))}\n\n"
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=back_button("back_main")
    )
