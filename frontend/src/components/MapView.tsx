import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Itinerary } from "../services/api";

// 修复 Leaflet 默认图标路径
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const DAY_COLORS = ["#C9622A", "#5B8C5A", "#8B6F4E", "#B8860B"];

interface MapViewProps {
  itinerary: Itinerary;
}

export default function MapView({ itinerary }: MapViewProps) {
  // 收集所有景点坐标
  const allPoints: { lat: number; lng: number; spot: string; day: number }[] = [];
  itinerary.itinerary.forEach((day) => {
    day.items.forEach((item) => {
      allPoints.push({ lat: item.lat, lng: item.lng, spot: item.spot, day: day.day });
    });
  });

  if (allPoints.length === 0) return null;

  // 计算地图中心
  const centerLat = allPoints.reduce((s, p) => s + p.lat, 0) / allPoints.length;
  const centerLng = allPoints.reduce((s, p) => s + p.lng, 0) / allPoints.length;

  // 按天生成路线
  const dayRoutes: { day: number; color: string; positions: [number, number][] }[] = [];
  itinerary.itinerary.forEach((day, idx) => {
    const positions = day.items.map((item) => [item.lat, item.lng] as [number, number]);
    dayRoutes.push({
      day: day.day,
      color: DAY_COLORS[idx % DAY_COLORS.length],
      positions,
    });
  });

  return (
    <div
      style={{
        border: "1px solid #E8DCC8",
        borderRadius: 2,
        overflow: "hidden",
      }}
    >
      <MapContainer
        center={[centerLat, centerLng]}
        zoom={11}
        style={{ height: 360, width: "100%", background: "#EDE9DA" }}
      >
        <TileLayer
          url="https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}"
          subdomains={["1", "2", "3", "4"]}
          attribution='&copy; 高德地图'
        />

        {/* 按天绘制路线 */}
        {dayRoutes.map((route) => (
          <Polyline
            key={route.day}
            positions={route.positions}
            pathOptions={{ color: route.color, weight: 3, opacity: 0.7 }}
          />
        ))}

        {/* 景点标记 */}
        {allPoints.map((point, idx) => (
          <Marker key={idx} position={[point.lat, point.lng]}>
            <Popup>
              <div style={{ fontFamily: "sans-serif" }}>
                <strong>{point.spot}</strong>
                <br />
                <span style={{ color: "#8B7B6A", fontSize: 12 }}>Day {point.day}</span>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}