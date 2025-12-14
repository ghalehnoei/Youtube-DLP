import React from 'react';
import { useDarkMode } from '../contexts/DarkModeContext';

const APP_NAME = process.env.REACT_APP_NAME || 'RAFO VIDEO Downloader';

const MainLayout = ({ children, searchQuery, onSearchChange, onNewDownload, showSidebar = true, showActiveJobs = false, onToggleActiveJobs, user, onLogout, onHome = null }) => {
  const { isDarkMode, toggleDarkMode } = useDarkMode();

  const handleLogoClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (onHome && typeof onHome === 'function') {
      onHome();
    }
  };

  return (
    <div className="main-layout">
      {/* Header */}
      <header className="aparat-header">
        <div className="header-top">
          <div className="header-left">
            <div 
              className="logo" 
              onClick={handleLogoClick}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleLogoClick(e);
                }
              }}
              role="button"
              tabIndex={0}
              style={{ cursor: 'pointer', userSelect: 'none' }}
              title="بازگشت به خانه"
            >
              <span className="logo-icon">🎥</span>
              <span className="logo-text">{APP_NAME}</span>
            </div>
          </div>
          
          <div className="header-center">
            <div className="search-container">
              <input
                type="text"
                placeholder="جستجوی ویدیو..."
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                className="header-search-input"
              />
              <button className="search-btn">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="m21 21-4.35-4.35"/>
                </svg>
              </button>
            </div>
          </div>
          
          <div className="header-right">
            <nav className="header-nav">
              <button type="button" className="nav-link">برای شما</button>
              <button type="button" className="nav-link">پخش زنده</button>
              <button onClick={onNewDownload} className="nav-link new-video-btn">
                ➕ ویدیو جدید
              </button>
            </nav>
          </div>
        </div>
        
        <div className="header-categories">
          <div className="categories-scroll">
            <button className="category-tab">همه</button>
            <button className="category-tab">فیلم</button>
            <button className="category-tab">موسیقی</button>
            <button className="category-tab">آموزشی</button>
            <button className="category-tab">سرگرمی</button>
            <button className="category-tab">کمدی</button>
            <button className="category-tab">اکشن</button>
            <button className="category-tab">دراما</button>
          </div>
        </div>
      </header>

      {/* Main Content with Sidebar */}
      <div className="main-content-wrapper">
        {/* Left Sidebar */}
        {showSidebar && (
        <aside className="sidebar">
          <nav className="sidebar-nav">
            <button 
              type="button" 
              className={`sidebar-item ${!showActiveJobs ? 'active' : ''}`}
              onClick={() => onToggleActiveJobs && onToggleActiveJobs(false)}
            >
              <span className="sidebar-icon">🏠</span>
              <span>خانه</span>
            </button>
            <button 
              type="button" 
              className={`sidebar-item ${showActiveJobs ? 'active' : ''}`}
              onClick={() => onToggleActiveJobs && onToggleActiveJobs(true)}
            >
              <span className="sidebar-icon">⚙️</span>
              <span>کارهای فعال</span>
            </button>
            <button type="button" className="sidebar-item">
              <span className="sidebar-icon">📺</span>
              <span>پخش زنده</span>
            </button>
            <button type="button" className="sidebar-item">
              <span className="sidebar-icon">📺</span>
              <span>مرور کانال‌ها</span>
            </button>
            <button type="button" className="sidebar-item">
              <span className="sidebar-icon">⭐</span>
              <span>برای شما</span>
            </button>
          </nav>
          
          {user ? (
            <div className="sidebar-section">
              <div style={{ 
                padding: '12px', 
                backgroundColor: '#f5f5f5', 
                borderRadius: '8px',
                marginBottom: '12px'
              }}>
                <div style={{ 
                  fontSize: '14px', 
                  fontWeight: '500', 
                  color: '#333',
                  marginBottom: '4px'
                }}>
                  {user.first_name && user.last_name 
                    ? `${user.first_name} ${user.last_name}` 
                    : user.phone_number}
                </div>
                {user.email && (
                  <div style={{ fontSize: '12px', color: '#666' }}>
                    {user.email}
                  </div>
                )}
              </div>
              <button 
                className="sidebar-login-btn" 
                onClick={onLogout}
                style={{ 
                  width: '100%',
                  backgroundColor: '#dc3545',
                  color: 'white',
                  border: 'none',
                  padding: '10px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500'
                }}
              >
                خروج از حساب
              </button>
            </div>
          ) : (
            <div className="sidebar-section">
              <p className="sidebar-description">
                برای دریافت پیشنهادات شخصی‌سازی شده، کانال‌های مورد علاقه خود را دنبال کنید
              </p>
              <button className="sidebar-login-btn">ورود به سیستم</button>
            </div>
          )}
          
          <div className="sidebar-section">
            <h3 className="sidebar-section-title">تنظیمات</h3>
            <div className="settings-item">
              <span>حالت شب</span>
              <label className="toggle-switch">
                <input 
                  type="checkbox" 
                  checked={isDarkMode}
                  onChange={toggleDarkMode}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>
          </div>
        </aside>
        )}

        {/* Main Content Area */}
        <main className="main-content">
          {children}
        </main>
      </div>
    </div>
  );
};

export default MainLayout;

