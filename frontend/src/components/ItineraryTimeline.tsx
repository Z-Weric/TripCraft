import { useState } from "react";
import { Tag } from "antd";
import { ChevronLeft, ChevronRight, GripVertical, Replace } from "lucide-react";
import PoiDetailModal from "./PoiDetailModal";
import {
  DndContext, closestCenter, type DragEndEvent,
  PointerSensor, useSensor, useSensors,
} from "@dnd-kit/core";
import {
  SortableContext, arrayMove, useSortable, verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Itinerary, ItineraryItem } from "../services/api";
import SpotReplaceModal from "./SpotReplaceModal";

const CATEGORY_COLORS: Record<string, string> = {
  "自然风光": "#5B8C5A", "美食": "#C9622A", "历史文化": "#8B6F4E", "购物": "#B8860B", "亲子": "#6B4A8C",
};

interface SortableItemProps {
  item: ItineraryItem;
  onReplace: () => void;
  onSpotClick: (poiId: number) => void;
}

function SortableTimelineItem({ item, onReplace, onSpotClick }: SortableItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.spot + item.time });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="flex items-start gap-2 group relative">
      {/* 时间线圆点 + 连线 */}
      <div className="flex flex-col items-center mt-1 shrink-0" style={{ width: 16 }}>
        <div className="w-3 h-3 rounded-full border-2 border-primary bg-background" />
        <div className="w-0.5 flex-1 bg-border-light min-h-[20px]" style={{ marginTop: 2 }} />
      </div>
      <button {...attributes} {...listeners} className="mt-1 cursor-grab active:cursor-grabbing text-foreground-tertiary opacity-0 group-hover:opacity-100 transition-opacity touch-none">
        <GripVertical className="w-3.5 h-3.5" />
      </button>
      <div className="flex-1 pb-4">
        <div>
          <div className="text-xs text-foreground-tertiary font-mono mb-0.5">{item.time}</div>
          <div className="text-base font-semibold font-display text-foreground mb-1 hover:text-primary cursor-pointer transition-colors" onClick={(e) => { e.stopPropagation(); if (item.poi_id) { onSpotClick(item.poi_id); } }}>{item.spot}</div>
          <div className="flex gap-2 items-center text-xs text-foreground-secondary">
            <Tag style={{ fontSize: 10, padding: "1px 6px", borderRadius: 2, color: CATEGORY_COLORS[item.category] || "#8B6F4E", background: `${CATEGORY_COLORS[item.category] || "#8B6F4E"}1f`, border: "none" }}>{item.category}</Tag>
            <span>{item.duration}</span>
            <span className="font-bold" style={{ color: item.cost === 0 ? "#6B8E6B" : "#2C1810" }}>{item.cost === 0 ? "免费" : `¥${item.cost}`}</span>
          </div>
          {item.note && <div className="text-xs text-foreground-tertiary mt-1 italic leading-relaxed">{item.note}</div>}
          <button onClick={onReplace} className="mt-1.5 text-[10px] font-mono text-foreground-tertiary hover:text-primary flex items-center gap-0.5 transition-colors no-print">
            <Replace className="w-2.5 h-2.5" />替换景点
          </button>
        </div>
      </div>
    </div>
  );
}

interface ItineraryTimelineProps {
  itinerary: Itinerary;
  onEdit?: (dayIndex: number, newItems: ItineraryItem[]) => void;
}

