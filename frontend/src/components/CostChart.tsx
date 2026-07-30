import ReactECharts from "echarts-for-react";
import type { Itinerary } from "../services/api";

const CATEGORY_COLORS: Record<string, string> = {
  "美食": "#C9622A", "自然风光": "#5B8C5A", "历史文化": "#8B6F4E", "购物": "#B8860B", "亲子": "#6B4A8C", "交通": "#7A8B99",
};

export default function CostChart({ itinerary, budget }: { itinerary: Itinerary; budget: number }) {
  if (!itinerary) return null;

  const costByCategory: Record<string, number> = {};
  itinerary.itinerary?.forEach((day) => {
    day.items?.forEach((item) => {
      const cat = item.category || "自然风光";
      costByCategory[cat] = (costByCategory[cat] || 0) + (item.cost || 0);
    });
    const itemsTicketSum = day.items?.reduce((s, i) => s + (i.cost || 0), 0) || 0;
    const transportCost = (day.day_cost || 0) - itemsTicketSum;
    if (transportCost > 0) costByCategory["交通"] = (costByCategory["交通"] || 0) + transportCost;
  });

  const pieData = Object.entries(costByCategory).map(([name, value]) => ({ name, value, itemStyle: { color: CATEGORY_COLORS[name] || "#8B7355" } }));
  const totalCost = itinerary.total_cost || 0;
  const utilization = budget > 0 ? Math.round((totalCost / budget) * 100) : 0;
  const isOverBudget = totalCost > budget;

  const option = {
    tooltip: { trigger: "item", formatter: "{b}: ¥{c} ({d}%)", backgroundColor: "#FFF9F0", borderColor: "#D4C5B0", textStyle: { color: "#2C1810", fontFamily: "monospace" } },
    legend: { bottom: 0, icon: "circle", itemWidth: 10, itemHeight: 10, textStyle: { fontSize: 11, color: "#5A4032" } },
    series: [{
      type: "pie", radius: ["40%", "65%"], center: ["50%", "42%"],
      label: { show: true, formatter: "¥{c}", fontSize: 11, color: "#2C1810", fontWeight: "bold" },
      emphasis: { itemStyle: { shadowBlur: 5, shadowColor: "rgba(44, 24, 16, 0.15)" } },
      data: pieData, animationDuration: 600,
    }],
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center bg-background-secondary border border-border rounded-sm p-6">
      <div>
        <div className="text-xs font-bold text-foreground-secondary uppercase tracking-widest mb-2 font-mono">◇ 花费饼图分布</div>
        <ReactECharts option={option} style={{ height: 230 }} opts={{ renderer: 'svg' }} />
      </div>
      <div className="flex flex-col justify-center">
        <div className="flex justify-between items-baseline pb-3 border-b-2 border-foreground mb-4">
          <span className="text-sm font-bold text-foreground-secondary uppercase tracking-wider font-mono">实际总计</span>
          <span className="text-3xl font-black font-mono text-primary">¥{totalCost.toLocaleString()}</span>
        </div>
        <div className="flex justify-between text-xs font-mono text-foreground-secondary mb-4">
          <span>预设预算:</span><span className="font-semibold">¥{budget.toLocaleString()}</span>
        </div>
        <div className="mb-4">
          <div className="flex items-center gap-2 text-xs font-bold font-mono">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: isOverBudget ? "#B85450" : "#6B8E6B" }} />
            <span style={{ color: isOverBudget ? "#B85450" : "#6B8E6B" }}>{isOverBudget ? "已超过预算" : "在预算范围内"}</span>
          </div>
          <div className="h-2 bg-background-tertiary rounded-full overflow-hidden mt-2.5 border border-border-light">
            <div className="h-full rounded-full transition-all duration-500" style={{ width: `${Math.min(utilization, 100)}%`, backgroundColor: isOverBudget ? "#B85450" : "#C9622A" }} />
          </div>
        </div>
        <div className="text-center font-mono text-xs text-foreground-tertiary">预算利用率：<strong className="text-foreground-secondary">{utilization}%</strong></div>
      </div>
    </div>
  );
}