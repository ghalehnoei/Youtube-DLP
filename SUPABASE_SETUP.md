# راه‌اندازی Supabase برای این پروژه

این راهنما به شما کمک می‌کند تا Supabase را برای این پروژه راه‌اندازی کنید.

> **نکته**: اگر می‌خواهید از SQLite استفاده کنید (پیش‌فرض)، نیازی به این راهنما نیست. فقط سرور را اجرا کنید و به صورت خودکار از SQLite استفاده می‌شود. برای اطلاعات بیشتر، [راهنمای انتخاب دیتابیس](backend/DATABASE_SELECTION.md) را ببینید.

## مرحله ۱: ایجاد پروژه در Supabase

1. به [supabase.com](https://supabase.com) بروید
2. روی **Start your project** کلیک کنید
3. با GitHub، Google یا ایمیل ثبت‌نام کنید
4. یک پروژه جدید ایجاد کنید:
   - **Name**: نام پروژه (مثلاً: youtube-dlp-db)
   - **Database Password**: یک رمز عبور قوی انتخاب کنید (این را یادداشت کنید!)
   - **Region**: نزدیک‌ترین منطقه را انتخاب کنید
5. روی **Create new project** کلیک کنید
6. منتظر بمانید تا دیتابیس آماده شود (۲-۳ دقیقه)

## مرحله ۲: دریافت اطلاعات اتصال

1. در پنل Supabase، به **Settings** (⚙️) > **Database** بروید
2. در بخش **Connection string**، گزینه **URI** را انتخاب کنید
3. Connection string را کپی کنید

### دو نوع Connection String:

#### ۱. Connection Pooling (توصیه می‌شود برای production)
```
postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```
- پورت: **6543**
- مناسب برای اپلیکیشن‌های production
- مدیریت بهتر اتصالات

#### ۲. Direct Connection (برای development)
```
postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```
- پورت: **5432**
- مناسب برای development و migration

## مرحله ۳: تنظیم فایل .env

1. در ریشه پروژه، فایل `.env` را ایجاد کنید (اگر وجود ندارد)
2. یکی از روش‌های زیر را انتخاب کنید:

### روش ۱: استفاده از DATABASE_URL (توصیه می‌شود)

```bash
# در فایل .env
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
```

**مثال واقعی:**
```bash
DATABASE_URL=postgresql://postgres:MySecurePassword123@db.abcdefghijklmnop.supabase.co:5432/postgres
```

### روش ۲: استفاده از متغیرهای جداگانه

```bash
# در فایل .env
DB_TYPE=postgresql
DB_USER=postgres
DB_PASSWORD=your_supabase_password
DB_HOST=db.your-project-ref.supabase.co
DB_PORT=5432
DB_NAME=postgres
```

**مثال واقعی:**
```bash
DB_TYPE=postgresql
DB_USER=postgres
DB_PASSWORD=MySecurePassword123
DB_HOST=db.abcdefghijklmnop.supabase.co
DB_PORT=5432
DB_NAME=postgres
```

## مرحله ۴: جایگزینی مقادیر

در Connection String که کپی کردید، مقادیر زیر را جایگزین کنید:

- `[YOUR-PASSWORD]` → رمز عبور دیتابیس که هنگام ایجاد پروژه انتخاب کردید
- `[PROJECT-REF]` → Project Reference ID (در Settings > General > Reference ID پیدا می‌شود)
- `[REGION]` → منطقه پروژه (مثلاً: us-east-1)

## مرحله ۵: نصب وابستگی‌ها

```bash
pip install -r requirements.txt
```

این دستور وابستگی‌های زیر را نصب می‌کند:
- `sqlalchemy` - ORM برای دیتابیس
- `psycopg2-binary` - درایور PostgreSQL

## مرحله ۶: Migration داده‌های موجود (اختیاری)

اگر داده‌های موجود در فایل‌های JSON دارید:

```bash
cd backend
python migrate_json_to_db.py
```

این اسکریپت:
- داده‌های `metadata.json` را به جدول `file_metadata` منتقل می‌کند
- داده‌های `playlists.json` را به جدول `playlists` منتقل می‌کند
- از تکرار داده‌ها جلوگیری می‌کند

## مرحله ۷: تست اتصال

سرور را اجرا کنید:

```bash
cd backend
uvicorn main:app --reload
```

اگر پیام زیر را در console دیدید، اتصال موفق بوده است:
```
Database initialized successfully.
Starting application...
```

## بررسی اتصال در Supabase

1. در پنل Supabase، به **Table Editor** بروید
2. باید جداول زیر را ببینید:
   - `file_metadata` - برای ذخیره متادیتای فایل‌ها
   - `playlists` - برای ذخیره پلی‌لیست‌ها

## عیب‌یابی

### خطا: "could not connect to server"
- بررسی کنید که `DATABASE_URL` درست تنظیم شده است
- بررسی کنید که رمز عبور درست است
- بررسی کنید که Project Reference ID درست است
- بررسی کنید که فایروال یا VPN مانع اتصال نمی‌شود

### خطا: "password authentication failed"
- رمز عبور دیتابیس را بررسی کنید
- در Supabase > Settings > Database > Database password را reset کنید

### خطا: "relation does not exist"
- جداول به صورت خودکار ایجاد می‌شوند
- اگر خطا می‌دهد، مطمئن شوید که `init_db()` در startup اجرا می‌شود

### خطا: "module 'psycopg2' not found"
```bash
pip install psycopg2-binary
```

## نکات امنیتی

1. **هرگز فایل `.env` را commit نکنید**
   - فایل `.env` باید در `.gitignore` باشد
   - از `.env.example` برای نمونه استفاده کنید

2. **از Connection Pooling استفاده کنید**
   - برای production، از پورت 6543 استفاده کنید
   - این باعث مدیریت بهتر اتصالات می‌شود

3. **رمز عبور قوی انتخاب کنید**
   - حداقل ۱۲ کاراکتر
   - شامل حروف بزرگ، کوچک، اعداد و کاراکترهای خاص

4. **IP Restrictions (اختیاری)**
   - در Supabase > Settings > Database > Connection Pooling
   - می‌توانید IP های مجاز را محدود کنید

## منابع بیشتر

- [مستندات Supabase](https://supabase.com/docs)
- [راهنمای اتصال به Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Connection Pooling در Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler)

