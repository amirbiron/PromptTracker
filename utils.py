"""
Utilities for safely rendering text in Telegram with HTML parse mode.
"""

from typing import Any, Optional

import config


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


def is_admin_user(user_id: Optional[int]) -> bool:
    """Return True if the given Telegram user_id matches the configured admin."""
    if not user_id:
        return False
    if not config.ADMIN_USER_ID:
        return False
    return int(user_id) == int(config.ADMIN_USER_ID)
