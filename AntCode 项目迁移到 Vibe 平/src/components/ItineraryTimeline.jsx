import React, { useState } from "react";
import { Timeline, Tag } from "antd";
import { ChevronLeft, ChevronRight, CalendarRange } from "lucide-react";

const CATEGORY_COLORS = {
  "自然风光": "#5B8C5A",
  "美食": "#C9622A",
  "历史文化": "#8B6F4E",
  "购物": "#B8860B",
  "亲子": "#6B4A8C",
};

export default function ItineraryTimeline({ itinerary }) {
  const [activeDayIdx, setActiveDayIdx] = useState(0);

  if (!itinerary || !itinerary.itinerary || itinerary.itinerary.length === 0) return null;

  const totalDays = itinerary.itinerary.length;
  const currentDayData = itinerary.itinerary[activeDayIdx];

  const handlePrevDay = (e) => {
    e.stopPropagation();
    if (activeDayIdx > 0) {
      setActiveDayIdx(activeDayIdx - 1);
    }
  };

  const handleNextDay = (e) => {
    e.stopPropagation();
    if (activeDayIdx < totalDays - 1) {
      setActiveDayIdx(activeDayIdx + 1);
    }
  };

  return (
    <div className="py-2 flex flex-col h-full justify-between">
      {/* 行程一句话精彩摘要 - 杂志式斜体 */}
      <div className="text-center text-sm md:text-base text-foreground-secondary italic font-display leading-relaxed py-3 max-w-2xl mx-auto border-b border-dashed border-border-light mb-4 select-none">
        “ {itinerary.summary} ”
      </div>

      {/* 按天分明信片 - 顶部天数导航 Tabs (no-print) */}
      <div className="day-tab-navigation flex items-center justify-between gap-2 border-b border-border-dark pb-2 mb-4 select-none no-print">
        {/* 极简左切换 */}
        <button
          onClick={handlePrevDay}
          disabled={activeDayIdx === 0}
          className={`p-1 border border-border-dark rounded-[1px] transition-all active:scale-95 ${
            activeDayIdx === 0 
              ? "opacity-30 cursor-not-allowed" 
              : "hover:bg-primary/5 hover:text-primary text-foreground"
          }`}
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {/* 横向滚动的天数 Tab 栏 */}
        <div className="flex-1 flex gap-2 overflow-x-auto px-2 scrollbar-none justify-center">
          {itinerary.itinerary.map((day, idx) => (
            <button
              key={day.day}
              onClick={(e) => {
                e.stopPropagation();
                setActiveDayIdx(idx);
              }}
              className={`flex-shrink-0 px-3 py-1 font-mono text-xs font-bold border rounded-[2px] transition-all relative ${
                activeDayIdx === idx
                  ? "bg-primary text-background-secondary border-primary scale-105 shadow-sm"
                  : "bg-background-tertiary text-foreground-secondary border-border hover:border-border-dark hover:text-foreground hover:-translate-y-0.5"
              }`}
            >
              Day {day.day}
            </button>
          ))}
        </div>

        {/* 极简右切换 */}
        <button
          onClick={handleNextDay}
          disabled={activeDayIdx === totalDays - 1}
          className={`p-1 border border-border-dark rounded-[1px] transition-all active:scale-95 ${
            activeDayIdx === totalDays - 1 
              ? "opacity-30 cursor-not-allowed" 
              : "hover:bg-primary/5 hover:text-primary text-foreground"
          }`}
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* 滚动时间线容器（交互态限制高度，防止拉长撑爆页面；打印态取消限制） */}
      <div className="timeline-scroll-container flex-1 overflow-y-auto custom-scroll pr-1 max-h-[320px] md:max-h-[340px]">
        
        {/* 遍历渲染所有天 (使用 CSS 控制非 active 隐藏，但在打印时强行全部块状显示) */}
        {itinerary.itinerary.map((day, idx) => {
          const isActive = idx === activeDayIdx;
          
          return (
            <div 
              key={day.day} 
              className={`day-block-item mb-4 ${isActive ? "block" : "hidden"} print:block print:mb-8 print:break-inside-avoid`}
            >
              {/* 日标标题：复古明信片印刷格式 */}
              <div className="flex items-baseline justify-between pb-1 border-b border-foreground mb-4 select-none">
                <span className="text-xl font-black font-display tracking-tight text-foreground flex items-center gap-2">
                  <span className="text-xs font-bold uppercase font-mono tracking-widest text-primary">Day</span>
                  <span>{day.day}</span>
                </span>
                <span className="text-sm font-bold font-mono text-primary">
                  预计消费: ¥{(day.day_cost || day.dayCost || 0).toLocaleString()}
                </span>
              </div>

              {/* 核心时间线轨迹 */}
              <Timeline
                className="custom-timeline"
                items={day.items && day.items.map((item, idx) => {
                  const catColor = CATEGORY_COLORS[item.category] || "#8B6F4E";
                  return {
                    color: "#C9622A",
                    children: (
                      <div className="pb-4 hover:translate-x-0.5 transition-transform duration-200">
                        {/* 时间和时段 */}
                        <div className="text-[10px] font-mono font-bold text-foreground-tertiary tracking-widest mb-0.5">
                          ◇ {item.time} ({item.duration})
                        </div>
                        
                        {/* 景点大字 */}
                        <div className="text-sm font-bold font-display text-foreground tracking-tight mb-1">
                          {item.spot}
                        </div>

                        {/* 门票分类、时长和单门票花费 */}
                        <div className="flex flex-wrap items-center gap-2 text-[10px] text-foreground-secondary font-mono leading-none">
                          <span 
                            className="px-1.5 py-0.5 rounded-[1px] text-[9px] uppercase font-bold tracking-wider"
                            style={{
                              color: catColor,
                              backgroundColor: `${catColor}14`,
                              border: `1px solid ${catColor}2a`
                            }}
                          >
                            {item.category}
                          </span>
                          <span className="text-foreground-tertiary">|</span>
                          <span>游玩: {item.duration}</span>
                          <span className="text-foreground-tertiary">|</span>
                          <span className={`font-bold ${item.cost === 0 ? "text-success" : "text-foreground"}`}>
                            {item.cost === 0 ? "免门票" : `门票 ¥${item.cost}`}
                          </span>
                        </div>

                        {/* 游玩贴士/小注 */}
                        {item.note && (
                          <div className="mt-1.5 p-2 bg-background-secondary border-l-2 border-primary-light text-[11px] text-foreground-secondary italic leading-normal rounded-r-[1px]">
                            {item.note}
                          </div>
                        )}
                      </div>
                    )
                  };
                })}
              />

              {/* 交通方式说明 */}
              <div className="mt-2 pt-2 border-t border-dashed border-border-light pl-4 text-xs text-foreground-secondary font-mono flex items-center gap-1.5">
                <span className="text-primary font-bold">●</span>
                <span>推荐交通：<strong className="text-foreground">{day.transport}</strong></span>
              </div>
            </div>
          );
        })}

      </div>

      {/* 底部天数指示 (no-print) */}
      <div className="text-center pt-2 text-[10px] text-foreground-tertiary font-mono uppercase tracking-widest border-t border-dashed border-border-light mt-2 select-none no-print flex items-center justify-between">
        <span>TRIPCRAFT DAY NAV</span>
        <span>第 {activeDayIdx + 1} 天 / 共 {totalDays} 天</span>
      </div>

      {/* 覆盖 Timeline 样式与打印自适应 */}
      <style>{`
        .custom-timeline .ant-timeline-item-tail {
          border-left: 1px dashed #E8DFD0 !important;
        }
        .custom-timeline .ant-timeline-item-head {
          background-color: #FBF7F0 !important;
          border-color: #C9622A !important;
          border-width: 1.5px !important;
          width: 8px !important;
          height: 8px !important;
        }
        
        /* 局部自定义精致滚动条 */
        .custom-scroll::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scroll::-webkit-scrollbar-thumb {
          background-color: #C9622A;
          border-radius: 2px;
        }
        .custom-scroll::-webkit-scrollbar-track {
          background: transparent;
        }

        /* 隐藏 Tab 滚动条 */
        .scrollbar-none::-webkit-scrollbar {
          display: none;
        }
        .scrollbar-none {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }

        /* 打印模式全天铺开 */
        @media print {
          .day-block-item {
            display: block !important;
          }
          .day-tab-navigation, .no-print {
            display: none !important;
          }
          .timeline-scroll-container {
            max-height: none !important;
            overflow: visible !important;
            padding-right: 0 !important;
          }
        }
      `}</style>
    </div>
  );
}