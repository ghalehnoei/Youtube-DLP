import React from 'react';
import RTLText from './RTLText';

const MainLayout = ({ children, searchQuery, onSearchChange, onNewDownload, showSidebar = true }) => {
  return (
    <div className="main-layout">
      {/* Header */}
      <header className="aparat-header">
        <div className="header-top">
          <div className="header-left">
            <div className="logo">
              <span className="logo-icon">🎥</span>
              <span className="logo-text">Youtube Downloader</span>
            </div>
            <button className="login-btn">ورود به سیستم</button>
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
              <a href="#" className="nav-link">برای شما</a>
              <a href="#" className="nav-link">پخش زنده</a>
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
            <a href="#" className="sidebar-item active">
              <span className="sidebar-icon">🏠</span>
              <span>خانه</span>
            </a>
            <a href="#" className="sidebar-item">
              <span className="sidebar-icon">📺</span>
              <span>پخش زنده</span>
            </a>
            <a href="#" className="sidebar-item">
              <span className="sidebar-icon">📺</span>
              <span>مرور کانال‌ها</span>
            </a>
            <a href="#" className="sidebar-item">
              <span className="sidebar-icon">⭐</span>
              <span>برای شما</span>
            </a>
          </nav>
          
          <div className="sidebar-section">
            <p className="sidebar-description">
              برای دریافت پیشنهادات شخصی‌سازی شده، کانال‌های مورد علاقه خود را دنبال کنید
            </p>
            <button className="sidebar-login-btn">ورود به سیستم</button>
          </div>
          
          <div className="sidebar-section">
            <h3 className="sidebar-section-title">تنظیمات</h3>
            <div className="settings-item">
              <span>حالت شب</span>
              <label className="toggle-switch">
                <input type="checkbox" />
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

