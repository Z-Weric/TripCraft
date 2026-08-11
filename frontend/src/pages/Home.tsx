import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Alert, Tag, Button } from "antd";
import { CheckCircle2, XCircle, Sparkles, Clock, MapPin, Brain, ShieldCheck, Share2, Moon, Sun, FileText, UtensilsCrossed, Users } from "lucide-react";
import SearchBar from "../components/SearchBar";
import PostcardFlipCard from "../components/PostcardFlipCard";
import MapView from "../components/MapView";
import CostChart from "../components/CostChart";
import FeedbackBar from "../components/FeedbackBar";
import TravelPet from "../components/TravelPet";
import ShareModal from "../components/ShareModal";
import WeatherCard from "../components/WeatherCard";
import PackingList from "../components/PackingList";
import Community from "./Community";
import FoodPlaza from "./FoodPlaza";
import { useTripStore, getCurrentTripId } from "../stores/itineraryStore";
import { useTheme } from "../hooks/useTheme";
import { useUserStore } from "../stores/userStore";

const TABS = [
  { key: "home", label: "首页", icon: MapPin },
  { key: "food", label: "美食广场", icon: UtensilsCrossed },
  { key: "community", label: "旅游社区", icon: Users },
];

export default function Home() {
  const navigate = useNavigate();
  const { loading, itinerary, verification, error, lastRequest, generate, regenerate, progressStage, progressMessage, editDayItems } = useTripStore();
  const { theme, toggle: toggleTheme } = useTheme();
  const { isLoggedIn, user, fetchMe, logout } = useUserStore();
  const [shareOpen, setShareOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("home");

  useEffect(() => { fetchMe(); }, []);

  return (
    <div className="min-h-screen bg-transparent flex flex-col">
      {/* 顶栏 + Tab 滑块 */}
      <header className="sticky top-0 z-50 bg-background-secondary border-b border-border-light shadow-sm">
        <div className="max-w-[888px] mx-auto px-4 h-16 flex items-center justify-between gap-4">
          {/* Logo */}
          <span className="text-2xl font-black font-display tracking-tight text-foreground shrink-0">Trip<span className="text-primary font-bold">Craft</span></span>

          {/* Tab 滑块 — 复古贴纸风格 */}
          <div className="flex-1 flex justify-center">
            <div className="flex items-center bg-background-tertiary border-2 border-border-dark p-1.5 rounded-full gap-1 shadow-sm">
              {TABS.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.key;
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`flex items-center gap-1.5 px-3 sm:px-5 py-2 text-xs font-mono font-bold uppercase tracking-wider rounded-full transition-all duration-300 ${
                      isActive
                        ? "bg-primary text-white border-2 border-border-dark shadow-sm translate-x-[-1px] translate-y-[-1px]"
                        : "text-foreground-tertiary hover:text-primary hover:bg-background-secondary border-2 border-transparent"
                    }`}
                    style={isActive ? { transition: "all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)" } : {}}
                  >
                    <Icon className={`w-3.5 h-3.5 transition-transform duration-500 ${isActive ? "scale-110 rotate-6" : "scale-100"}`} />
                    <span className="hidden sm:inline">{tab.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 右侧操作 */}
          <div className="flex items-center gap-2 shrink-0">
            <Link to="/history" className="flex items-center gap-1 text-xs text-foreground-tertiary hover:text-primary transition-colors font-mono px-2 py-1">
              <Clock className="w-3.5 h-3.5" /><span className="hidden md:inline">历史</span>
            </Link>
            <button onClick={toggleTheme} className="text-xs text-foreground-tertiary hover:text-primary transition-colors font-mono p-1" aria-label="切换主题">
              {theme === "dark" ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
            </button>
            {isLoggedIn && user ? (
              <div className="flex items-center gap-2">
                <Link to="/profile" className="flex items-center gap-1.5 text-xs font-mono text-foreground hover:text-primary transition-colors">
                  <span className="w-6 h-6 rounded-full bg-primary text-white text-[10px] font-bold flex items-center justify-center">
                    {user.nickname?.[0]?.toUpperCase() || "U"}
                  </span>
                  <span className="hidden sm:inline">{user.nickname}</span>
                </Link>
                <button onClick={() => { logout(); navigate("/"); }} className="text-[10px] text-foreground-tertiary hover:text-error font-mono">退出</button>
              </div>
            ) : (
              <Link to="/login" className="text-xs font-mono font-bold text-primary border border-primary px-3 py-1 rounded-sm hover:bg-primary hover:text-white transition-all">
                登录
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* 滑动内容区 */}
      <div className="flex-1">
        {activeTab === "home" && (
          <div className="max-w-[888px] mx-auto px-6 py-10">
              {/* 主标题 */}
              <section className="text-center mb-10">
                <h1 className="text-4xl md:text-5xl font-black font-display tracking-tight leading-none text-foreground mb-3 uppercase">Trip<span className="text-primary">Craft</span> AI 行程</h1>
                <p className="text-sm font-mono text-foreground-secondary tracking-widest uppercase">◇ 复古明信片式的旅行手册生成系统 ◇</p>
              </section>

              {/* 搜索栏 */}
              <section className="mb-10"><SearchBar onGenerate={generate} loading={loading} /></section>

              {/* 加载中 */}
              {loading && (
                <section className="py-16 text-center">
                  <div className="inline-block relative mb-4">
                    <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent" />
                    <Sparkles className="absolute -top-1 -right-1 w-5 h-5 text-primary-light animate-pulse" />
                  </div>
                  <div className="flex items-center justify-center gap-6 mb-4">
                    {[{ key: "rag", label: "景点检索", icon: MapPin }, { key: "llm", label: "AI 规划", icon: Brain }, { key: "verifying", label: "行程验证", icon: ShieldCheck }].map((stage) => {
                      const isActive = progressStage.startsWith(stage.key);
                      const Icon = stage.icon;
                      return (
                        <div key={stage.key} className={`flex items-center gap-1.5 text-xs font-mono font-bold uppercase tracking-wider transition-all ${isActive ? "text-primary scale-110" : "text-foreground-tertiary opacity-50"}`}>
                          <Icon className={`w-3.5 h-3.5 ${isActive ? "animate-pulse" : ""}`} />{stage.label}
                        </div>
                      );
                    })}
                  </div>
                  <p className="text-sm font-display italic text-foreground-secondary font-semibold">{progressMessage || "正在生成..."}</p>
                  <div className="max-w-xs mx-auto mt-4 h-1 bg-background-tertiary rounded-full overflow-hidden">
                    <div className="h-full bg-primary rounded-full transition-all duration-500" style={{ width: progressStage === "rag_retrieval" ? "20%" : progressStage === "rag_done" ? "30%" : progressStage === "llm_generating" ? "50%" : progressStage === "llm_done" ? "75%" : progressStage === "verifying" ? "90%" : "100%" }} />
                  </div>
                </section>
              )}

              {/* 错误 */}
              {error && !loading && <Alert message="无法生成攻略" description={error} type="warning" showIcon className="mb-8 rounded-sm" />}

              {/* 结果 */}
              {itinerary && !loading && (
                <div className="space-y-10">
                  {verification && (
                    <div className="flex flex-wrap gap-3 items-center justify-center p-3 bg-background-tertiary border border-border-light rounded-sm animate-fade-in-up" style={{ animationDelay: "0ms" }}>
                      <span className="text-xs text-foreground-tertiary font-mono uppercase tracking-wider mr-2">系统验证:</span>
                      <Tag icon={verification.spots_valid ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />} color={verification.spots_valid ? "success" : "error"} className="text-xs py-1 px-2.5">景点真实性 ({verification.spots_verified}/{verification.spots_total})</Tag>
                      <Tag icon={verification.budget_valid ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />} color={verification.budget_valid ? "success" : "error"} className="text-xs py-1 px-2.5">预算 {verification.budget_valid ? "合规" : "超支"}</Tag>
                      <Tag icon={verification.route_valid ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />} color={verification.route_valid ? "success" : "error"} className="text-xs py-1 px-2.5">路线 {verification.route_valid ? "合理" : "需调优"}</Tag>
                    </div>
                  )}

                  <section className="animate-fade-in-up" style={{ animationDelay: "100ms" }}><PostcardFlipCard itinerary={itinerary} userName="临心" workNo="549395" onEditDayItems={editDayItems} /></section>

                  <section className="animate-fade-in-up mt-8" style={{ animationDelay: "200ms" }}>
                    <h2 className="text-xl font-bold font-display text-foreground uppercase tracking-wider mb-4 border-l-4 border-primary pl-3">旅行轨迹地图</h2>
                    <MapView itinerary={itinerary} />
                  </section>

                  <section className="animate-fade-in-up" style={{ animationDelay: "300ms" }}>
                    <h2 className="text-xl font-bold font-display text-foreground uppercase tracking-wider mb-4 border-l-4 border-primary pl-3">出行天气预报</h2>
                    <WeatherCard city={lastRequest?.destination || ""} days={lastRequest?.days || 3} />
                  </section>

                  <section className="animate-fade-in-up" style={{ animationDelay: "400ms" }}>
                    <h2 className="text-xl font-bold font-display text-foreground uppercase tracking-wider mb-4 border-l-4 border-primary pl-3">行李打包清单</h2>
                    <PackingList city={lastRequest?.destination || ""} days={lastRequest?.days || 3} preferences={lastRequest?.preferences || []} />
                  </section>

                  <section className="animate-fade-in-up" style={{ animationDelay: "500ms" }}>
                    <h2 className="text-xl font-bold font-display text-foreground uppercase tracking-wider mb-4 border-l-4 border-primary pl-3">预计花费分析</h2>
                    <CostChart itinerary={itinerary} budget={lastRequest?.budget || 2000} />
                  </section>

                  <section>
                    <div className="flex justify-center gap-3 mb-4 no-print">
                      <Button icon={<FileText className="w-4 h-4 inline mr-1" />}
                        onClick={() => { if (itinerary) { sessionStorage.setItem("article-itinerary", JSON.stringify(itinerary)); navigate("/article/edit"); } }}
                        className="h-10 bg-primary border-primary text-white hover:bg-primary-dark rounded-sm font-mono font-bold">
                        生成攻略
                      </Button>
                      <Button icon={<Share2 className="w-4 h-4 inline mr-1" />} onClick={() => setShareOpen(true)}
                        className="h-10 border-border text-foreground-secondary hover:border-primary hover:text-primary rounded-sm font-mono font-bold">
                        分享行程
                      </Button>
                    </div>
                    <FeedbackBar destination={lastRequest?.destination || ""} days={lastRequest?.days || 3} budget={lastRequest?.budget || 2000} preferences={lastRequest?.preferences || []} onRegenerate={regenerate} />
                  </section>
                </div>
              )}

              {/* 空状态 */}
              {!itinerary && !loading && !error && (
                <section className="mt-12 relative overflow-hidden border border-dashed border-border rounded-sm min-h-[420px]">
                  <img src="/travel-hero.png" alt="旅行者" className="absolute inset-0 w-full h-full object-cover object-center" />
                  <div className="absolute inset-0 bg-gradient-to-t from-background/90 via-background/50 to-transparent" />
                  <div className="relative max-w-md mx-auto py-20 px-6 text-center space-y-4 flex flex-col items-center justify-center min-h-[420px]">
                    <h3 className="text-lg font-bold font-display text-foreground italic">"人生是一场明信片，风景总在寄出的瞬间"</h3>
                    <p className="text-xs text-foreground-secondary leading-relaxed font-mono">选择城市、天数和预算，行程微调模块会自动核对高德 LBS 真实经纬度与门票花费，为你排印一份高质感的行程明信片。</p>
                  </div>
                </section>
              )}
            </div>
        )}

        {/* 美食广场 */}
        {activeTab === "food" && <FoodPlaza embedded />}

        {/* 旅游社区 */}
        {activeTab === "community" && <Community embedded />}
      </div>

      {/* 页脚 */}
      <footer className="border-t border-border-light bg-background-tertiary py-6 text-center text-xs text-foreground-tertiary font-mono tracking-wider">
        <div className="max-w-[888px] mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <div>TRIPCRAFT &copy; 2026. ALL RIGHTS RESERVED.</div>
          <div className="flex gap-4"><a href="https://github.com/Z-Weric/TripCraft" target="_blank" rel="noreferrer" className="hover:text-primary hover:underline">GITHUB</a><span>·</span><span>POSTCARD DESIGN SYSTEM</span></div>
        </div>
      </footer>

      {/* 分享弹窗 */}
      <ShareModal open={shareOpen} tripId={getCurrentTripId()} onClose={() => setShareOpen(false)} />

      {/* 旅行桌宠 */}
      <TravelPet />
    </div>
  );
}