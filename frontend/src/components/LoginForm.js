import React, { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const LoginForm = ({ onLoginSuccess }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isRegister) {
        // Register
        const response = await axios.post(`${API_BASE_URL}/api/auth/register`, {
          phone_number: phoneNumber,
          first_name: firstName,
          last_name: lastName,
          email: email
        });

        if (response.data && response.data.access_token) {
          // Save token to localStorage
          localStorage.setItem('access_token', response.data.access_token);
          localStorage.setItem('user', JSON.stringify(response.data.user));
          onLoginSuccess(response.data.user, response.data.access_token);
        }
      } else {
        // Login
        const response = await axios.post(`${API_BASE_URL}/api/auth/login`, {
          phone_number: phoneNumber,
          password: password || '111111' // Default password
        });

        if (response.data && response.data.access_token) {
          // Save token to localStorage
          localStorage.setItem('access_token', response.data.access_token);
          localStorage.setItem('user', JSON.stringify(response.data.user));
          onLoginSuccess(response.data.user, response.data.access_token);
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'خطا در ورود/ثبت نام');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      backgroundColor: '#f5f5f5',
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '40px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
        width: '100%',
        maxWidth: '400px'
      }}>
        <h2 style={{
          textAlign: 'center',
          marginBottom: '30px',
          color: '#333'
        }}>
          {isRegister ? 'ثبت نام' : 'ورود به سیستم'}
        </h2>

        {error && (
          <div style={{
            backgroundColor: '#fee',
            color: '#c33',
            padding: '12px',
            borderRadius: '4px',
            marginBottom: '20px',
            textAlign: 'center'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '20px' }}>
            <label style={{
              display: 'block',
              marginBottom: '8px',
              color: '#666',
              fontWeight: '500'
            }}>
              شماره موبایل
            </label>
            <input
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="09123456789"
              required
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '16px',
                boxSizing: 'border-box'
              }}
            />
          </div>

          {!isRegister && (
            <div style={{ marginBottom: '20px' }}>
              <label style={{
                display: 'block',
                marginBottom: '8px',
                color: '#666',
                fontWeight: '500'
              }}>
                رمز عبور (پیش‌فرض: 111111)
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="111111"
                style={{
                  width: '100%',
                  padding: '12px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '16px',
                  boxSizing: 'border-box'
                }}
              />
            </div>
          )}

          {isRegister && (
            <>
              <div style={{ marginBottom: '20px' }}>
                <label style={{
                  display: 'block',
                  marginBottom: '8px',
                  color: '#666',
                  fontWeight: '500'
                }}>
                  نام
                </label>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="نام"
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '16px',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{
                  display: 'block',
                  marginBottom: '8px',
                  color: '#666',
                  fontWeight: '500'
                }}>
                  نام خانوادگی
                </label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="نام خانوادگی"
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '16px',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{
                  display: 'block',
                  marginBottom: '8px',
                  color: '#666',
                  fontWeight: '500'
                }}>
                  ایمیل (اختیاری)
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="email@example.com"
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '16px',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
            </>
          )}

          <button
            type="submit"
            disabled={loading || !phoneNumber.trim()}
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: loading ? '#ccc' : '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontSize: '16px',
              fontWeight: 'bold',
              cursor: loading ? 'not-allowed' : 'pointer',
              marginBottom: '15px'
            }}
          >
            {loading ? 'در حال پردازش...' : (isRegister ? 'ثبت نام' : 'ورود')}
          </button>
        </form>

        <div style={{
          textAlign: 'center',
          marginTop: '20px',
          paddingTop: '20px',
          borderTop: '1px solid #eee'
        }}>
          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              setError(null);
              setPassword('');
            }}
            style={{
              background: 'none',
              border: 'none',
              color: '#2196F3',
              cursor: 'pointer',
              textDecoration: 'underline',
              fontSize: '14px'
            }}
          >
            {isRegister ? 'قبلاً ثبت نام کرده‌اید؟ ورود' : 'حساب کاربری ندارید؟ ثبت نام'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;

