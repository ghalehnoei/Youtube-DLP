# راه‌اندازی Supabase Data API

این راهنما به شما کمک می‌کند تا از Supabase Data API (REST API) به جای اتصال مستقیم به دیتابیس استفاده کنید.

## مزایای استفاده از Data API

✅ **امنیت بیشتر**: نیازی به باز کردن پورت دیتابیس نیست  
✅ **Row Level Security**: می‌توانید از RLS استفاده کنید  
✅ **ساده‌تر**: فقط نیاز به URL و API Key دارید  
✅ **مقیاس‌پذیر**: مناسب برای production  

## مرحله ۱: دریافت API Keys

1. به پنل Supabase بروید
2. به **Settings** > **API** بروید
3. اطلاعات زیر را کپی کنید:
   - **Project URL**: `https://[YOUR-PROJECT-REF].supabase.co`
   - **anon/public key**: برای دسترسی عمومی (با RLS)
   - **service_role key**: برای دسترسی کامل (بدون RLS) - **مراقب باشید!**

## مرحله ۲: تنظیم فایل .env

فایل `.env` را در ریشه پروژه ایجاد/ویرایش کنید:

```bash
# Supabase Data API Configuration
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
```

**یا برای دسترسی کامل (توصیه نمی‌شود برای production):**

```bash
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_KEY=your_service_role_key_here
```

**مثال واقعی:**
```bash
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTYzODk2NzIwMCwiZXhwIjoxOTU0NTQzMjAwfQ.xxx
```

## مرحله ۳: نصب وابستگی‌ها

```bash
pip install -r requirements.txt
```

این دستور `supabase` را نصب می‌کند.

## مرحله ۴: ایجاد جداول در Supabase

در پنل Supabase، به **SQL Editor** بروید و SQL زیر را اجرا کنید:

### جدول users (برای احراز هویت)

```sql
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
```

### جدول file_metadata

```sql
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

-- ایجاد ایندکس برای جستجوی سریع‌تر
CREATE INDEX IF NOT EXISTS idx_file_metadata_created_at ON file_metadata(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_file_metadata_playlist_id ON file_metadata(playlist_id);
```

### جدول playlists

```sql
CREATE TABLE IF NOT EXISTS playlists (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  publish_status TEXT DEFAULT 'private',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ایجاد ایندکس
CREATE INDEX IF NOT EXISTS idx_playlists_created_at ON playlists(created_at DESC);
```

## مرحله ۵: تنظیم Row Level Security (اختیاری)

اگر از `SUPABASE_ANON_KEY` استفاده می‌کنید، باید RLS را تنظیم کنید:

```sql
-- برای file_metadata
ALTER TABLE file_metadata ENABLE ROW LEVEL SECURITY;

-- اجازه خواندن و نوشتن برای همه (برای شروع)
CREATE POLICY "Allow all operations" ON file_metadata
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- برای playlists
ALTER TABLE playlists ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations" ON playlists
  FOR ALL
  USING (true)
  WITH CHECK (true);
```

**نکته**: برای production، باید RLS را دقیق‌تر تنظیم کنید.

## مرحله ۶: تست اتصال

سرور را اجرا کنید:

```bash
cd backend
uvicorn main:app --reload
```

اگر پیام زیر را دیدید، اتصال موفق بوده است:

```
Supabase client initialized: https://xxx.supabase.co
Using Supabase Data API for metadata storage
Using Supabase Data API for playlist storage
Database initialized successfully.
```

## عیب‌یابی

### خطا: "Supabase client not initialized"

- بررسی کنید که `SUPABASE_URL` و `SUPABASE_ANON_KEY` (یا `SUPABASE_KEY`) در `.env` تنظیم شده‌اند
- بررسی کنید که فایل `.env` در ریشه پروژه است
- سرور را restart کنید

### خطا: "relation does not exist"

- جداول را در Supabase ایجاد کنید (مرحله ۴)
- نام جداول باید دقیقاً `file_metadata` و `playlists` باشد

### خطا: "permission denied"

- اگر از `SUPABASE_ANON_KEY` استفاده می‌کنید، RLS را تنظیم کنید (مرحله ۵)
- یا از `SUPABASE_KEY` (service_role) استفاده کنید (برای development)

### خطا: "module 'supabase' not found"

```bash
pip install supabase
```

## مقایسه با اتصال مستقیم

| ویژگی | Data API | Direct Connection |
|-------|----------|-------------------|
| امنیت | ✅ بهتر (RLS) | ⚠️ نیاز به فایروال |
| سادگی | ✅ فقط URL + Key | ⚠️ نیاز به Connection String |
| عملکرد | ⚠️ کمی کندتر | ✅ سریع‌تر |
| مناسب برای | Production | Development |

## نکات مهم

1. **هرگز `SUPABASE_KEY` (service_role) را در frontend استفاده نکنید**
2. **از `SUPABASE_ANON_KEY` با RLS برای production استفاده کنید**
3. **فایل `.env` را commit نکنید**
4. **بعد از تغییر `.env`، سرور را restart کنید**

## منابع بیشتر

- [مستندات Supabase Data API](https://supabase.com/docs/reference/javascript/introduction)
- [Row Level Security در Supabase](https://supabase.com/docs/guides/auth/row-level-security)