export default function ItineraryTimeline({ itinerary, onEdit }: ItineraryTimelineProps) {
  const [activeDayIdx, setActiveDayIdx] = useState(0);
  const [replaceModalOpen, setReplaceModalOpen] = useState(false);
  const [replacingSpot, setReplacingSpot] = useState<{ dayIdx: number; spot: ItineraryItem } | null>(null);
  const [poiDetailId, setPoiDetailId] = useState<number | null>(null);
  const [poiDetailOpen, setPoiDetailOpen] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  );

  if (!itinerary || !itinerary.itinerary || itinerary.itinerary.length === 0) return null;

  const totalDays = itinerary.itinerary.length;
  const handlePrev = (e: React.MouseEvent) => { e.stopPropagation(); if (activeDayIdx > 0) setActiveDayIdx(activeDayIdx - 1); };
  const handleNext = (e: React.MouseEvent) => { e.stopPropagation(); if (activeDayIdx < totalDays - 1) setActiveDayIdx(activeDayIdx + 1); };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const dayItems = [...(itinerary.itinerary[activeDayIdx].items || [])];
    const oldIndex = dayItems.findIndex(i => i.spot + i.time === active.id);
    const newIndex = dayItems.findIndex(i => i.spot + i.time === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    const newItems = arrayMove(dayItems, oldIndex, newIndex);
    onEdit?.(activeDayIdx, newItems);
  };

  const handleReplaceClick = (dayIdx: number, spot: ItineraryItem) => {
    setReplacingSpot({ dayIdx, spot });
    setReplaceModalOpen(true);
  };

  const handleReplace = (newSpot: ItineraryItem) => {
    if (!replacingSpot) return;
    const dayItems = [...(itinerary.itinerary[replacingSpot.dayIdx].items || [])];
    const idx = dayItems.findIndex(i => i.spot === replacingSpot.spot.spot && i.time === replacingSpot.spot.time);
    if (idx !== -1) {
      dayItems[idx] = newSpot;
      onEdit?.(replacingSpot.dayIdx, dayItems);
    }
    setReplacingSpot(null);
  };

  return (
    <div className="py-2 flex flex-col h-full justify-between">
      <div className="text-center text-sm md:text-base text-foreground-secondary italic font-display leading-relaxed py-3 border-b border-dashed border-border-light mb-4 select-none">" {itinerary.summary} "</div>

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

              {onEdit && isActive ? (
                <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                  <SortableContext items={(day.items || []).map(i => i.spot + i.time)} strategy={verticalListSortingStrategy}>
                    {(day.items || []).map((item) => (
                      <SortableTimelineItem
                        key={item.spot + item.time}
                        item={item}
                        onReplace={() => handleReplaceClick(idx, item)}
                        onSpotClick={(poiId) => { setPoiDetailId(poiId); setPoiDetailOpen(true); }}
                      />
                    ))}
                  </SortableContext>
                </DndContext>
              ) : (
                <div className="pl-1">
                  {(day.items || []).map((item, i) => (
                    <div key={i} className="flex items-start gap-2 relative pb-4">
                      {/* 时间线圆点 + 连线 */}
                      <div className="flex flex-col items-center mt-1 shrink-0" style={{ width: 16 }}>
                        <div className="w-3 h-3 rounded-full border-2 border-primary bg-background" />
                        {i < (day.items || []).length - 1 && <div className="w-0.5 flex-1 bg-border-light min-h-[20px]" style={{ marginTop: 2 }} />}
                      </div>
                      <div className="flex-1">
                        <div className="text-xs text-foreground-tertiary font-mono mb-0.5">{item.time}</div>
                        <div className="text-base font-semibold font-display text-foreground mb-1 hover:text-primary cursor-pointer transition-colors" onClick={(e) => { e.stopPropagation(); if (item.poi_id) { onSpotClick(item.poi_id); } }}>{item.spot}</div>
                        <div className="flex gap-2 items-center text-xs text-foreground-secondary">
                          <Tag style={{ fontSize: 10, padding: "1px 6px", borderRadius: 2, color: CATEGORY_COLORS[item.category] || "#8B6F4E", background: `${CATEGORY_COLORS[item.category] || "#8B6F4E"}1f`, border: "none" }}>{item.category}</Tag>
                          <span>{item.duration}</span>
                          <span className="font-bold" style={{ color: item.cost === 0 ? "#6B8E6B" : "#2C1810" }}>{item.cost === 0 ? "免费" : `¥${item.cost}`}</span>
                        </div>
                        {item.note && <div className="text-xs text-foreground-tertiary mt-1 italic leading-relaxed">{item.note}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-2 pt-2 border-t border-dashed border-border-light pl-4 text-xs text-foreground-secondary font-mono">
                <span className="text-primary font-bold">●</span> 推荐交通：<strong className="text-foreground">{day.transport}</strong>
              </div>
            </div>
          );
        })}
      </div>

      <div className="text-center pt-2 text-[10px] text-foreground-tertiary font-mono uppercase tracking-widest border-t border-dashed border-border-light mt-2 select-none no-print flex items-center justify-between">
        <span>TRIPCRAFT DAY NAV</span>
        <span className="flex items-center gap-1">
          {onEdit && <span className="text-primary">编辑模式 · 拖拽排序</span>}
          {" · "}
          第 {activeDayIdx + 1} 天 / 共 {totalDays} 天
        </span>
      </div>

      <SpotReplaceModal
        open={replaceModalOpen}
        currentSpot={replacingSpot?.spot || null}
        city={itinerary.destination}
        onClose={() => { setReplaceModalOpen(false); setReplacingSpot(null); }}
        onReplace={handleReplace}
      />

      <PoiDetailModal
        poiId={poiDetailId}
        open={poiDetailOpen}
        onClose={() => setPoiDetailOpen(false)}
      />
    </div>
  );
}