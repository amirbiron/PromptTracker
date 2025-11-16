# Dockerfile לפריסה ב-Render
FROM python:3.11-slim

# הגדרת תיקיית עבודה
WORKDIR /app

# העתקת קבצי requirements
COPY requirements.txt .

# התקנת תלויות
RUN pip install --no-cache-dir -r requirements.txt

# העתקת כל הקבצים
COPY . .

# הגדרת משתני סביבה
ENV PYTHONUNBUFFERED=1

# הרצת הבוט
CMD ["python", "bot.py"]
