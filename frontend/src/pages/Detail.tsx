import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { Spin, Alert } from "antd";
import { ArrowLeft } from "lucide-react";
import PostcardFlipCard from "../components/PostcardFlipCard";
import MapView from "../components/MapView";
import CostChart from "../components/CostChart";
import { getSharedTrip, type Itinerary } from "../services/api";

export default function Detail() {
  const { token } = useParams<{ token: string }>();
  const [loading, setLoading] = useState(true);
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [budget, setBudget] = useState(2000);

  useEffect(() => {
    if (!token) return;
    getSharedTrip(token)
      .then((data: any) => {
        if (data.error) {
          setError(data.error);
        } else {
          setItinerary(data.itinerary);
          setBudget(data.budget);
        }
      })
      .catch(() => setError("加载失败"))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Spin size="large" />
      </div>
    );
  }

  if (error || !itinerary) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-6">
        <div className="max-w-md w-full">
          <Alert type="warning" message="无法查看行程" description={error || "行程不存在"} showIcon />
          <Link to="/" className="block mt-4 text-center text-xs font-mono text-primary hover:underline">返回首页</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-transparent flex flex-col">
      <header className="sticky top-0 z-50 bg-background-secondary border-b border-border-light shadow-sm">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between gap-6">
          <Link to="/" className="text-2xl font-black font-display tracking-tight text-foreground hover:text-primary transition-colors">
            Trip<span className="text-primary font-bold">Craft</span>
          </Link>
          <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] uppercase font-bold tracking-widest border border-primary text-primary rounded-sm">分享行程</span>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-10 flex-1 w-full">
        <div className="text-center mb-6">
          <p className="text-xs font-mono text-foreground-tertiary tracking-widest uppercase">◇ 分享的旅行明信片 ◇</p>
        </div>

        <div className="space-y-10">
          <section><PostcardFlipCard itinerary={itinerary} userName="旅行者" workNo="000000" /></section>

          <section>
            <h2 className="text-xl font-bold font-display text-foreground uppercase tracking-wider mb-4 border-l-4 border-primary pl-3">旅行轨迹地图</h2>
            <MapView itinerary={itinerary} />
          </section>

          <section>
            <h2 className="text-xl font-bold font-display text-foreground uppercase tracking-wider mb-4 border-l-4 border-primary pl-3">预计花费分析</h2>
            <CostChart itinerary={itinerary} budget={budget} />
          </section>
        </div>
      </div>

      <footer className="border-t border-border-light bg-background-tertiary py-6 text-center text-xs text-foreground-tertiary font-mono tracking-wider">
        <Link to="/" className="hover:text-primary hover:underline flex items-center justify-center gap-1">
          <ArrowLeft className="w-3 h-3" /> 返回 TripCraft 生成你的行程
        </Link>
      </footer>
    </div>
  );
}