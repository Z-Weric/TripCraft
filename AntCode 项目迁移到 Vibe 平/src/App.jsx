import React, { useEffect, useState } from 'react';
import { Routes, Route, Link, NavLink } from 'react-router-dom';
import vibeSdk from "@alipay/weavefox-vibe-web";
import Home from '@/pages/Home/index.jsx';
import History from '@/pages/History/index.jsx';
import Detail from '@/pages/Detail/index.jsx';
import About from '@/pages/About/index.jsx';

const App = () => {
  const [userInfo, setUserInfo] = useState(null);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const res = await vibeSdk.getUserInfo();
        if (res?.success && res?.data?.userInfo) {
          setUserInfo(res.data.userInfo);
        }
      } catch (err) {
        console.error('Failed to get user info', err);
      }
    };
    fetchUser();
  }, []);

  return (
    <div className="min-h-screen bg-transparent text-foreground flex flex-col selection:bg-primary-light selection:text-foreground">
      {/* 顶栏 Layout：在 Routes 外部，不使用 router hooks，仅用 Link / NavLink 进行安全导航 */}
      <header className="sticky top-0 z-50 bg-background-secondary border-b border-border-light shadow-sm">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between gap-6">
          
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <span className="text-2xl font-black font-display tracking-tight text-foreground transition-colors group-hover:text-primary">
              Trip<span className="text-primary font-bold">Craft</span>
            </span>
            <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] uppercase font-bold tracking-widest border border-primary text-primary rounded-[2px]">
              Postcard v1.0
            </span>
          </Link>

          {/* 导航链接 */}
          <nav className="flex items-center gap-6 md:gap-8">
            <NavLink 
              to="/" 
              className={({ isActive }) => 
                `text-sm font-semibold tracking-wide border-b-2 py-1 transition-all ${
                  isActive ? 'border-primary text-primary font-bold' : 'border-transparent text-foreground-secondary hover:text-primary'
                }`
              }
            >
              主页
            </NavLink>
            <NavLink 
              to="/history" 
              className={({ isActive }) => 
                `text-sm font-semibold tracking-wide border-b-2 py-1 transition-all ${
                  isActive ? 'border-primary text-primary font-bold' : 'border-transparent text-foreground-secondary hover:text-primary'
                }`
              }
            >
              我的攻略
            </NavLink>
            <NavLink 
              to="/about" 
              className={({ isActive }) => 
                `text-sm font-semibold tracking-wide border-b-2 py-1 transition-all ${
                  isActive ? 'border-primary text-primary font-bold' : 'border-transparent text-foreground-secondary hover:text-primary'
                }`
              }
            >
              关于
            </NavLink>
          </nav>

          {/* 当前登录用户信息 (由 Vibe 平台注入) */}
          <div className="flex items-center gap-3">
            {userInfo ? (
              <div className="flex items-center gap-2">
                <div className="hidden md:flex flex-col text-right">
                  <span className="text-sm font-semibold leading-tight text-foreground">
                    {userInfo.nickName || userInfo.name || '旅行者'}
                  </span>
                  <span className="text-[10px] text-foreground-tertiary">
                    {userInfo.dep?.split('/').pop() || '未设定部门'}
                  </span>
                </div>
                <img
                  src={userInfo.avatarUrl || `https://work.alibaba-inc.com/photo/${userInfo.workNo}.200x200.jpg` || 'https://mdn.alipayobjects.com/fecodex_image/afts/img/JVKRQaNDtAIAAAAAgBAAAAgAejH3AQBr/original'}
                  alt="avatar"
                  className="w-9 h-9 rounded-full border border-border-dark object-cover"
                  onError={(e) => {
                    e.target.src = 'https://mdn.alipayobjects.com/fecodex_image/afts/img/JVKRQaNDtAIAAAAAgBAAAAgAejH3AQBr/original';
                  }}
                />
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-background-tertiary animate-pulse border border-border" />
              </div>
            )}
          </div>

        </div>
      </header>

      {/* 页面区域 */}
      <main className="flex-1 flex flex-col">
        <Routes>
          <Route path="/" element={<Home />} title="首页" />
          <Route path="/history" element={<History />} title="我的历史攻略" />
          <Route path="/detail/:id" element={<Detail />} title="攻略详情" />
          <Route path="/about" element={<About />} title="关于" />
        </Routes>
      </main>

      {/* 印刷级极简页脚 */}
      <footer className="border-t border-border-light bg-background-tertiary py-8 text-center text-xs text-foreground-tertiary font-mono tracking-wider">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <div>TRIPCRAFT &copy; 2026. ALL RIGHTS RESERVED.</div>
          <div className="flex gap-4">
            <a href="https://code.alipay.com/jiaye.zjy/TripGraft.git" target="_blank" rel="noreferrer" className="hover:text-primary hover:underline transition-colors">ANTCODE REPO</a>
            <span>·</span>
            <span>VIBE FRAMEWORK MIGRATION</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;