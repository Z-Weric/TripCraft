import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Button, Popconfirm, message, Empty, Spin } from "antd";
import { Clock, Trash2, MapPin, Calendar, DollarSign, ArrowLeft } from "lucide-react";
import { listTrips, deleteTrip, type TripSummary } from "../services/api";

export default function History() {
  const [trips, setTrips] = useState<TripSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const loadTrips = async () => {
    setLoading(true);
    try {
      const data = await listTrips();
      setTrips(data);
    } catch {
      message.error("加载历史行程失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadTrips(); }, []);

  const handleDelete = async (id: number) => {
    try {
      await deleteTrip(id);
      message.success("已删除");
      setTrips(prev => prev.filter(t => t.id !== id));
    } catch {
      message.error("删除失败");
    }
  };

  return (
    <div className="min-h-screen bg-transparent flex flex-col">
      <header className="sticky top-0 z-50 bg-background-secondary border-b border-border-light shadow-sm">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between gap-6">
          <Link to="/" className="text-2xl font-black font-display tracking-tight text-foreground hover:text-primary transition-colors">
            Trip<span className="text-primary font-bold">Craft</span>
          </Link>
          <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] uppercase font-bold tracking-widest border border-primary text-primary rounded-sm">历史行程</span>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-10 flex-1 w-full">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-black font-display tracking-tight text-foreground mb-1 uppercase">行程历史</h1>
            <p className="text-sm text-foreground-secondary font-mono">您生成过的所有旅行明信片</p>
          </div>
          <Link to="/">
            <Button icon={<ArrowLeft className="w-4 h-4 inline" />} className="font-mono font-bold border-border hover:border-primary rounded-sm">
              返回生成
            </Button>
          </Link>
        </div>

        {loading ? (
          <div className="flex justify-center py-20"><Spin size="large" /></div>
        ) : trips.length === 0 ? (
          <div className="border border-dashed border-border rounded-sm p-16 text-center">
            <Clock className="w-10 h-10 text-foreground-tertiary mx-auto mb-4 opacity-50" />
            <Empty description={<span className="text-sm text-foreground-tertiary italic">暂无历史行程</span>} />
            <Link to="/" className="inline-block mt-6 text-xs font-mono font-bold text-primary border border-primary px-4 py-2 rounded-sm hover:bg-primary hover:text-background transition-all uppercase tracking-wider">
              生成第一份行程
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {trips.map((trip) => (
              <div key={trip.id} className="bg-background-secondary border border-border rounded-sm p-5 hover:border-primary transition-all group">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-xl font-black font-display text-foreground tracking-tight">{trip.destination}</h3>
                    <p className="text-xs text-foreground-tertiary font-mono mt-0.5">{trip.created_at}</p>
                  </div>
                  <Popconfirm title="确定删除此行程？" onConfirm={() => handleDelete(trip.id)} okText="删除" cancelText="取消">
                    <button className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 hover:bg-error/10 rounded border border-transparent hover:border-error/30">
                      <Trash2 className="w-3.5 h-3.5 text-error" />
                    </button>
                  </Popconfirm>
                </div>

                <p className="text-sm text-foreground-secondary italic font-display mb-3 line-clamp-1">"{trip.summary}"</p>

                <div className="flex flex-wrap gap-3 text-xs font-mono text-foreground-tertiary">
                  <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{trip.days}天</span>
                  <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" />¥{trip.total_cost}/{trip.budget}</span>
                  {trip.preferences && (
                    <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{trip.preferences}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <footer className="border-t border-border-light bg-background-tertiary py-6 text-center text-xs text-foreground-tertiary font-mono tracking-wider">
        TRIPCRAFT &copy; 2026. ALL RIGHTS RESERVED.
      </footer>
    </div>
  );
}