import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Spin, Empty, message, Modal, Input } from "antd";
import { ArrowLeft, Clock, Trash2, Star, MapPin, Edit2, Heart, Map as MapIcon, FileCheck2 } from "lucide-react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { useUserStore } from "../stores/userStore";
import { listTrips, deleteTrip, isLoggedIn, updateProfile, type TripSummary } from "../services/api";
import { API_BASE } from "../services/config";
import axios from "axios";

interface FavoritePOI {
  id: number; name: string; category: string; city: string; cost: number; rating: number;
}

interface UserStats {
  trip_count: number; total_days: number; city_count: number;
  total_cost: number; favorite_count: number; review_count: number; cities: string[];
}

interface CityVisit {
  city: string; trip_count: number; total_cost: number; lat: number; lng: number;
}

const CITY_COLORS = ["#C9622A", "#5B8C5A", "#8B6F4E", "#B8860B", "#6B4A8C", "#7A8B99"];

export default function Profile() {
  const navigate = useNavigate();
  const { user, fetchMe, logout } = useUserStore();
  const [tab, setTab] = useState<"trips" | "favorites" | "footprint">("trips");
  const [trips, setTrips] = useState<TripSummary[]>([]);
  const [favorites, setFavorites] = useState<FavoritePOI[]>([]);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [cities, setCities] = useState<CityVisit[]>([]);
  const [loading, setLoading] = useState(true);
  const [editOpen, setEditOpen] = useState(false);
  const [nickname, setNickname] = useState("");

  useEffect(() => { fetchMe(); }, []);

  useEffect(() => {
    if (!isLoggedIn()) { navigate("/login"); return; }
    loadData();
  }, []);

  const headers = { Authorization: `Bearer ${localStorage.getItem("tripcraft-token")}` };

  const loadData = async () => {
    setLoading(true);
    try {
      const [tripsRes, favRes, statsRes, cityRes] = await Promise.all([
        listTrips(),
        axios.get(`${API_BASE}/api/favorites`, { headers }),
        axios.get(`${API_BASE}/api/user/stats`, { headers }),
        axios.get(`${API_BASE}/api/user/cities`, { headers }),
      ]);
      setTrips(tripsRes);
      setFavorites(favRes.data);
      setStats(statsRes.data);
      setCities(cityRes.data);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteTrip(id);
      setTrips(prev => prev.filter(t => t.id !== id));
      message.success("已删除");
    } catch { message.error("删除失败"); }
  };

  const handleTogglePublic = async (id: number) => {
    try {
      await axios.put(`${API_BASE}/api/itineraries/${id}/visibility`, {}, { headers });
      setTrips(prev => prev.map(t => t.id === id ? { ...t, is_public: t.is_public ? 0 : 1 } : t));
      message.success("已切换可见性");
    } catch { message.error("操作失败"); }
  };

  const handleSaveNickname = async () => {
    if (!nickname.trim()) { message.warning("昵称不能为空"); return; }
    try {
      await updateProfile({ nickname: nickname.trim() });
      await fetchMe();
      message.success("已保存");
      setEditOpen(false);
    } catch { message.error("保存失败"); }
  };

  // 按城市分组收藏
  const favoritesByCity = favorites.reduce((acc, poi) => {
    if (!acc[poi.city]) acc[poi.city] = [];
    acc[poi.city].push(poi);
    return acc;
  }, {} as Record<string, FavoritePOI[]>);

  if (!isLoggedIn()) {
    return <div className="min-h-screen flex items-center justify-center"><Spin size="large" /></div>;
  }

  return (
    <div className="min-h-screen bg-transparent flex flex-col">
      <header className="sticky top-0 z-50 bg-background-secondary border-b border-border-light shadow-sm">
        <div className="max-w-[888px] mx-auto px-6 h-16 flex items-center justify-between gap-6">
          <Link to="/home" className="text-2xl font-black font-display tracking-tight text-foreground hover:text-primary transition-colors">
            Trip<span className="text-primary font-bold">Craft</span>
          </Link>
          <button onClick={() => { logout(); navigate("/"); }} className="text-xs font-mono text-foreground-tertiary hover:text-error">退出登录</button>
        </div>
      </header>

      <div className="max-w-[888px] mx-auto px-6 py-10 flex-1 w-full">
          <Link to="/home" className="text-xs text-foreground-tertiary hover:text-primary font-mono flex items-center gap-1 mb-4">
            <ArrowLeft className="w-3.5 h-3.5" />返回首页
          </Link>
          <Link to="/training-review" className="mb-4 inline-flex items-center gap-1 text-xs font-mono text-foreground-tertiary hover:text-primary">
            <FileCheck2 className="h-3.5 w-3.5" />训练样本审核
          </Link>

        {/* 用户信息卡 + 编辑 */}
        <div className="bg-background-secondary border border-border rounded-sm p-6 mb-4 flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-primary text-white text-2xl font-black font-display flex items-center justify-center">
            {user?.nickname?.[0]?.toUpperCase() || "U"}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-black font-display text-foreground">{user?.nickname}</h1>
              <button onClick={() => { setNickname(user?.nickname || ""); setEditOpen(true); }} className="text-foreground-tertiary hover:text-primary transition-colors">
                <Edit2 className="w-3.5 h-3.5" />
              </button>
            </div>
            <p className="text-xs text-foreground-tertiary font-mono">{user?.email}</p>
            {user?.created_at && <p className="text-[10px] text-foreground-disabled font-mono mt-0.5">注册于 {user.created_at}</p>}
          </div>
        </div>

        {/* 旅行统计仪表盘 */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {[
              { label: "行程", value: stats.trip_count, icon: Clock, color: "#C9622A" },
              { label: "旅行天数", value: stats.total_days, icon: Star, color: "#5B8C5A" },
              { label: "去过城市", value: stats.city_count, icon: MapPin, color: "#8B6F4E" },
              { label: "总花费", value: `¥${stats.total_cost}`, icon: Heart, color: "#B8860B" },
            ].map((item, i) => {
              const Icon = item.icon;
              return (
                <div key={i} className="bg-background-secondary border border-border rounded-sm p-4 text-center">
                  <Icon className="w-4 h-4 mx-auto mb-1.5" style={{ color: item.color }} />
                  <div className="text-2xl font-black font-mono" style={{ color: item.color }}>{item.value}</div>
                  <div className="text-[10px] text-foreground-tertiary font-mono uppercase mt-0.5">{item.label}</div>
                </div>
              );
            })}
          </div>
        )}

        {/* Tab */}
        <div className="flex gap-4 border-b border-border-light mb-6">
          {[
            { key: "trips", label: "我的行程", icon: Clock },
            { key: "favorites", label: "收藏景点", icon: Heart },
            { key: "footprint", label: "旅行足迹", icon: MapIcon },
          ].map((t) => {
            const Icon = t.icon;
            return (
              <button key={t.key} onClick={() => setTab(t.key as typeof tab)}
                className={`pb-2 text-sm font-bold font-mono uppercase tracking-wider border-b-2 transition-all flex items-center gap-1.5 ${tab === t.key ? "border-primary text-primary" : "border-transparent text-foreground-tertiary hover:text-primary"}`}>
                <Icon className="w-3.5 h-3.5" />{t.label}
              </button>
            );
          })}
        </div>

        {loading ? (
          <div className="flex justify-center py-12"><Spin /></div>
        ) : tab === "trips" ? (
          trips.length === 0 ? (
            <Empty description={<span className="text-sm text-foreground-tertiary italic">暂无行程</span>} >
              <Link to="/home" className="text-xs font-mono text-primary hover:underline">去生成行程 →</Link>
            </Empty>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {trips.map((trip) => (
                <div key={trip.id} className="bg-background-secondary border border-border rounded-sm p-4 hover:border-primary transition-all group">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="text-lg font-black font-display text-foreground">{trip.destination}</h3>
                      <p className="text-[10px] text-foreground-tertiary font-mono mt-0.5">{trip.created_at}</p>
                    </div>
                    <div className="flex items-center gap-1">
                      <button onClick={() => handleTogglePublic(trip.id)} className={`text-[10px] font-mono px-2 py-0.5 border rounded-sm transition-all ${trip.is_public ? "bg-primary text-white border-primary" : "border-border text-foreground-tertiary hover:border-primary"}`}>
                        {trip.is_public ? "公开" : "私有"}
                      </button>
                      <button onClick={() => handleDelete(trip.id)} className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-error/10 rounded">
                        <Trash2 className="w-3.5 h-3.5 text-error" />
                      </button>
                    </div>
                  </div>
                  <p className="text-xs text-foreground-secondary italic line-clamp-1 mb-2">"{trip.summary}"</p>
                  <div className="flex items-center gap-3 text-xs font-mono text-foreground-tertiary">
                    <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{trip.days}天</span>
                    <span>¥{trip.total_cost}/{trip.budget}</span>
                    {(trip.user_rating ?? 0) > 0 && <span className="flex items-center gap-0.5"><Star className="w-3 h-3 text-primary fill-current" />{trip.user_rating}</span>}
                  </div>
                </div>
              ))}
            </div>
          )
        ) : tab === "favorites" ? (
          favorites.length === 0 ? (
            <Empty description={<span className="text-sm text-foreground-tertiary italic">暂无收藏</span>} />
          ) : (
            <div className="space-y-4">
              {Object.entries(favoritesByCity).map(([city, pois]) => (
                <div key={city}>
                  <h3 className="text-sm font-bold font-display text-foreground mb-2 flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-primary" />{city}
                    <span className="text-[10px] text-foreground-tertiary font-mono ml-1">({pois.length})</span>
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                    {pois.map((poi) => (
                      <div key={poi.id} className="bg-background-secondary border border-border rounded-sm p-3 hover:border-primary transition-all">
                        <h4 className="text-sm font-bold font-display text-foreground mb-1">{poi.name}</h4>
                        <div className="flex items-center gap-2 text-[10px] text-foreground-tertiary font-mono">
                          <span>★{poi.rating}</span>
                          <span>{poi.cost === 0 ? "免费" : `¥${poi.cost}`}</span>
                          <span>{poi.category}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )
        ) : (
          /* 旅行足迹地图 */
          cities.length === 0 ? (
            <Empty description={<span className="text-sm text-foreground-tertiary italic">暂无足迹</span>} />
          ) : (
            <div>
              <div className="border-2 border-border-dark rounded-sm overflow-hidden shadow-sm mb-4">
                <MapContainer
                  center={[32, 110]}
                  zoom={4}
                  scrollWheelZoom={false}
                  style={{ height: 400, width: "100%", background: "#EDE9DA" }}
                >
                  <TileLayer url="https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}" subdomains={["1", "2", "3", "4"]} attribution='&copy; 高德地图' />
                  {cities.map((c, idx) => (
                    <CircleMarker key={c.city} center={[c.lat, c.lng]}
                      radius={8 + c.trip_count * 3}
                      pathOptions={{ color: CITY_COLORS[idx % CITY_COLORS.length], fillColor: CITY_COLORS[idx % CITY_COLORS.length], fillOpacity: 0.6 }}
                    >
                      <Popup>
                        <div>
                          <div className="font-bold text-sm">{c.city}</div>
                          <div className="text-xs text-gray-500 mt-1">{c.trip_count} 次行程 · ¥{c.total_cost}</div>
                        </div>
                      </Popup>
                    </CircleMarker>
                  ))}
                </MapContainer>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {cities.map((c, idx) => (
                  <div key={c.city} className="bg-background-secondary border border-border rounded-sm p-3 text-center">
                    <div className="w-3 h-3 rounded-full mx-auto mb-1" style={{ backgroundColor: CITY_COLORS[idx % CITY_COLORS.length] }} />
                    <div className="text-sm font-bold font-display text-foreground">{c.city}</div>
                    <div className="text-[10px] text-foreground-tertiary font-mono">{c.trip_count}次 · ¥{c.total_cost}</div>
                  </div>
                ))}
              </div>
            </div>
          )
        )}
      </div>

      {/* 编辑昵称弹窗 */}
      <Modal title="编辑昵称" open={editOpen} onOk={handleSaveNickname} onCancel={() => setEditOpen(false)} okText="保存" cancelText="取消"
        okButtonProps={{ className: "bg-primary border-primary" }}>
        <Input value={nickname} onChange={(e) => setNickname(e.target.value)} placeholder="输入新昵称" maxLength={20} className="mt-2" />
      </Modal>
    </div>
  );
}
