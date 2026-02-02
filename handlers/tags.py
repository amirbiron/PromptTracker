"""
מטפלי ניהול תגיות
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from keyboards import tag_management_keyboard, back_button
import config
from utils import escape_html
from reporter_instance import reporter

# States
WAITING_FOR_NEW_TAG = 0

async def manage_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ניהול תגיות של פרומפט"""
    update.effective_user and reporter.report_activity(update.effective_user.id)
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    prompt_id = query.data.replace('tags_', '')
    
    prompt = db.get_prompt(prompt_id, user.id)
    
    if not prompt:
        await query.edit_message_text("⚠️ הפרומפט לא נמצא")
        return
    
    existing_tags = prompt.get('tags', [])
    
    text = f"🏷️ <b>ניהול תגיות</b>\n\n"
    text += f"📋 פרומפט: {escape_html(prompt['title'])}\n\n"
    
    if existing_tags:
        text += f"תגיות קיימות ({len(existing_tags)}):\n"
        for tag in existing_tags:
            text += f"• #{escape_html(tag)}\n"
    else:
        text += "<i>אין עדיין תגיות</i>\n"
    
    text += f"\n💡 <i>תגיות עוזרות למצוא פרומפטים במהירות</i>"
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=tag_management_keyboard(prompt_id, existing_tags)
    )

async def start_add_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """התחלת הוספת תגית"""
    query = update.callback_query
    await query.answer()
    
    prompt_id = query.data.replace('addtag_', '')
    context.user_data['adding_tag_to'] = prompt_id
    
    await query.edit_message_text(
        "🏷️ <b>הוספת תגית חדשה</b>\n\n"
        "שלח את שם התגית (ללא #)\n\n"
        "דוגמאות:\n"
        "• <code>python</code>\n"
        "• <code>telegram-bot</code>\n"
        "• <code>beginner</code>\n\n"
        "או שלח /cancel לביטול.",
        parse_mode='HTML'
    )
    
    return WAITING_FOR_NEW_TAG

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

async def remove_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הסרת תגית"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    _, prompt_id, tag = query.data.split('_', 2)
    
    prompt = db.get_prompt(prompt_id, user.id)
    
    if not prompt:
        await query.answer("⚠️ הפרומפט לא נמצא", show_alert=True)
        return
    
    # הסרת התגית
    existing_tags = prompt.get('tags', [])
    
    if tag in existing_tags:
        existing_tags.remove(tag)
        db.update_prompt(prompt_id, user.id, {'tags': existing_tags})
        await query.answer(f"✅ התגית #{tag} הוסרה")
        
        # רענון התצוגה
        await manage_tags(update, context)
    else:
        await query.answer("⚠️ התגית לא נמצאה", show_alert=True)

async def cancel_add_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ביטול הוספת תגית"""
    prompt_id = context.user_data.get('adding_tag_to')
    context.user_data.clear()
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "❌ ההוספה בוטלה.",
            reply_markup=back_button(f"tags_{prompt_id}" if prompt_id else "back_main")
        )
    else:
        await update.message.reply_text(
            "❌ ההוספה בוטלה.",
            reply_markup=back_button(f"tags_{prompt_id}" if prompt_id else "back_main")
        )
    
    return ConversationHandler.END
