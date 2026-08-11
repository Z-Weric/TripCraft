import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Spin, Empty, message } from "antd";
import { Star, MapPin, DollarSign } from "lucide-react";
import { API_BASE } from "../services/config";
import PoiDetailModal from "../components/PoiDetailModal";

interface FoodItem {
  id: number; name: string; city: string; category: string;
  cost: number; address: string; note: string; rating: number;
  lat: number; lng: number;
}

const CITIES = ["杭州", "成都", "西安", "厦门", "苏州", "南京", "重庆", "长沙", "青岛", "大理"];

export default function FoodPlaza({ embedded = false }: { embedded?: boolean }) {
  const [city, setCity] = useState("杭州");
  const [foods, setFoods] = useState<FoodItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [poiDetailId, setPoiDetailId] = useState<number | null>(null);
  const [poiDetailOpen, setPoiDetailOpen] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/api/foods?city=${encodeURIComponent(city)}`)
      .then(res => res.json())
      .then(data => setFoods(data))
      .catch(() => message.error("加载失败"))
      .finally(() => setLoading(false));
  }, [city]);

  const content = (
    <>
      <h1 className="text-2xl font-black font-display tracking-tight text-foreground uppercase mb-2">🍜 美食广场</h1>
      <p className="text-sm text-foreground-tertiary font-mono mb-6">各城市特色美食推荐</p>

      <div className="flex flex-wrap gap-2 mb-6">
        {CITIES.map((c) => (
          <button
            key={c}
            onClick={() => setCity(c)}
            className={`text-xs px-3 py-1.5 border rounded-full transition-all font-mono font-bold ${city === c ? "bg-primary text-white border-primary" : "border-border text-foreground-secondary hover:border-primary hover:text-primary"}`}
          >
            {c}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Spin /></div>
      ) : foods.length === 0 ? (
        <Empty description={<span className="text-sm text-foreground-tertiary italic">暂无美食数据</span>} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {foods.map((food) => (
            <div
              key={food.id}
              onClick={() => { setPoiDetailId(food.id); setPoiDetailOpen(true); }}
              className="bg-background-secondary border border-border rounded-sm p-4 hover:border-primary transition-all cursor-pointer group"
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-base font-bold font-display text-foreground group-hover:text-primary transition-colors">{food.name}</h3>
                <div className="flex items-center gap-0.5 text-xs font-mono text-primary">
                  <Star className="w-3 h-3 fill-current" />{food.rating}
                </div>
              </div>
              {food.note && <p className="text-xs text-foreground-tertiary italic mb-2 line-clamp-2">{food.note}</p>}
              <div className="flex items-center gap-3 text-[10px] text-foreground-tertiary font-mono">
                <span className="flex items-center gap-0.5"><MapPin className="w-3 h-3" />{food.address || city}</span>
                <span className="flex items-center gap-0.5"><DollarSign className="w-3 h-3" />{food.cost === 0 ? "免费" : `¥${food.cost}`}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      <PoiDetailModal poiId={poiDetailId} open={poiDetailOpen} onClose={() => setPoiDetailOpen(false)} />
    </>
  );

  if (embedded) {
    return <div className="max-w-[888px] mx-auto px-6 py-10">{content}</div>;
  }

  return (
    <div className="min-h-screen bg-transparent flex flex-col">
      <header className="sticky top-0 z-50 bg-background-secondary border-b border-border-light shadow-sm">
        <div className="max-w-[888px] mx-auto px-6 h-16 flex items-center justify-between gap-6">
          <Link to="/home" className="text-2xl font-black font-display tracking-tight text-foreground hover:text-primary transition-colors">
            Trip<span className="text-primary font-bold">Craft</span>
          </Link>
          <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] uppercase font-bold tracking-widest border border-primary text-primary rounded-sm">美食广场</span>
        </div>
      </header>

      <div className="max-w-[888px] mx-auto px-6 py-10 flex-1 w-full">
        {content}
      </div>
    </div>
  );
}