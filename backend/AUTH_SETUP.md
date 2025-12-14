# راه‌اندازی سیستم احراز هویت

این پروژه از سیستم احراز هویت با شماره موبایل و رمز عبور استفاده می‌کند.

## ویژگی‌ها

- ✅ ورود با شماره موبایل
- ✅ ثبت نام برای کاربران جدید
- ✅ ذخیره اطلاعات: نام، نام خانوادگی، ایمیل
- ✅ رمز عبور ثابت: `111111` (برای همه کاربران)
- ✅ JWT Token برای احراز هویت
- ✅ محافظت از API endpoints

## ساختار دیتابیس

### جدول users

```sql
CREATE TABLE users (
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

CREATE INDEX idx_users_phone_number ON users(phone_number);
CREATE INDEX idx_users_created_at ON users(created_at DESC);
```

## API Endpoints

### ثبت نام

**POST** `/api/auth/register`

**Request Body:**
```json
{
  "phone_number": "09123456789",
  "first_name": "علی",
  "last_name": "احمدی",
  "email": "ali@example.com"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "phone_number": "09123456789",
    "first_name": "علی",
    "last_name": "احمدی",
    "email": "ali@example.com",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### ورود

**POST** `/api/auth/login`

**Request Body:**
```json
{
  "phone_number": "09123456789",
  "password": "111111"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "phone_number": "09123456789",
    "first_name": "علی",
    "last_name": "احمدی",
    "email": "ali@example.com",
    "is_active": true
  }
}
```

### دریافت اطلاعات کاربر

**GET** `/api/auth/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "uuid",
  "phone_number": "09123456789",
  "first_name": "علی",
  "last_name": "احمدی",
  "email": "ali@example.com",
  "is_active": true
}
```

## استفاده در Frontend

### ذخیره Token

```javascript
// بعد از login/register موفق
localStorage.setItem('access_token', response.data.access_token);
localStorage.setItem('user', JSON.stringify(response.data.user));

// اضافه کردن token به header های axios
axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
```

### استفاده در API Calls

```javascript
// axios به صورت خودکار token را در header اضافه می‌کند
axios.get('/api/files')
  .then(response => {
    // ...
  });
```

## محافظت از Endpoints

برای محافظت از یک endpoint، از `Depends(get_current_user)` استفاده کنید:

```python
@app.get("/api/protected")
async def protected_route(current_user: Dict = Depends(get_current_user)):
    return {"message": f"Hello {current_user['first_name']}"}
```

## تنظیمات

### JWT Secret Key

در فایل `.env`:

```bash
JWT_SECRET_KEY=your-secret-key-change-this-in-production
```

**نکته**: برای production، حتماً یک secret key قوی و تصادفی استفاده کنید.

## امنیت

1. **رمز عبور**: در حال حاضر رمز ثابت `111111` است. برای production باید:
   - رمز عبور را hash کنید
   - از OTP استفاده کنید
   - رمز عبور را از کاربر بگیرید

2. **JWT Secret**: حتماً در production تغییر دهید

3. **HTTPS**: در production از HTTPS استفاده کنید

4. **Token Expiration**: به صورت پیش‌فرض 7 روز است. می‌توانید در `backend/app/auth.py` تغییر دهید.

## عیب‌یابی

### خطا: "User not found"

- کاربر باید ابتدا ثبت نام کند
- شماره موبایل را بررسی کنید

### خطا: "Invalid password"

- رمز عبور باید `111111` باشد

### خطا: "Invalid or expired token"

- Token منقضی شده است
- دوباره login کنید

### خطا: "User account is inactive"

- حساب کاربری غیرفعال است
- با ادمین تماس بگیرید

