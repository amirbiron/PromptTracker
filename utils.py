"""
Utilities for safely rendering text in Telegram with HTML parse mode.
"""

from typing import Any


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
