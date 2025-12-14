# راه‌اندازی دیتابیس

این پروژه از SQLAlchemy برای ذخیره‌سازی متادیتا استفاده می‌کند و از دیتابیس‌های PostgreSQL، MySQL و SQLite پشتیبانی می‌کند.

## نصب وابستگی‌ها

ابتدا وابستگی‌های جدید را نصب کنید:

```bash
pip install -r requirements.txt
```

## پیکربندی دیتابیس

### روش ۱: استفاده از DATABASE_URL (توصیه می‌شود)

متغیر محیطی `DATABASE_URL` را تنظیم کنید:

```bash
# PostgreSQL (مثال: Supabase, Neon, Railway)
export DATABASE_URL="postgresql://user:password@host:port/database"

# MySQL (مثال: PlanetScale)
export DATABASE_URL="mysql+pymysql://user:password@host:port/database"

# SQLite (محلی)
export DATABASE_URL="sqlite:///./database.sqlite"
```

### روش ۲: استفاده از متغیرهای محیطی جداگانه

```bash
# نوع دیتابیس (postgresql, mysql, sqlite)
export DB_TYPE="postgresql"

# اطلاعات اتصال
export DB_USER="your_username"
export DB_PASSWORD="your_password"
export DB_HOST="your_host"
export DB_PORT="5432"  # برای PostgreSQL
export DB_NAME="youtube_dlp"
```

### مثال‌های سرویس‌های آنلاین

#### Supabase (PostgreSQL) - راه‌اندازی کامل

**مرحله ۱: ایجاد پروژه در Supabase**
1. به [supabase.com](https://supabase.com) بروید و یک حساب کاربری ایجاد کنید
2. یک پروژه جدید ایجاد کنید
3. منتظر بمانید تا دیتابیس آماده شود (چند دقیقه طول می‌کشد)

**مرحله ۲: دریافت اطلاعات اتصال**
1. در پنل Supabase، به **Settings** > **Database** بروید
2. در بخش **Connection string**، گزینه **URI** را انتخاب کنید
3. Connection string را کپی کنید (شکل زیر):
   ```
   postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```
   یا برای اتصال مستقیم:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```

**مرحله ۳: تنظیم در فایل .env**
فایل `.env` را در ریشه پروژه ایجاد کنید و تنظیمات زیر را اضافه کنید:

```bash
# روش ۱: استفاده از DATABASE_URL (توصیه می‌شود)
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres

# روش ۲: استفاده از متغیرهای جداگانه
# DB_TYPE=postgresql
# DB_USER=postgres
# DB_PASSWORD=your_supabase_password
# DB_HOST=db.your-project-ref.supabase.co
# DB_PORT=5432
# DB_NAME=postgres
```

**نکات مهم:**
- `[YOUR-PASSWORD]` را با رمز عبور دیتابیس خود جایگزین کنید (در Settings > Database > Database password)
- `[YOUR-PROJECT-REF]` را با Project Reference خود جایگزین کنید (در Settings > General > Reference ID)
- برای امنیت بیشتر، از Connection Pooling استفاده کنید (پورت 6543 به جای 5432)

**مثال واقعی:**
```bash
DATABASE_URL=postgresql://postgres.abcdefghijklmnop:MySecurePassword123@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**مرحله ۴: نصب وابستگی‌ها**
```bash
pip install -r requirements.txt
```

**مرحله ۵: اجرای Migration**
```bash
cd backend
python migrate_json_to_db.py
```

**مرحله ۶: تست اتصال**
سرور را اجرا کنید:
```bash
cd backend
uvicorn main:app --reload
```

اگر پیام "Database initialized successfully." را دیدید، اتصال موفق بوده است.

#### Neon (PostgreSQL)
```bash
export DATABASE_URL="postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/dbname"
```

#### Railway (PostgreSQL)
```bash
export DATABASE_URL="postgresql://postgres:password@containers-us-west-xxx.railway.app:5432/railway"
```

#### PlanetScale (MySQL)
```bash
export DATABASE_URL="mysql+pymysql://user:password@host.psdb.cloud/database?ssl={"rejectUnauthorized":true}"
```

## Migration (انتقال داده‌های موجود)

اگر داده‌های موجود در فایل‌های JSON دارید، می‌توانید آن‌ها را به دیتابیس منتقل کنید:

```bash
cd backend
python migrate_json_to_db.py
```

این اسکریپت:
- داده‌های `metadata.json` را به جدول `file_metadata` منتقل می‌کند
- داده‌های `playlists.json` را به جدول `playlists` منتقل می‌کند
- از تکرار داده‌ها جلوگیری می‌کند (اگر داده‌ای قبلاً وجود داشته باشد، skip می‌شود)

## استفاده از SQLite (برای توسعه محلی)

اگر می‌خواهید از SQLite استفاده کنید (نیازی به نصب دیتابیس جداگانه نیست):

```bash
# هیچ متغیر محیطی نیاز نیست - به صورت پیش‌فرض از SQLite استفاده می‌کند
# فایل database.sqlite در پوشه backend ایجاد می‌شود
```

## ساختار جداول

### جدول file_metadata
- `id`: شناسه یکتا (String)
- `s3_url`: URL فایل در S3
- `s3_key`: کلید S3
- `job_id`: شناسه کار
- `metadata`: متادیتای JSON
- `video_width`: عرض ویدیو
- `video_height`: ارتفاع ویدیو
- `thumbnail_url`: URL تصویر بندانگشتی
- `thumbnail_key`: کلید تصویر بندانگشتی
- `playlist_id`: شناسه پلی‌لیست
- `created_at`: تاریخ ایجاد

### جدول playlists
- `id`: شناسه یکتا (String)
- `title`: عنوان
- `description`: توضیحات
- `publish_status`: وضعیت انتشار
- `created_at`: تاریخ ایجاد
- `updated_at`: تاریخ به‌روزرسانی

## نکات مهم

1. **پشتیبان‌گیری**: همیشه از دیتابیس خود پشتیبان‌گیری کنید
2. **امنیت**: هرگز اطلاعات اتصال دیتابیس را در کد commit نکنید
3. **Connection Pooling**: SQLAlchemy به صورت خودکار connection pooling را مدیریت می‌کند
4. **Migration**: فقط یک بار migration را اجرا کنید

## عیب‌یابی

اگر خطای اتصال به دیتابیس دریافت کردید:

1. بررسی کنید که `DATABASE_URL` یا متغیرهای محیطی درست تنظیم شده‌اند
2. بررسی کنید که دیتابیس در دسترس است و فایروال اجازه اتصال می‌دهد
3. بررسی کنید که وابستگی‌ها نصب شده‌اند (`psycopg2-binary` برای PostgreSQL، `pymysql` برای MySQL)

