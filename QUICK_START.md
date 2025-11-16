# 🚀 התחלה מהירה - PromptTracker

## תהליך פריסה מהיר ב-5 דקות

### 📋 מה צריך להכין

לפני שמתחילים, תצטרך:

1. ✅ חשבון GitHub (חינמי)
2. ✅ חשבון Render (חינמי)
3. ✅ חשבון MongoDB Atlas (חינמי)
4. ✅ בוט טלגרם (חינמי)

---

## שלב 1️⃣: יצירת בוט טלגרם (דקה אחת)

1. פתח את [@BotFather](https://t.me/BotFather) בטלגרם
2. שלח: `/newbot`
3. שלח שם לבוט (למשל: `My Prompt Manager`)
4. שלח username (למשל: `my_prompt_bot`)
5. **העתק את הטוקן** שקיבלת - תצטרך אותו!

```
📝 שמור את הטוקן הזה:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567
```

---

## שלב 2️⃣: יצירת MongoDB Atlas (3 דקות)

### א. הרשמה
1. לך ל-[MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. לחץ "Try Free"
3. הירשם (אימייל או Google)

### ב. יצירת Cluster
1. בחר **M0 FREE** (זה חינמי לנצח!)
2. בחר Region קרוב (למשל Frankfurt)
3. לחץ "Create Cluster"
4. המתן 2-3 דקות ליצירה

### ג. הגדרת גישה
1. לחץ "Database Access" בתפריט צד
2. "Add New Database User"
   - Username: `promptbot`
   - Password: **צור סיסמה חזקה ושמור!**
   - לחץ "Add User"

3. לחץ "Network Access"
4. "Add IP Address"
   - לחץ "Allow Access from Anywhere"
   - לחץ "Confirm"

### ד. קבלת Connection String
1. חזור ל-"Database"
2. לחץ "Connect" על הקלאסטר
3. בחר "Connect your application"
4. העתק את ה-URI
5. **החלף את `<password>`** בסיסמה שיצרת!

```
📝 שמור את ה-URI הזה:
mongodb+srv://promptbot:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/
```

---

## שלב 3️⃣: קבלת ה-Telegram ID שלך (30 שניות)

1. פתח את [@userinfobot](https://t.me/userinfobot) בטלגרם
2. שלח `/start`
3. **העתק את ה-ID** שקיבלת

```
📝 שמור את ה-ID:
123456789
```

---

## שלב 4️⃣: פריסה ב-Render (דקה אחת)

### א. Fork הריפו
1. לך לריפו ב-GitHub
2. לחץ "Fork" בפינה ימנית למעלה
3. המתן שהפורק יסתיים

### ב. חיבור ל-Render
1. לך ל-[Render](https://render.com)
2. הירשם עם GitHub
3. לחץ "New +" → "Web Service"
4. בחר את הריפו `PromptTracker` שיצרת

### ג. הגדרות
1. **Name**: `prompttracker-bot`
2. **Region**: Frankfurt (או קרוב אליך)
3. **Branch**: `main`
4. **Runtime**: Python 3
5. **Build Command**: `pip install -r requirements.txt`
6. **Start Command**: `python bot.py`

### ד. Environment Variables
לחץ "Advanced" ואז "Add Environment Variable".
הוסף את המשתנים הבאים:

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | הטוקן מהבוט (**שלב 1**) |
| `MONGO_URI` | ה-URI מ-MongoDB (**שלב 2**) |
| `MONGO_DB_NAME` | `prompttracker` |
| `ADMIN_USER_ID` | ה-Telegram ID שלך (**שלב 3**) |
| `ENVIRONMENT` | `production` |

### ה. Deploy!
1. לחץ "Create Web Service"
2. המתן 2-3 דקות לפריסה
3. כשהסטטוס יהיה "Live" בירוק - הבוט פעיל! 🎉

---

## שלב 5️⃣: בדיקה (10 שניות)

1. פתח את הבוט בטלגרם (ה-username שיצרת)
2. שלח `/start`
3. אמור לראות תפריט עם כפתורים
4. נסה לשמור פרומפט ראשון!

---

## ✅ זהו! הבוט עובד!

### מה עכשיו?

**תתחיל להשתמש:**
- שלח `/save` כדי לשמור פרומפט ראשון
- השתמש בקטגוריות לארגון
- הוסף תגיות לפרומפטים

**התאם אישית:**
- ערוך `config.py` לשינוי קטגוריות
- הוסף תכונות חדשות ב-`handlers/`
- שנה הודעות בעברית/אנגלית

---

## 🐛 בעיות? תיקונים מהירים

### הבוט לא מגיב
```bash
# בדוק לוגים ב-Render:
1. לך לדשבורד של Render
2. לחץ על השירות שלך
3. לחץ על "Logs"
4. חפש שגיאות אדומות
```

### שגיאת MongoDB
```
⚠️ שגיאה: "Authentication failed"

פתרון:
1. בדוק שהסיסמה נכונה ב-MONGO_URI
2. וודא שהחלפת <password> בסיסמה האמיתית
3. בדוק שה-User קיים ב-Database Access
```

### הבוט נופל אחרי כמה שעות
```
ℹ️ זה נורמלי ב-Free Tier של Render

Render מפסיק שירותים אחרי 15 דקות של חוסר שימוש.
הוא יתעורר אוטומטית כשמישהו ישתמש בבוט.

פתרון: שדרג ל-Paid tier ($7/חודש) או השתמש ב-Uptime Monitor.
```

---

## 📞 עזרה נוספת

- 📖 קרא את [README.md](README.md) המלא
- 🐛 פתח Issue ב-GitHub
- 💬 צור קשר בטלגרם

---

**מזל טוב! 🎉**
הבוט שלך פעיל ומוכן לשימוש!
