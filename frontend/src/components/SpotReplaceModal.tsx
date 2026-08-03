import { useState, useEffect } from "react";
import { Modal, Spin, message } from "antd";
import axios from "axios";
import { API_BASE } from "../services/config";
import type { ItineraryItem } from "../services/api";

interface SpotReplaceModalProps {
  open: boolean;
  currentSpot: ItineraryItem | null;
  city: string;
  onClose: () => void;
  onReplace: (newSpot: ItineraryItem) => void;
}

interface POIOption {
  name: string;
  category: string;
  lat: number;
  lng: number;
  cost: number;
  duration: string;
  note: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  "自然风光": "#5B8C5A", "美食": "#C9622A", "历史文化": "#8B6F4E", "购物": "#B8860B", "亲子": "#6B4A8C",
};

export default function SpotReplaceModal({ open, currentSpot, city, onClose, onReplace }: SpotReplaceModalProps) {
  const [options, setOptions] = useState<POIOption[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !city) return;
    setLoading(true);
    axios.get(`${API_BASE}/api/pois`, { params: { city } })
      .then(({ data }) => {
        // 排除当前景点
        const filtered = (data as POIOption[]).filter(p => p.name !== currentSpot?.spot);
        setOptions(filtered);
      })
      .catch(() => message.error("加载景点列表失败"))
      .finally(() => setLoading(false));
  }, [open, city, currentSpot]);

  const handleSelect = (poi: POIOption) => {
    const newSpot: ItineraryItem = {
      time: currentSpot?.time || "09:00-12:00",
      spot: poi.name,
      category: poi.category,
      duration: poi.duration || "2h",
      cost: poi.cost,
      lat: poi.lat,
      lng: poi.lng,
      note: poi.note,
    };
    onReplace(newSpot);
    onClose();
  };

  return (
    <Modal
      title={<span className="font-display font-bold text-lg">替换景点</span>}
      open={open}
      onCancel={onClose}
      footer={null}
      width={480}
    >
      <div className="py-2">
        <p className="text-xs text-foreground-secondary mb-4 font-mono">
          当前景点：<strong className="text-foreground">{currentSpot?.spot}</strong>
          {" → "}从{city}的景点列表中选择替代
        </p>
        {loading ? (
          <div className="flex justify-center py-8"><Spin /></div>
        ) : (
          <div className="max-h-80 overflow-y-auto scrollbar-thin space-y-2">
            {options.map((poi) => (
              <button
                key={poi.name}
                onClick={() => handleSelect(poi)}
                className="w-full text-left p-3 border border-border rounded-sm hover:border-primary hover:bg-primary/5 transition-all group"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-display font-semibold text-foreground text-sm">{poi.name}</span>
                  <span className="text-xs font-mono font-bold" style={{ color: poi.cost === 0 ? "#6B8E6B" : "#2C1810" }}>
                    {poi.cost === 0 ? "免费" : `¥${poi.cost}`}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-foreground-tertiary">
                  <span className="px-1.5 py-0.5 rounded-sm text-[10px]" style={{ color: CATEGORY_COLORS[poi.category] || "#8B6F4E", background: `${CATEGORY_COLORS[poi.category] || "#8B6F4E"}1f` }}>
                    {poi.category}
                  </span>
                  <span>{poi.duration}</span>
                </div>
                {poi.note && <p className="text-xs text-foreground-tertiary italic mt-1 line-clamp-1">{poi.note}</p>}
              </button>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}