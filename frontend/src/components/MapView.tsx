import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Itinerary } from "../services/api";

const DAY_COLORS = ["#C9622A", "#5B8C5A", "#8B6F4E", "#B8860B", "#6B4A8C"];

/** 为每天生成一个彩色圆形标记图标 */
function makeColoredIcon(color: string, day: number) {
  return L.divIcon({
    className: "custom-marker",
    html: `<div style="
      width: 28px; height: 28px; border-radius: 50% 50% 50% 0;
      background: ${color}; border: 2px solid #fff;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      transform: rotate(-45deg);
      display: flex; align-items: center; justify-content: center;
    "><span style="transform: rotate(45deg); color: #fff; font-size: 11px; font-weight: bold; font-family: monospace;">D${day}</span></div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 28],
    popupAnchor: [0, -28],
  });
}

/** 自动调整地图视野以包含所有点 */
function FitBounds({ points }: { points: { lat: number; lng: number }[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 0) return;
    const bounds = L.latLngBounds(points.map(p => [p.lat, p.lng] as [number, number]));
    map.fitBounds(bounds, { padding: [50, 50] });
  }, [map, points]);
  return null;
}

/** 强制地图在组件渲染后 invalidate（修复缩放不跟随问题） */
function MapInvalidator() {
  const map = useMap();
  useEffect(() => {
    // 延迟 invalidate 确保容器尺寸已计算
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 100);
    return () => clearTimeout(timer);
  }, [map]);
  return null;
}

export default function MapView({ itinerary }: { itinerary: Itinerary }) {
  if (!itinerary) return null;

  const allPoints: { lat: number; lng: number; spot: string; day: number; time: string; category: string }[] = [];
  itinerary.itinerary?.forEach((day) => {
    day.items?.forEach((item) => {
      if (item.lat && item.lng) allPoints.push({
        lat: item.lat, lng: item.lng, spot: item.spot, day: day.day,
        time: item.time, category: item.category,
      });
    });
  });

  if (allPoints.length === 0) {
    return <div className="bg-background-tertiary border border-border p-8 text-center text-foreground-tertiary italic text-sm rounded-sm">暂无有效的地理位置信息</div>;
  }

  const centerLat = allPoints.reduce((s, p) => s + p.lat, 0) / allPoints.length;
  const centerLng = allPoints.reduce((s, p) => s + p.lng, 0) / allPoints.length;

  const dayRoutes = itinerary.itinerary?.map((day, idx) => ({
    day: day.day,
    color: DAY_COLORS[idx % DAY_COLORS.length],
    positions: (day.items || []).filter(i => i.lat && i.lng).map(i => [i.lat, i.lng] as [number, number]),
  })).filter(r => r.positions.length > 0) || [];

  return (
    <div className="border-2 border-border-dark rounded-sm overflow-hidden shadow-sm relative">
      <div style={{ filter: "sepia(0.2) contrast(0.95) saturate(1.15)" }}>
        <MapContainer
          key={itinerary.destination + itinerary.days}
          center={[centerLat, centerLng]}
          zoom={11}
          scrollWheelZoom={true}
          style={{ height: 380, width: "100%", background: "#EDE9DA" }}
        >
          <MapInvalidator />
          <FitBounds points={allPoints} />
          <TileLayer url="https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}" subdomains={["1", "2", "3", "4"]} attribution='&copy; 高德地图' />

          {/* 每天路线线条 */}
          {dayRoutes.map((route) => (
            <Polyline
              key={route.day}
              positions={route.positions}
              pathOptions={{ color: route.color, weight: 5, opacity: 0.85 }}
            />
          ))}

          {/* 每天彩色标记 */}
          {allPoints.map((point, idx) => {
            const color = DAY_COLORS[(point.day - 1) % DAY_COLORS.length];
            return (
              <Marker
                key={idx}
                position={[point.lat, point.lng]}
                icon={makeColoredIcon(color, point.day)}
              >
                <Popup>
                  <div className="p-1">
                    <div className="font-bold text-sm mb-1">{point.spot}</div>
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: color }} />
                      <span className="text-xs font-bold">Day {point.day}</span>
                      <span className="text-xs text-gray-500">{point.time}</span>
                    </div>
                    <div className="text-xs text-gray-500">{point.category}</div>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>

      {/* 图例 */}
      <div className="absolute bottom-3 left-3 z-[1000] bg-background-secondary border border-border-dark p-2 rounded-sm text-[11px] font-mono shadow flex flex-col gap-1">
        <div className="font-bold text-foreground mb-0.5 border-b border-border pb-0.5">路线色例</div>
        {itinerary.itinerary?.map((day, idx) => (
          <div key={day.day} className="flex items-center gap-2">
            <span className="w-4 h-1 inline-block rounded-sm" style={{ backgroundColor: DAY_COLORS[idx % DAY_COLORS.length] }} />
            <span>Day {day.day} ({day.items?.length || 0} 景点)</span>
          </div>
        ))}
      </div>
    </div>
  );
}