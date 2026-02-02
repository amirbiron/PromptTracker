"""
Shared activity reporter instance.

Imported by handlers to report user activity without circular imports.
"""

# בראש הקובץ
from activity_reporter import create_reporter

# Ensure env vars are loaded before creating the reporter (config calls load_dotenv()).
import config  # noqa: F401

# ה (שמור בראש הקובץ אחרי טעינת משתנים)
reporter = create_reporter(
    mongodb_uri="mongodb+srv://mumin:M43M2TFgLfGvhBwY@muminai.tm6x81b.mongodb.net/?retryWrites=true&w=majority&appName=muminAI",
    service_id="srv-d4cpmuf5r7bs73aindc0",
    service_name="PromptTracker",
)
