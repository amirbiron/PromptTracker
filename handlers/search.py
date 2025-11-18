"""
מטפלי חיפוש וסינון
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from urllib.parse import quote_plus, unquote_plus
from database import db
from keyboards import category_keyboard, back_button, main_menu_keyboard
from utils import escape_html

CATEGORY_ADDING, CATEGORY_RENAMING = range(2)
SEARCH_FLAG = "awaiting_search_query"

def _looks_like_emoji(token: str) -> bool:
    if not token:
        return False
    token = token.strip()
    if not token or len(token) > 4:
        return False
    return not all(ch.isalnum() for ch in token)


def _parse_category_input(raw_text: str):
    """
    מחזיר tuple (emoji or None, name or None) מתוך טקסט שהוזן על ידי המשתמש.
    ניתן להתחיל באימוג׳י ואחריו שם הקטגוריה, למשל: "🤖 בוטים".
    """
    text = (raw_text or "").strip()
    if not text:
        return None, None
    parts = text.split(maxsplit=1)
    if len(parts) == 2 and _looks_like_emoji(parts[0]):
        emoji = parts[0][:4]
        name = parts[1].strip()
        return emoji, name
    return None, text

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
    category_lookup = db.get_category_lookup(user.id)
    
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
        emoji = category_lookup.get(prompt['category'], '📁')
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
    
    raw_value = query.data.replace('cat_', '', 1)
    user = update.effective_user
    
    if raw_value == 'all':
        # הצגת כל הפרומפטים
        from handlers.manage import view_my_prompts
        return await view_my_prompts(update, context)
    
    category = db.ensure_category_name(user.id, unquote_plus(raw_value))
    category_lookup = db.get_category_lookup(user.id)
    # סינון לפי קטגוריה
    prompts = db.search_prompts(user.id, category=category, limit=50)
    
    if not prompts:
        emoji = category_lookup.get(category, '📁')
        await query.edit_message_text(
            f"📁 <b>{emoji} {escape_html(category)}</b>\n\n"
            f"אין פרומפטים בקטגוריה זו.",
            parse_mode='HTML',
            reply_markup=back_button("categories")
        )
        return
    
    # הצגת תוצאות
    emoji = category_lookup.get(category, '📁')
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
    
    categories = db.get_user_categories(user.id)
    
    # ספירת פרומפטים לכל קטגוריה
    text = "📁 <b>קטגוריות</b>\n\n"
    text += "בחר קטגוריה לצפייה:\n\n"
    
    any_counts = False
    for item in categories:
        name = item.get('name')
        emoji = item.get('emoji', '📁')
        count = db.count_prompts(user.id, category=name)
        if count > 0:
            any_counts = True
            text += f"{emoji} <b>{escape_html(name)}</b>: {count} פרומפטים\n"
    
    if not any_counts:
        text += "<i>עוד אין פרומפטים בקטגוריות שלך.</i>\n"
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=category_keyboard(categories, include_all=True, show_manage_button=True)
    )

async def manage_categories(update: Update, context: ContextTypes.DEFAULT_TYPE, notice: str = None, skip_answer: bool = False):
    """תצוגת ניהול קטגוריות אישיות."""
    query = update.callback_query
    message = update.effective_message
    if query and not skip_answer:
        await query.answer()
    user = update.effective_user
    categories = db.get_user_categories(user.id)
    text = "⚙️ <b>ניהול קטגוריות</b>\n"
    if notice:
        text += f"{notice}\n"
    text += "\nלחץ על קטגוריה כדי לערוך שם/אימוג׳י.\n"
    text += "כפתור 🗑️ יסיר את הקטגוריה (הפרומפטים יעברו לקטגוריית fallback).\n\n"
    
    keyboard = []
    can_delete = len(categories) > 1
    if not categories:
        text += "<i>עוד לא יצרת קטגוריות מותאמות אישית.</i>\n\n"
    for item in categories:
        name = item.get('name', '')
        if not name:
            continue
        emoji = item.get('emoji', '📁')
        encoded = quote_plus(name)
        row = [InlineKeyboardButton(f"{emoji} {name}", callback_data=f"catcfg_edit_{encoded}")]
        if can_delete:
            row.append(InlineKeyboardButton("🗑️", callback_data=f"catcfg_remove_{encoded}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("➕ הוסף קטגוריה חדשה", callback_data="catcfg_add")])
    keyboard.append([InlineKeyboardButton("« חזרה", callback_data="categories")])
    
    markup = InlineKeyboardMarkup(keyboard)
    if query:
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=markup
        )
    elif message:
        await message.reply_text(
            text,
            parse_mode='HTML',
            reply_markup=markup
        )

async def start_add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """תחילת תהליך הוספת קטגוריה."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "➕ <b>קטגוריה חדשה</b>\n\n"
        "שלח שם לקטגוריה החדשה.\n"
        "אפשר להתחיל באימוג׳י ולאחריו השם (לדוגמה: 🤖 בוטים).\n\n"
        "או שלח <code>בטל</code> לביטול.",
        parse_mode='HTML'
    )
    return CATEGORY_ADDING

