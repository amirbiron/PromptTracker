"""
מקלדות ותפריטים - Inline Keyboards
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict
import config

def main_menu_keyboard():
    """תפריט ראשי"""
    keyboard = [
        [
            InlineKeyboardButton("💾 שמור פרומפט", callback_data="new_prompt"),
            InlineKeyboardButton("📋 הפרומפטים שלי", callback_data="my_prompts")
        ],
        [
            InlineKeyboardButton("🔍 חיפוש", callback_data="search"),
            InlineKeyboardButton("⭐ מועדפים", callback_data="favorites")
        ],
        [
            InlineKeyboardButton("📁 קטגוריות", callback_data="categories"),
            InlineKeyboardButton("🏷️ תגיות", callback_data="tags")
        ],
        [
            InlineKeyboardButton("📊 סטטיסטיקות", callback_data="stats"),
            InlineKeyboardButton("⚙️ הגדרות", callback_data="settings")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def category_keyboard(include_all: bool = True):
    """מקלדת בחירת קטגוריה"""
    keyboard = []
    categories = list(config.CATEGORIES.items())
    
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

def pagination_keyboard(current_page: int, total_pages: int, prefix: str = "page"):
    """מקלדת דפדוף"""
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

def confirm_keyboard(action: str, item_id: str):
    """מקלדת אישור"""
    keyboard = [
        [
            InlineKeyboardButton("✅ כן", callback_data=f"confirm_{action}_{item_id}"),
            InlineKeyboardButton("❌ לא", callback_data=f"cancel_{action}_{item_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def tag_management_keyboard(prompt_id: str, existing_tags: List[str]):
    """מקלדת ניהול תגיות"""
    keyboard = []
    
    # תגיות קיימות
    for tag in existing_tags:
        keyboard.append([
            InlineKeyboardButton(
                f"🏷️ {tag}",
                callback_data="noop"
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

def prompt_list_item_keyboard(prompt_id: str, index: int):
    """כפתורים לפרומפט ברשימה"""
    keyboard = [
        [
            InlineKeyboardButton("👁️ צפה", callback_data=f"view_{prompt_id}"),
            InlineKeyboardButton("📋 העתק", callback_data=f"copy_{prompt_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_button(callback_data: str = "back_main"):
    """כפתור חזרה פשוט"""
    keyboard = [[InlineKeyboardButton("« חזרה", callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)
