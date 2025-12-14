# راه‌اندازی فایل .env

## مشکل: برنامه فایل .env را نمی‌خواند

اگر فایل `.env` را تغییر دادید ولی برنامه آن را نمی‌خواند، مراحل زیر را انجام دهید:

## مرحله ۱: نصب python-dotenv

```bash
pip install python-dotenv
```

یا:

```bash
pip install -r requirements.txt
```

## مرحله ۲: ایجاد فایل .env

1. فایل `env.example` را در ریشه پروژه پیدا کنید
2. آن را کپی کرده و نام آن را به `.env` تغییر دهید:

**در Windows (PowerShell):**
```powershell
Copy-Item env.example .env
```

**در Windows (CMD):**
```cmd
copy env.example .env
```

**در Linux/Mac:**
```bash
cp env.example .env
```

## مرحله ۳: ویرایش فایل .env

فایل `.env` را با یک ویرایشگر متن باز کنید و تنظیمات دیتابیس را اضافه کنید:

```bash
# برای استفاده از Supabase
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
```

یا:

```bash
# برای استفاده از متغیرهای جداگانه
DB_TYPE=postgresql
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=db.your-project-ref.supabase.co
DB_PORT=5432
DB_NAME=postgres
```

## مرحله ۴: Restart سرور

**مهم**: بعد از تغییر فایل `.env`، حتماً سرور را restart کنید:

1. سرور را متوقف کنید (Ctrl+C)
2. دوباره اجرا کنید:

```bash
cd backend
uvicorn main:app --reload
```

## بررسی اینکه فایل .env خوانده می‌شود

هنگام راه‌اندازی سرور، باید پیام زیر را ببینید:

```
Using database from DATABASE_URL: postgresql://***@db.xxx.supabase.co:5432/postgres
```

یا:

```
Using PostgreSQL database: db.xxx.supabase.co:5432/postgres
```

اگر این پیام را نمی‌بینید و به جای آن:

```
Using SQLite database (default): ...
```

یعنی فایل `.env` خوانده نشده است.

## عیب‌یابی

### مشکل ۱: فایل .env در مسیر اشتباه است

فایل `.env` باید در **ریشه پروژه** باشد (همان جایی که `env.example` است):

```
Youtube-DLP/
├── .env          ← اینجا
├── env.example
├── backend/
├── frontend/
└── requirements.txt
```

### مشکل ۲: نام فایل اشتباه است

نام فایل باید دقیقاً `.env` باشد (نه `env` یا `.env.txt`)

**در Windows:**
- اگر فایل را در Notepad ایجاد می‌کنید، هنگام Save As:
  - File name: `.env`
  - Save as type: `All Files (*.*)`

### مشکل ۳: فایل .env در .gitignore است

این طبیعی است و باید باشد. فایل `.env` نباید commit شود.

### مشکل ۴: سرور restart نشده

بعد از تغییر `.env`، حتماً سرور را restart کنید.

### مشکل ۵: python-dotenv نصب نشده

```bash
pip install python-dotenv
```

## تست سریع

برای تست اینکه فایل `.env` خوانده می‌شود:

```python
# در Python
from dotenv import load_dotenv
import os

load_dotenv()
print(os.getenv("DATABASE_URL"))
```

اگر `None` چاپ شد، یعنی فایل `.env` خوانده نشده یا متغیر تنظیم نشده است.

## نکات مهم

1. **هرگز فایل `.env` را commit نکنید** - این فایل در `.gitignore` است
2. **از `env.example` به عنوان نمونه استفاده کنید**
3. **بعد از تغییر `.env`، حتماً سرور را restart کنید**
4. **مقادیر حساس (مثل رمز عبور) را در `.env` نگه دارید، نه در کد**

