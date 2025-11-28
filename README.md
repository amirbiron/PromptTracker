# 🚀 PromptTracker Bot

בוט טלגרם לניהול וארגון פרומפטים למודלים של AI (ChatGPT, Claude, Midjourney ועוד).

## ✨ תכונות

### 💾 שמירת פרומפטים
- שמירה פשוטה ומהירה
- הוספת כותרת וקטגוריה
- תמיכה בפרומפטים עד 4000 תווים

### 📁 ארגון
- 10 קטגוריות מוכנות (Bots, Design, Code, וכו')
- תגיות מותאמות אישית
- מערכת מועדפים

### 🔍 חיפוש
- חיפוש מלא בתוכן ובכותרת
- סינון לפי קטגוריה
- סינון לפי תגיות
- רשימת הפרומפטים הפופולריים

### ✏️ עריכה
- עריכת תוכן וכותרת
- שינוי קטגוריה
- ניהול תגיות
- מחיקה רכה עם סל מחזור (30 יום)

### 📋 שימוש
- העתקה בלחיצה אחת
- מעקב אחר מספר שימושים
- סטטיסטיקות מפורטות

## 🛠️ התקנה

### דרישות מקדימות
- Python 3.11+
- MongoDB Atlas (חשבון חינמי)
- Telegram Bot Token

### התקנה מקומית

1. **שכפל את הריפו:**
```bash
git clone https://github.com/yourusername/PromptTracker.git
cd PromptTracker
```

2. **צור סביבה וירטואלית:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# או
venv\Scripts\activate  # Windows
```

3. **התקן תלויות:**
```bash
pip install -r requirements.txt
```

4. **הגדר משתני סביבה:**
```bash
cp .env.example .env
```

ערוך את `.env` והוסף:
- `BOT_TOKEN` - Token מ-@BotFather
- `MONGO_URI` - URI של MongoDB Atlas
- `ADMIN_USER_ID` - ה-Telegram ID שלך

5. **הרץ את הבוט:**
```bash
python bot.py
```

## 🚀 פריסה ב-Render

### שלב 1: יצירת MongoDB Atlas

1. הירשם ל-[MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. צור Cluster חינמי (M0)
3. צור Database User
4. הוסף את IP: `0.0.0.0/0` ל-Network Access
5. העתק את ה-Connection String

### שלב 2: יצירת בוט טלגרם

1. דבר עם [@BotFather](https://t.me/BotFather)
2. שלח `/newbot`
3. בחר שם ו-username לבוט
4. העתק את ה-Token

### שלב 3: פריסה ב-Render

1. הירשם ל-[Render](https://render.com)
2. לחץ על "New +" → "Web Service"
3. חבר את הריפו שלך מ-GitHub
4. הגדרות:
   - **Name**: `prompttracker-bot`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`

5. הוסף Environment Variables:
   - `BOT_TOKEN` - הטוקן מ-BotFather
   - `MONGO_URI` - Connection String מ-MongoDB Atlas
   - `MONGO_DB_NAME` - `prompttracker`
   - `ADMIN_USER_ID` - ה-Telegram ID שלך
   - `ENVIRONMENT` - `production`

6. לחץ "Create Web Service"

### שלב 4: בדיקה

1. פתח את הבוט בטלגרם
2. שלח `/start`
3. אם הכל עובד - תראה את התפריט הראשי! 🎉

## 📱 שימוש בבוט

### פקודות זמינות

- `/start` - תפריט ראשי
- `/save` - שמור פרומפט חדש
- `/list` - הצג את כל הפרומפטים
- `/search` - חיפוש פרומפטים
- `/favorites` - פרומפטים מועדפים
- `/stats` - סטטיסטיקות
- `/statsA` - סטטיסטיקות מנהל (אדמין בלבד)
- `/categories` - קטגוריות
- `/tags` - תגיות
- `/trash` - סל מחזור
- `/help` - עזרה

### זרימת עבודה מומלצת

1. **שמור פרומפט:**
   - `/save` → הדבק פרומפט → הוסף כותרת → בחר קטגוריה

2. **ארגן:**
   - הוסף תגיות לפרומפטים דומים
   - סמן חשובים במועדפים ⭐

3. **השתמש:**
   - `/list` או `/search` כדי למצוא
   - לחץ "📋 העתק" כדי להעתיק
   - הדבק ב-ChatGPT/Claude

## 🔧 קונפיגורציה

### קטגוריות

הבוט מגיע עם 10 קטגוריות מוכנות:

- 🤖 Bots
- 🎨 Design
- 📚 Documentation
- 💻 Code
- ✍️ Writing
- 📊 Data
- 🔍 Research
- 📧 Communication
- 🎓 Education
- ⚙️ Other

ניתן לשנות ב-`config.py`

### הגבלות

- אורך מקסימלי לפרומפט: 4000 תווים
- פרומפטים בעמוד: 10
- מקסימום תגיות לפרומפט: 10
- זמן שמירה בסל מחזור: 30 יום

ניתן לשנות ב-`config.py`

## 📊 מבנה הפרויקט

```
PromptTracker/
├── bot.py                 # קובץ ראשי
├── database.py           # מודול MongoDB
├── keyboards.py          # מקלדות inline
├── config.py            # הגדרות
├── handlers/
│   ├── save.py          # שמירת פרומפטים
│   ├── manage.py        # ניהול פרומפטים
│   └── search.py        # חיפוש וסינון
├── requirements.txt     # תלויות Python
├── Dockerfile          # Docker image
├── render.yaml         # הגדרות Render
└── README.md           # תיעוד זה
```

## 🐛 בעיות נפוצות

### הבוט לא מגיב
- בדוק את הלוגים ב-Render
- וודא ש-BOT_TOKEN נכון
- בדוק חיבור ל-MongoDB

### שגיאת חיבור ל-MongoDB
- וודא ש-MONGO_URI נכון
- בדוק ש-IP של Render מורשה ב-Network Access
- בדוק שיש Database User

### הבוט נופל אחרי זמן מה
- Render (Free tier) עוצר את הסרוויס אחרי חוסר פעילות
- שדרג ל-Paid tier או השתמש ב-Uptime Monitor

## 🔐 אבטחה

- כל משתמש רואה רק את הפרומפטים שלו
- התחברות אוטומטית דרך Telegram ID
- מחיקה רכה עם אפשרות שחזור
- ניקוי אוטומטי של מחיקות ישנות

## 🚀 תכונות עתידיות

- [ ] שיתוף פרומפטים עם משתמשים אחרים
- [ ] אוספים (Collections)
- [ ] תבניות (Templates) עם משתנים
- [ ] ייצוא ל-JSON/CSV
- [ ] Web App משלים
- [ ] קהילת פרומפטים
- [ ] AI Suggestions לשיפור פרומפטים

## 📝 רישיון

MIT License - ראה LICENSE

## 👨‍💻 מפתח

נוצר עם ❤️ על ידי [השם שלך]

## 🤝 תרומה

Pull Requests יתקבלו בברכה!

1. Fork the project
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📞 תמיכה

יש בעיה או שאלה?
- פתח Issue ב-GitHub
- צור קשר ב-Telegram: @YourUsername

---

**PromptTracker** - ארגן את הפרומפטים שלך פעם אחת, השתמש לנצח! 🚀