async def receive_new_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """קבלת שם לקטגוריה חדשה."""
    user = update.effective_user
    # תמיכה בביטול באמצעות המילה "בטל"
    incoming_text = (update.message.text or "").strip()
    if incoming_text == "בטל":
        return await cancel_category_edit(update, context)

    emoji, name = _parse_category_input(incoming_text)
    
    if not name:
        await update.message.reply_text(
            "⚠️ אנא הזן שם תקין לקטגוריה (לפחות שני תווים)."
        )
        return CATEGORY_ADDING
    
    if not emoji:
        emoji = "📁"
    
    try:
        db.add_user_category(user.id, name, emoji)
    except ValueError as exc:
        await update.message.reply_text(f"⚠️ {escape_html(str(exc))}", parse_mode='HTML')
        return CATEGORY_ADDING
    
    context.user_data.pop('category_edit_target', None)
    notice = f"✅ נוספה קטגוריה חדשה: {emoji} <b>{escape_html(name)}</b>"
    await manage_categories(update, context, notice)
    return ConversationHandler.END

async def start_edit_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """תחילת עריכת קטגוריה קיימת."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    raw_value = query.data.replace('catcfg_edit_', '', 1)
    decoded = unquote_plus(raw_value)
    
    category = db.get_category(user.id, decoded)
    if not category:
        await query.edit_message_text(
            "⚠️ הקטגוריה לא נמצאה.",
            parse_mode='HTML',
            reply_markup=back_button("catcfg_manage")
        )
        return ConversationHandler.END
    
    context.user_data['category_edit_target'] = category.get('name')
    await query.edit_message_text(
        "✏️ <b>עריכת קטגוריה</b>\n\n"
        f"נוכחי: {category.get('emoji', '📁')} <b>{escape_html(category.get('name', ''))}</b>\n"
        "שלח שם חדש (אפשר להתחיל באימוג׳י) כדי לעדכן. לדוגמה:\n"
        "<code>✍️ כתיבה יצירתית</code>\n\n"
        "או שלח <code>בטל</code> לביטול.",
        parse_mode='HTML'
    )
    return CATEGORY_RENAMING

async def receive_updated_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """קבלת שם מעודכן לקטגוריה."""
    user = update.effective_user
    original_name = context.user_data.get('category_edit_target')
    if not original_name:
        await update.message.reply_text(
            "⚠️ לא נמצאה קטגוריה לעריכה.",
            reply_markup=back_button("catcfg_manage")
        )
        return ConversationHandler.END
    
    # תמיכה בביטול באמצעות המילה "בטל"
    incoming_text = (update.message.text or "").strip()
    if incoming_text == "בטל":
        return await cancel_category_edit(update, context)

    emoji, name = _parse_category_input(incoming_text)
    if not name:
        await update.message.reply_text("⚠️ אנא הזן שם תקין (לפחות שני תווים).")
        return CATEGORY_RENAMING
    
    if not emoji:
        current = db.get_category(user.id, original_name)
        emoji = (current or {}).get('emoji', '📁')
    
    try:
        db.update_user_category(user.id, original_name, name, emoji)
    except ValueError as exc:
        await update.message.reply_text(f"⚠️ {escape_html(str(exc))}", parse_mode='HTML')
        return CATEGORY_RENAMING
    
    context.user_data.pop('category_edit_target', None)
    notice = f"✅ עודכן ל-{emoji} <b>{escape_html(name)}</b>"
    await manage_categories(update, context, notice)
    return ConversationHandler.END

async def start_remove_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הצגת מסך אישור להסרת קטגוריה."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    raw_value = query.data.replace('catcfg_remove_', '', 1)
    decoded = unquote_plus(raw_value)
    
    categories = db.get_user_categories(user.id)
    if len(categories) <= 1:
        await query.answer("⚠️ חייבת להישאר לפחות קטגוריה אחת.", show_alert=True)
        return
    
    category = db.get_category(user.id, decoded)
    if not category:
        await query.answer("⚠️ הקטגוריה לא נמצאה.", show_alert=True)
        return
    
    name = category.get('name', '')
    emoji = category.get('emoji', '📁')
    encoded = quote_plus(name)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ מחק", callback_data=f"catcfg_remove_confirm_{encoded}"),
            InlineKeyboardButton("❌ בטל", callback_data="catcfg_manage")
        ]
    ])
    await query.edit_message_text(
        "🗑️ <b>מחיקת קטגוריה</b>\n\n"
        f"האם להסיר את {emoji} <b>{escape_html(name)}</b>?\n"
        "כל הפרומפטים בקטגוריה זו יעברו אוטומטית לקטגוריית fallback.",
        parse_mode='HTML',
        reply_markup=keyboard
    )

async def apply_remove_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ביצוע הסרת קטגוריה לאחר אישור."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    raw_value = query.data.replace('catcfg_remove_confirm_', '', 1)
    decoded = unquote_plus(raw_value)
    
    category = db.get_category(user.id, decoded)
    if not category:
        await query.edit_message_text(
            "⚠️ הקטגוריה כבר אינה קיימת.",
            parse_mode='HTML',
            reply_markup=back_button("catcfg_manage")
        )
        return
    
    try:
        fallback = db.delete_user_category(user.id, category.get('name'))
    except ValueError as exc:
        await query.edit_message_text(
            f"⚠️ {escape_html(str(exc))}",
            parse_mode='HTML',
            reply_markup=back_button("catcfg_manage")
        )
        return
    
    notice = (
        f"🗑️ הקטגוריה <b>{escape_html(category.get('name', ''))}</b> הוסרה.\n"
        f"פרומפטים הועברו ל-<b>{escape_html(fallback)}</b>."
    )
    await manage_categories(update, context, notice, skip_answer=True)

async def cancel_category_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ביטול תהליך הוספה/עריכת קטגוריה."""
    context.user_data.pop('category_edit_target', None)
    
    if update.callback_query:
        await update.callback_query.answer()
        await manage_categories(update, context, "❌ הפעולה בוטלה.", skip_answer=True)
    else:
        await update.message.reply_text(
            "❌ הפעולה בוטלה.",
            reply_markup=back_button("catcfg_manage")
        )
    return ConversationHandler.END

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
    category_lookup = db.get_category_lookup(user.id)
    
    if not prompts:
        text = "🔥 <b>פרומפטים פופולריים</b>\n\n"
        text += "אין עדיין נתונים על שימוש.\n\n"
        text += "השתמש בפרומפטים שלך (העתק) כדי לאסוף נתונים."
    else:
        text = "🔥 <b>הפרומפטים הפופולריים ביותר</b>\n\n"
        
        for i, prompt in enumerate(prompts, 1):
            emoji = category_lookup.get(prompt['category'], '📁')
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