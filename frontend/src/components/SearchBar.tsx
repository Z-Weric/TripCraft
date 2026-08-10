import { useState, useEffect } from "react";
import { Form, Input, Select, InputNumber, Button, message } from "antd";
import { MapPin, Compass, Star, Heart } from "lucide-react";
import type { GenerateRequest } from "../services/api";
import { API_BASE } from "../services/config";
import axios from "axios";

const { Option } = Select;
const PREFERENCES = ["自然风光", "美食", "历史文化", "购物", "亲子"];
const HOT_CITIES = ["杭州", "成都", "西安", "厦门", "苏州", "南京", "重庆", "长沙", "青岛", "大理"];

/** 权重标签：0=未选, 1=普通, 2=喜欢, 3=强烈推荐 */
const WEIGHT_LABELS: Record<number, string> = { 0: "", 1: "普通", 2: "喜欢", 3: "强烈推荐" };

interface SearchBarProps {
  onGenerate: (req: GenerateRequest) => void;
  loading: boolean;
}

export default function SearchBar({ onGenerate, loading }: SearchBarProps) {
  const [destination, setDestination] = useState("杭州");
  const [days, setDays] = useState(3);
  const [budget, setBudget] = useState(2000);
  const [prefWeights, setPrefWeights] = useState<Record<string, number>>({
    "自然风光": 2, "美食": 2, "亲子": 1, "历史文化": 0, "购物": 0,
  });
  const [favorFirst, setFavorFirst] = useState(false);
  const [favCount, setFavCount] = useState(0);

  // 获取收藏数量
  useEffect(() => {
    const token = localStorage.getItem("tripcraft-token");
    if (!token) return;
    axios.get(`${API_BASE}/api/favorites/ids`, { headers: { Authorization: `Bearer ${token}` } })
      .then(({ data }) => setFavCount(data.length))
      .catch(() => {});
  }, []);

  const handlePrefClick = (pref: string) => {
    setPrefWeights(prev => {
      const current = prev[pref] || 0;
      // 0 → 1 → 2 → 3 → 0 循环
      const next = (current + 1) % 4;
      return { ...prev, [pref]: next };
    });
  };

  const handleSubmit = async () => {
    if (!destination.trim()) { message.warning("请输入目的地"); return; }
    // 按权重降序排列偏好，权重>0 的才传入
    const sortedPrefs = Object.entries(prefWeights)
      .filter(([, w]) => w > 0)
      .sort((a, b) => b[1] - a[1])
      .map(([p]) => p);

    // 如果开启了收藏优先，获取收藏 ID
    let favIds: number[] = [];
    if (favorFirst) {
      const token = localStorage.getItem("tripcraft-token");
      if (token) {
        try {
          const { data } = await axios.get(`${API_BASE}/api/favorites/ids`, { headers: { Authorization: `Bearer ${token}` } });
          favIds = data;
        } catch { /* 忽略 */ }
      }
    }

    onGenerate({ destination: destination.trim(), days, budget, preferences: sortedPrefs, favorite_poi_ids: favIds });
  };

  return (
    <div className="relative my-8 px-1 md:px-3 pt-6 pb-2">
      {/* 底层复古卡片 */}
      <div className="absolute inset-0 bg-[#FBF7F0] border border-[#E4D7C1] rounded-lg shadow-sm transform rotate-[-2deg] -translate-x-2 translate-y-1.5 pointer-events-none overflow-hidden" />
      <div className="absolute inset-0 bg-[#F4ECD8] border border-[#DFCEAF] rounded-lg shadow-md transform rotate-[1.5deg] translate-x-2.5 translate-y-2 pointer-events-none" />

      {/* 邮票装饰 */}
      <div className="absolute -top-6 right-8 w-18 h-22 bg-[#FFFDF7] p-1 shadow-lg border border-[#DFCEAF] transform rotate-[12deg] pointer-events-none z-0 hidden sm:block overflow-hidden">
        <div className="absolute inset-0 bg-[#FFFDF9] border-2 border-double border-primary/30 m-0.5 flex flex-col items-center justify-between p-1">
          <div className="text-[7px] font-bold text-primary/60 font-mono tracking-wider">POSTAGE</div>
          <Compass className="w-7 h-7 text-primary/40" />
          <div className="text-[8px] font-bold text-[#5A4032] font-mono">¥ 1.20</div>
        </div>
      </div>

      {/* 主表单 */}
      <div className="relative z-10 bg-[#FFFDF9] border-[3px] border-double border-primary rounded-lg p-6 md:p-8 shadow-lg transform rotate-[-0.2deg] hover:rotate-0 transition-transform duration-300">
        <div className="text-sm font-bold text-foreground-secondary uppercase tracking-widest mb-5 font-mono flex items-center gap-1.5">
          <span className="text-primary">◇</span> 规划你的个性化明信片旅程
        </div>

        <Form layout="vertical" onFinish={handleSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            <div className="md:col-span-1">
              <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-2 font-mono">目的地 / City</label>
              <div className="relative">
                <MapPin className="absolute left-3 top-2.5 h-4 w-4 text-foreground-tertiary z-10" />
                <Input value={destination} onChange={(e) => setDestination(e.target.value)} placeholder="你想去哪里？"
                  className="pl-9 h-10 border-b border-t-0 border-l-0 border-r-0 border-border hover:border-primary focus:border-primary rounded-none shadow-none font-semibold" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-2 font-mono">天数 / Days</label>
              <Select value={days} onChange={setDays} className="w-full" style={{ height: '40px' }}
                popupMatchSelectWidth={false}>
                <Option value={2}>2 天行程</Option>
                <Option value={3}>3 天精选</Option>
                <Option value={5}>5 天深度</Option>
              </Select>
            </div>
            <div>
              <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-2 font-mono">人均预算 (元)</label>
              <InputNumber value={budget} onChange={(v) => setBudget(v || 2000)} min={500} max={50000} step={500} controls={false}
                className="w-full h-10 rounded-none border-b border-t-0 border-l-0 border-r-0 border-border hover:border-primary focus:border-primary" />
            </div>
            <div>
              <Button type="primary" htmlType="submit" loading={loading} aria-label={loading ? "正在生成行程" : "生成旅行攻略"}
                className="w-full h-10 bg-primary border-primary hover:bg-primary-dark active:scale-[0.98] transition-transform text-white font-bold tracking-wider rounded-sm uppercase">
                {loading ? "生成中..." : "生成旅行攻略"}
              </Button>
            </div>
          </div>

          {/* 热门城市 */}
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <span className="text-xs text-foreground-tertiary font-mono mr-2">快捷推荐:</span>
            {HOT_CITIES.map((city) => (
              <button key={city} onClick={() => setDestination(city)} type="button"
                className={`text-xs px-2.5 py-1 border rounded-full transition-all ${destination === city ? "bg-primary text-background border-primary" : "border-border text-foreground-secondary hover:border-primary hover:text-primary"}`}>
                {city}
              </button>
            ))}
          </div>

          {/* 偏好权重 */}
          <div className="mt-6 pt-4 border-t border-dashed border-border">
            <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-2 font-mono">
              选择你的旅行偏好 / Preferences <span className="text-foreground-tertiary normal-case font-normal ml-2">（点击切换权重：普通 → 喜欢 → 强烈推荐）</span>
            </label>
            <div className="flex flex-wrap gap-2.5">
              {PREFERENCES.map((pref) => {
                const weight = prefWeights[pref] || 0;
                const active = weight > 0;
                return (
                  <button key={pref} type="button" onClick={() => handlePrefClick(pref)} aria-label={`${pref} 偏好权重: ${WEIGHT_LABELS[weight] || "未选"}`}
                    className={`text-sm px-4 py-2 border-2 rounded-full transition-all font-semibold flex items-center gap-1.5 ${
                      active
                        ? weight === 3
                          ? "bg-primary text-background border-primary shadow-md"
                          : weight === 2
                            ? "bg-primary/80 text-background border-primary"
                            : "bg-primary/15 text-primary border-primary/50"
                        : "border-border text-foreground-secondary hover:border-primary hover:text-primary"
                    }`}>
                    {pref}
                    {active && (
                      <span className="flex items-center gap-0.5">
                        {Array.from({ length: weight }).map((_, i) => (
                          <Star key={i} className="w-2.5 h-2.5 fill-current" />
                        ))}
                      </span>
                    )}
                    {active && <span className="text-[9px] font-mono opacity-70">{WEIGHT_LABELS[weight]}</span>}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 收藏优先 */}
          {favCount > 0 && (
            <div className="mt-4 pt-3 border-t border-dashed border-border flex items-center gap-2">
              <button
                type="button"
                onClick={() => setFavorFirst(!favorFirst)}
                className={`flex items-center gap-1.5 text-xs px-3 py-1.5 border rounded-full transition-all ${favorFirst ? "bg-primary text-white border-primary" : "border-border text-foreground-secondary hover:border-primary"}`}
              >
                <Heart className={`w-3.5 h-3.5 ${favorFirst ? "fill-current" : ""}`} />
                优先收藏景点
                <span className="text-[10px] opacity-70">({favCount})</span>
              </button>
            </div>
          )}
        </Form>
      </div>
    </div>
  );
}