import { useState, useCallback } from "react";
import { Alert, Tag } from "antd";
import { CheckCircle2, XCircle, Sparkles } from "lucide-react";
import SearchBar from "./components/SearchBar";
import PostcardFlipCard from "./components/PostcardFlipCard";
import MapView from "./components/MapView";
import CostChart from "./components/CostChart";
import FeedbackBar from "./components/FeedbackBar";
import TravelPet from "./components/TravelPet";
import { generateItinerary, type Itinerary, type Verification, type GenerateRequest } from "./services/api";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [verification, setVerification] = useState<Verification | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastRequest, setLastRequest] = useState<GenerateRequest | null>(null);

  const handleGenerate = useCallback(async (req: GenerateRequest) => {
    setLoading(true); setError(null); setLastRequest(req);
    try {
      const res = await generateItinerary(req);
      if (res.itinerary.error) { setError(res.itinerary.error as string); setItinerary(null); }
      else { setItinerary(res.itinerary); setVerification(res.verification); }
    } catch (e: any) { setError(e?.message || "生成失败，请检查后端服务是否启动"); }
    finally { setLoading(false); }
  }, []);

  return (
    <div className="min-h-screen bg-transparent flex flex-col">
      {/* 顶栏 */}
      <header className="sticky top-0 z-50 bg-background-secondary border-b border-border-light shadow-sm">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between gap-6">
          <span className="text-2xl font-black font-display tracking-tight text-foreground">Trip<span className="text-primary font-bold">Craft</span></span>
          <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] uppercase font-bold tracking-widest border border-primary text-primary rounded-sm">Postcard v2.0</span>
          {itinerary && <span className="text-sm text-foreground-tertiary">{itinerary.days}天{itinerary.destination} · 预算 ¥{lastRequest?.budget}</span>}
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-10 flex-1 w-full">
        {/* 主标题 */}
        <section className="text-center mb-10">
          <h1 className="text-4xl md:text-5xl font-black font-display tracking-tight leading-none text-foreground mb-3 uppercase">Trip<span className="text-primary">Craft</span> AI 行程</h1>
          <p className="text-sm font-mono text-foreground-secondary tracking-widest uppercase">◇ 复古明信片式的旅行手册生成系统 ◇</p>
        </section>

        {/* 搜索栏 */}
        <section className="mb-10"><SearchBar onGenerate={handleGenerate} loading={loading} /></section>

        {/* 加载中 */}
        {loading && (
          <section className="py-20 text-center">
            <div className="inline-block relative">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent mb-4" />
              <Sparkles className="absolute -top-1 -right-1 w-5 h-5 text-primary-light animate-pulse" />
            </div>
            <p className="text-lg font-display italic text-foreground-secondary font-semibold">正在通过微调模型精排最合理的明信片路线...</p>
          </section>
        )}

        {/* 错误 */}
        {error && !loading && <Alert message="无法生成攻略" description={error} type="warning" showIcon className="mb-8 rounded-sm" />}

        {/* 结果 */}
        {itinerary && !loading && (
          <div className="space-y-10">
            {/* 验证徽章 */}
            {verification && (
              <div className="flex flex-wrap gap-3 items-center justify-center p-3 bg-background-tertiary border border-border-light rounded-sm">
                <span className="text-xs text-foreground-tertiary font-mono uppercase tracking-wider mr-2">系统验证:</span>
                <Tag icon={verification.spots_valid ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />} color={verification.spots_valid ? "success" : "error"} className="text-xs py-1 px-2.5">景点真实性 ({verification.spots_verified}/{verification.spots_total})</Tag>
                <Tag icon={verification.budget_valid ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />} color={verification.budget_valid ? "success" : "error"} className="text-xs py-1 px-2.5">预算 {verification.budget_valid ? "合规" : "超支"}</Tag>
                <Tag icon={verification.route_valid ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />} color={verification.route_valid ? "success" : "error"} className="text-xs py-1 px-2.5">路线 {verification.route_valid ? "合理" : "需调优"}</Tag>
              </div>
            )}

            {/* 明信片翻转卡片 */}
            <section><PostcardFlipCard itinerary={itinerary} userName="临心" workNo="549395" /></section>

            {/* 地图 */}
            <section>
              <h2 className="text-xl font-bold font-display text-foreground uppercase tracking-wider mb-4 border-l-4 border-primary pl-3">旅行轨迹地图</h2>
              <MapView itinerary={itinerary} />
            </section>

            {/* 花费 */}
            <section>
              <h2 className="text-xl font-bold font-display text-foreground uppercase tracking-wider mb-4 border-l-4 border-primary pl-3">预计花费分析</h2>
              <CostChart itinerary={itinerary} budget={lastRequest?.budget || 2000} />
            </section>

            {/* 反馈 */}
            <section><FeedbackBar destination={lastRequest?.destination || ""} days={lastRequest?.days || 3} budget={lastRequest?.budget || 2000} preferences={lastRequest?.preferences || []} onRegenerate={() => lastRequest && handleGenerate(lastRequest)} /></section>
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

      {/* 页脚 */}
      <footer className="border-t border-border-light bg-background-tertiary py-8 text-center text-xs text-foreground-tertiary font-mono tracking-wider">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <div>TRIPCRAFT &copy; 2026. ALL RIGHTS RESERVED.</div>
          <div className="flex gap-4"><a href="https://github.com/Z-Weric/TripCraft" target="_blank" rel="noreferrer" className="hover:text-primary hover:underline">GITHUB</a><span>·</span><span>POSTCARD DESIGN SYSTEM</span></div>
        </div>
      </footer>

      {/* 旅行桌宠 */}
      <TravelPet />
    </div>
  );
}