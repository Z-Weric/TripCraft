import React from "react";
import L from "leaflet";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// 修复 Leaflet 默认标记图标路径
const LeafletIcon = L.Icon;
delete LeafletIcon.Default.prototype._getIconUrl;
LeafletIcon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const DAY_COLORS = ["#C9622A", "#5B8C5A", "#8B6F4E", "#B8860B", "#6B4A8C"];

export default function MapView({ itinerary }) {
  if (!itinerary) return null;

  // 整理所有景点坐标点
  const allPoints = [];
  itinerary.itinerary?.forEach((day) => {
    day.items?.forEach((item) => {
      if (item.lat && item.lng) {
        allPoints.push({
          lat: item.lat,
          lng: item.lng,
          spot: item.spot,
          day: day.day,
        });
      }
    });
  });

  if (allPoints.length === 0) {
    return (
      <div className="bg-background-tertiary border border-border p-8 text-center text-foreground-tertiary italic text-sm rounded-[2px]">
        暂无有效的地理位置信息，无法渲染路线图。
      </div>
    );
  }

  // 计算地图中心点
  const centerLat = allPoints.reduce((sum, p) => sum + p.lat, 0) / allPoints.length;
  const centerLng = allPoints.reduce((sum, p) => sum + p.lng, 0) / allPoints.length;

  // 按天将景点串联成折线
  const dayRoutes = [];
  itinerary.itinerary?.forEach((day, idx) => {
    const positions = (day.items || [])
      .filter(item => item.lat && item.lng)
      .map(item => [item.lat, item.lng]);
    
    if (positions.length > 0) {
      dayRoutes.push({
        day: day.day,
        color: DAY_COLORS[idx % DAY_COLORS.length],
        positions,
      });
    }
  });

  return (
    <div className="border-2 border-border-dark rounded-[2px] overflow-hidden shadow-sm relative">
      {/* 叠加上层复古羊皮纸色彩滤镜（只影响地图，确保图例颜色纯净无偏差） */}
      <div style={{ filter: "sepia(0.85) contrast(0.92) saturate(1.1) brightness(1.01)" }}>
        <MapContainer
          center={[centerLat, centerLng]}
          zoom={11}
          scrollWheelZoom={false}
          style={{ height: 380, width: "100%", background: "#EDE9DA" }}
        >
          {/* 高德地图高保真瓦片源 */}
          <TileLayer
            url="https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}"
            subdomains={["1", "2", "3", "4"]}
            attribution='&copy; <a href="https://lbs.amap.com/">高德地图 LBS</a>'
          />

          {/* 绘制每日旅行轨迹折线 */}
          {dayRoutes.map((route) => (
            <Polyline
              key={route.day}
              positions={route.positions}
              pathOptions={{ color: route.color, weight: 4, opacity: 0.8 }}
            />
          ))}

          {/* 绘制旅行地标 Pins */}
          {allPoints.map((point, idx) => (
            <Marker key={idx} position={[point.lat, point.lng]}>
              <Popup>
                <div className="p-1 font-sans">
                  <div className="font-bold text-foreground text-sm font-display mb-1">{point.spot}</div>
                  <div className="flex items-center gap-1.5">
                    <span 
                      className="w-2.5 h-2.5 rounded-full inline-block"
                      style={{ backgroundColor: DAY_COLORS[(point.day - 1) % DAY_COLORS.length] }}
                    />
                    <span className="text-xs text-foreground-secondary font-mono">第 {point.day} 天推荐行程</span>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
      
      {/* 图例 */}
      <div className="absolute bottom-3 left-3 z-[1000] bg-background-secondary border border-border-dark p-2 rounded-[2px] text-[11px] font-mono shadow flex flex-col gap-1">
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