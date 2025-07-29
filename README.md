# 🤖 OfferBot – Discord Suggestion Bot

OfferBot הוא בוט לדיסקורד שמנהל הצעות של משתמשים על בסיס תגובות.  
הבוט משתמש ב־✅ / ❌ כדי להחליט האם לפתוח טיקט להצעה.  
הוא שומר נתונים ב־Firebase וכולל ניהול דרך פקודות Slash.

---

## 🚀 תכונות עיקריות

- תיעוד אוטומטי של הצעות
- פתיחת טיקט כאשר הצעה מקבלת מספיק תגובות ✅
- סף מקסימלי של ❌ למחיקה אוטומטית
- מערכת Crew Roles לניהול הצעות
- מערכת תגים למציעים טובים
- שמירה וניהול ב־Firebase
- פקודת `/remove_offerbot` למחיקת כל הדאטה והבוט מהשרת

---

## 🛠️ התקנה מקומית

### דרישות מוקדמות

- Python 3.9 או חדש יותר
- חשבון Firebase + קובץ `serviceAccountKey.json`
- טוקן דיסקורד בוט

### התקנה

```bash
git clone https://github.com/yourusername/offerbot.git
cd offerbot
pip install -r requirements.txt
