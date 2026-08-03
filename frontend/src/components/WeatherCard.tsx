import { useState, useEffect } from "react";
import { Spin } from "antd";
import { CloudSun, CloudRain, Sun, Cloud, Snowflake, Wind } from "lucide-react";
import { getWeather, type WeatherDay } from "../services/api";

const WEEK_MAP: Record<string, string> = { "1": "周一", "2": "周二", "3": "周三", "4": "周四", "5": "周五", "6": "周六", "7": "周日" };

function WeatherIcon({ weather }: { weather: string }) {
  if (weather.includes("雨")) return <CloudRain className="w-5 h-5 text-info" />;
  if (weather.includes("雪")) return <Snowflake className="w-5 h-5 text-info" />;
  if (weather.includes("晴")) return <Sun className="w-5 h-5 text-warning" />;
  if (weather.includes("云") || weather.includes("阴")) return <Cloud className="w-5 h-5 text-foreground-tertiary" />;
  return <CloudSun className="w-5 h-5 text-primary-light" />;
}

interface WeatherCardProps {
  city: string;
  days: number;
}

export default function WeatherCard({ city, days }: WeatherCardProps) {
  const [forecasts, setForecasts] = useState<WeatherDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!city) return;
    setLoading(true);
    getWeather(city, days)
      .then((data) => {
        setForecasts(data.forecasts || []);
        setMessage(data.message || "");
      })
      .catch(() => setMessage("天气服务暂不可用"))
      .finally(() => setLoading(false));
  }, [city, days]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Spin size="small" />
        <span className="ml-2 text-xs text-foreground-tertiary font-mono">加载天气...</span>
      </div>
    );
  }

  if (message || forecasts.length === 0) {
    return (
      <div className="py-4 text-center text-xs text-foreground-tertiary italic font-mono">{message || "暂无天气数据"}</div>
    );
  }

  return (
    <div className="bg-background-secondary border border-border rounded-sm p-4">
      <div className="flex items-center gap-1.5 mb-3">
        <Wind className="w-3.5 h-3.5 text-primary" />
        <span className="text-xs font-bold text-foreground-secondary uppercase tracking-widest font-mono">{city}天气预报</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {forecasts.map((f, i) => (
          <div key={i} className="border border-border-light rounded-sm p-3 bg-background-tertiary">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono font-bold text-foreground">{WEEK_MAP[f.week] || f.date}</span>
              <WeatherIcon weather={f.dayweather} />
            </div>
            <div className="text-sm font-display text-foreground mb-1">{f.dayweather}</div>
            <div className="flex items-center gap-2 text-xs font-mono text-foreground-tertiary">
              <span className="text-primary font-bold">{f.daytemp}°</span>
              <span>/</span>
              <span>{f.nighttemp}°</span>
              {f.daypower && <span className="ml-1">{f.daywind}{f.daypower}级</span>}
            </div>
            {f.clothing && (
              <div className="mt-1.5 text-[10px] text-foreground-tertiary italic border-t border-border-light pt-1.5">
                {f.clothing}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}