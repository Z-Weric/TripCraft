import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Itinerary } from "../services/api";

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const DAY_COLORS = ["#C9622A", "#5B8C5A", "#8B6F4E", "#B8860B", "#6B4A8C"];

export default function MapView({ itinerary }: { itinerary: Itinerary }) {
  if (!itinerary) return null;

  const allPoints: { lat: number; lng: number; spot: string; day: number }[] = [];
  itinerary.itinerary?.forEach((day) => {
    day.items?.forEach((item) => {
      if (item.lat && item.lng) allPoints.push({ lat: item.lat, lng: item.lng, spot: item.spot, day: day.day });
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
      <div style={{ filter: "sepia(0.85) contrast(0.92) saturate(1.1) brightness(1.01)" }}>
        <MapContainer center={[centerLat, centerLng]} zoom={11} scrollWheelZoom={false} style={{ height: 380, width: "100%", background: "#EDE9DA" }}>
          <TileLayer url="https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}" subdomains={["1", "2", "3", "4"]} attribution='&copy; 高德地图' />
          {dayRoutes.map((route) => (<Polyline key={route.day} positions={route.positions} pathOptions={{ color: route.color, weight: 4, opacity: 0.8 }} />))}
          {allPoints.map((point, idx) => (
            <Marker key={idx} position={[point.lat, point.lng]}>
              <Popup>
                <div className="p-1">
                  <div className="font-bold text-sm mb-1">{point.spot}</div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: DAY_COLORS[(point.day - 1) % DAY_COLORS.length] }} />
                    <span className="text-xs">第 {point.day} 天推荐</span>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
      {/* 图例 */}
      <div className="absolute bottom-3 left-3 z-[1000] bg-background-secondary border border-border-dark p-2 rounded-sm text-[11px] font-mono shadow flex flex-col gap-1">
        <div className="font-bold text-foreground mb-0.5 border-b border-border pb-0.5">路线色例</div>
        {itinerary.itinerary?.map((day, idx) => (
          <div key={day.day} className="flex items-center gap-2">
            <span className="w-3 h-1 inline-block" style={{ backgroundColor: DAY_COLORS[idx % DAY_COLORS.length] }} />
            <span>Day {day.day} ({day.items?.length || 0} 景点)</span>
          </div>
        ))}
      </div>
    </div>
  );
}