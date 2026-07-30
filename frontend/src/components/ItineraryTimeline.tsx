import { useState } from "react";
import { Timeline, Tag } from "antd";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { Itinerary } from "../services/api";

const CATEGORY_COLORS: Record<string, string> = {
  "自然风光": "#5B8C5A", "美食": "#C9622A", "历史文化": "#8B6F4E", "购物": "#B8860B", "亲子": "#6B4A8C",
};

export default function ItineraryTimeline({ itinerary }: { itinerary: Itinerary }) {
  const [activeDayIdx, setActiveDayIdx] = useState(0);

  if (!itinerary || !itinerary.itinerary || itinerary.itinerary.length === 0) return null;

  const totalDays = itinerary.itinerary.length;
  const handlePrev = (e: React.MouseEvent) => { e.stopPropagation(); if (activeDayIdx > 0) setActiveDayIdx(activeDayIdx - 1); };
  const handleNext = (e: React.MouseEvent) => { e.stopPropagation(); if (activeDayIdx < totalDays - 1) setActiveDayIdx(activeDayIdx + 1); };

  return (
    <div className="py-2 flex flex-col h-full justify-between">
      {/* 摘要 */}
      <div className="text-center text-sm md:text-base text-foreground-secondary italic font-display leading-relaxed py-3 border-b border-dashed border-border-light mb-4 select-none">" {itinerary.summary} "</div>

      {/* 天数导航 */}
      <div className="flex items-center justify-between gap-2 border-b border-border-dark pb-2 mb-4 select-none no-print">
        <button onClick={handlePrev} disabled={activeDayIdx === 0} className={`p-1 border border-border-dark rounded-sm transition-all active:scale-95 ${activeDayIdx === 0 ? "opacity-30 cursor-not-allowed" : "hover:bg-primary/5 hover:text-primary text-foreground"}`}><ChevronLeft className="w-4 h-4" /></button>
        <div className="flex-1 flex gap-2 justify-center">
          {itinerary.itinerary.map((day, idx) => (
            <button key={day.day} onClick={(e) => { e.stopPropagation(); setActiveDayIdx(idx); }}
              className={`px-3 py-1 text-xs font-bold font-mono uppercase tracking-wider border-b-2 transition-all ${idx === activeDayIdx ? "border-primary text-primary" : "border-transparent text-foreground-tertiary hover:text-primary"}`}>
              Day {day.day}
            </button>
          ))}
        </div>
        <button onClick={handleNext} disabled={activeDayIdx === totalDays - 1} className={`p-1 border border-border-dark rounded-sm transition-all active:scale-95 ${activeDayIdx === totalDays - 1 ? "opacity-30 cursor-not-allowed" : "hover:bg-primary/5 hover:text-primary text-foreground"}`}><ChevronRight className="w-4 h-4" /></button>
      </div>

      {/* 时间线 */}
      <div className="flex-1 overflow-y-auto pr-1 max-h-[340px] scrollbar-thin">
        {itinerary.itinerary.map((day, idx) => {
          const isActive = idx === activeDayIdx;
          return (
            <div key={day.day} className={`mb-4 ${isActive ? "block" : "hidden"} print:block print:mb-8`}>
              <div className="flex items-baseline justify-between pb-1 border-b border-foreground mb-4 select-none">
                <span className="text-xl font-black font-display tracking-tight text-foreground flex items-center gap-2">
                  <span className="text-xs font-bold uppercase font-mono tracking-widest text-primary">Day</span><span>{day.day}</span>
                </span>
                <span className="text-sm font-bold font-mono text-primary">预计消费: ¥{(day.day_cost || 0).toLocaleString()}</span>
              </div>
              <Timeline items={day.items.map((item) => ({
                color: "#C9622A",
                children: (
                  <div>
                    <div className="text-xs text-foreground-tertiary font-mono mb-0.5">{item.time}</div>
                    <div className="text-base font-semibold font-display text-foreground mb-1">{item.spot}</div>
                    <div className="flex gap-2 items-center text-xs text-foreground-secondary">
                      <Tag style={{ fontSize: 10, padding: "1px 6px", borderRadius: 2, color: CATEGORY_COLORS[item.category] || "#8B6F4E", background: `${CATEGORY_COLORS[item.category] || "#8B6F4E"}1f`, border: "none" }}>{item.category}</Tag>
                      <span>{item.duration}</span>
                      <span className="font-bold" style={{ color: item.cost === 0 ? "#6B8E6B" : "#2C1810" }}>{item.cost === 0 ? "免费" : `¥${item.cost}`}</span>
                    </div>
                    {item.note && <div className="text-xs text-foreground-tertiary mt-1 italic leading-relaxed">{item.note}</div>}
                  </div>
                ),
              }))} />
              <div className="mt-2 pt-2 border-t border-dashed border-border-light pl-4 text-xs text-foreground-secondary font-mono">
                <span className="text-primary font-bold">●</span> 推荐交通：<strong className="text-foreground">{day.transport}</strong>
              </div>
            </div>
          );
        })}
      </div>

      <div className="text-center pt-2 text-[10px] text-foreground-tertiary font-mono uppercase tracking-widest border-t border-dashed border-border-light mt-2 select-none no-print flex items-center justify-between">
        <span>TRIPCRAFT DAY NAV</span><span>第 {activeDayIdx + 1} 天 / 共 {totalDays} 天</span>
      </div>
    </div>
  );
}