# راهنمای سریع: استفاده از Supabase Data API

## ✅ بعد از آپدیت فایل .env

### 1. بررسی تنظیمات

مطمئن شوید که در فایل `.env` این تنظیمات را دارید:

```bash
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
```

**نکته**: 
- `[YOUR-PROJECT-REF]` را با Project Reference خود جایگزین کنید
- `your_anon_key_here` را با anon key خود جایگزین کنید

### 2. نصب وابستگی‌ها (اگر نصب نشده)

```bash
pip install supabase
```

یا:

```bash
pip install -r requirements.txt
```

### 3. ایجاد جداول در Supabase

در پنل Supabase، به **SQL Editor** بروید و این SQL را اجرا کنید:

```sql
-- ایجاد جدول users (برای احراز هویت)
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  phone_number TEXT UNIQUE NOT NULL,
  first_name TEXT,
  last_name TEXT,
  email TEXT,
  password_hash TEXT,
  is_active INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_phone_number ON users(phone_number);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);

-- ایجاد جدول file_metadata
CREATE TABLE IF NOT EXISTS file_metadata (
  id TEXT PRIMARY KEY,
  s3_url TEXT,
  s3_key TEXT,
  job_id TEXT,
  metadata JSONB,
  video_width INTEGER,
  video_height INTEGER,
  thumbnail_url TEXT,
  thumbnail_key TEXT,
  playlist_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ایجاد جدول playlists
CREATE TABLE IF NOT EXISTS playlists (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  publish_status TEXT DEFAULT 'private',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ایجاد ایندکس‌ها برای عملکرد بهتر
CREATE INDEX IF NOT EXISTS idx_file_metadata_created_at ON file_metadata(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_file_metadata_playlist_id ON file_metadata(playlist_id);
CREATE INDEX IF NOT EXISTS idx_playlists_created_at ON playlists(created_at DESC);
```

### 4. Restart سرور

**مهم**: بعد از تغییر `.env`، حتماً سرور را restart کنید:

```bash
# اگر سرور در حال اجرا است، آن را متوقف کنید (Ctrl+C)
# سپس دوباره اجرا کنید:
cd backend
uvicorn main:app --reload
```

### 5. بررسی موفقیت

هنگام راه‌اندازی سرور، باید این پیام‌ها را ببینید:

```
Supabase client initialized: https://xxx.supabase.co
Using Supabase Data API for metadata storage
Using Supabase Data API for playlist storage
Database initialized successfully.
```

اگر این پیام‌ها را نمی‌بینید:
- بررسی کنید که فایل `.env` در ریشه پروژه است
- بررسی کنید که `SUPABASE_URL` و `SUPABASE_ANON_KEY` درست تنظیم شده‌اند
- بررسی کنید که `supabase` نصب شده است: `pip install supabase`

## 🔍 عیب‌یابی سریع

### مشکل: "Supabase client not initialized"

**راه‌حل:**
1. بررسی کنید که فایل `.env` در ریشه پروژه است (همان جایی که `env.example` است)
2. بررسی کنید که خطوط زیر در `.env` هستند و comment نشده‌اند:
   ```bash
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_ANON_KEY=xxx
   ```
3. سرور را restart کنید

### مشکل: "relation does not exist"

**راه‌حل:**
- جداول را در Supabase ایجاد کنید (مرحله ۳ بالا)
- نام جداول باید دقیقاً `file_metadata` و `playlists` باشد

### مشکل: "permission denied"

**راه‌حل:**
- اگر از `SUPABASE_ANON_KEY` استفاده می‌کنید، RLS را غیرفعال کنید یا policy اضافه کنید
- یا از `SUPABASE_KEY` (service_role) استفاده کنید (فقط برای development)

## 📝 مثال کامل فایل .env

```bash
# Supabase Data API
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTYzODk2NzIwMCwiZXhwIjoxOTU0NTQzMjAwfQ.xxx

# S3 Configuration (اگر نیاز دارید)
# S3_BUCKET=your-bucket
# AWS_ACCESS_KEY_ID=your-key
# AWS_SECRET_ACCESS_KEY=your-secret
```

## 🎯 خلاصه مراحل

1. ✅ فایل `.env` را آپدیت کردید
2. ⬜ `pip install supabase` (اگر نصب نشده)
3. ⬜ جداول را در Supabase ایجاد کنید
4. ⬜ سرور را restart کنید
5. ⬜ پیام‌های موفقیت را بررسی کنید

## 📚 منابع بیشتر

- [راهنمای کامل Supabase Data API](SUPABASE_DATA_API_SETUP.md)
- [راهنمای عمومی دیتابیس](backend/DATABASE_SETUP.md)

