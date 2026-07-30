import React from "react";
import ReactECharts from "echarts-for-react";

const CATEGORY_COLORS = {
  "美食": "#C9622A",
  "自然风光": "#5B8C5A",
  "历史文化": "#8B6F4E",
  "购物": "#B8860B",
  "亲子": "#6B4A8C",
  "交通": "#7A8B99",
};

export default function CostChart({ itinerary, budget }) {
  if (!itinerary) return null;

  // 1. 汇总各类别的花费
  const costByCategory = {};
  
  // 汇总景点门票花费
  itinerary.itinerary?.forEach((day) => {
    day.items?.forEach((item) => {
      const cat = item.category || "自然风光";
      if (!costByCategory[cat]) {
        costByCategory[cat] = 0;
      }
      costByCategory[cat] += item.cost || 0;
    });

    // 汇总每天的交通花费
    // 我们提取 transport 花费，默认从 day_cost 中减去门票，就是交通+餐饮其他（或者为了精确展示，单独把交通费独立出来）
    // 原项目中交通费用包含在 day_cost 里。我们这里为了可视化饱满，把每天的交通费加在“交通”分类里
    // 门票总额
    const itemsTicketSum = day.items?.reduce((sum, item) => sum + (item.cost || 0), 0) || 0;
    const dayTransportAndOther = (day.day_cost || day.dayCost || 0) - itemsTicketSum;
    if (dayTransportAndOther > 0) {
      costByCategory["交通"] = (costByCategory["交通"] || 0) + dayTransportAndOther;
    }
  });

  const pieData = Object.entries(costByCategory).map(([name, value]) => ({
    name,
    value,
    itemStyle: { color: CATEGORY_COLORS[name] || "#8B7355" },
  }));

  const totalCost = itinerary.total_cost || itinerary.totalCost || 0;
  const safeBudget = budget ?? 0;
  const utilization = safeBudget > 0 ? Math.round((totalCost / safeBudget) * 100) : 0;
  const isOverBudget = totalCost > safeBudget;

  // ECharts 配置参数
  const option = {
    tooltip: {
      trigger: "item",
      formatter: "{b}: ¥{c} ({d}%)",
      backgroundColor: "#FFF9F0",
      borderColor: "#D4C5B0",
      textStyle: {
        color: "#2C1810",
        fontFamily: "monospace"
      }
    },
    legend: {
      bottom: 0,
      icon: "circle",
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { fontSize: 11, color: "#5A4032", fontFamily: "sans-serif" },
    },
    series: [
      {
        type: "pie",
        radius: ["40%", "65%"],
        center: ["50%", "42%"],
        label: {
          show: true,
          formatter: "¥{c}",
          fontSize: 11,
          color: "#2C1810",
          fontFamily: "monospace",
          fontWeight: "bold"
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 5,
            shadowColor: "rgba(44, 24, 16, 0.15)",
          },
        },
        data: pieData,
        animationDuration: 600, // 优雅的 600ms 快速渲染
      },
    ],
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center bg-background-secondary border border-border rounded-[2px] p-6">
      
      {/* 饼图区块 */}
      <div>
        <div className="text-xs font-bold text-foreground-secondary uppercase tracking-widest mb-2 font-mono">
          ◇ 花费饼图分布 / Analysis
        </div>
        <ReactECharts 
          option={option} 
          style={{ height: 230 }} 
          opts={{ renderer: 'svg' }} // SVG 渲染更加适合精细印刷风格
        />
      </div>

      {/* 右侧数据汇总表格 */}
      <div className="flex flex-col justify-center">
        
        {/* 总花费大字 */}
        <div className="flex justify-between items-baseline pb-3 border-b-2 border-foreground mb-4">
          <span className="text-sm font-bold text-foreground-secondary uppercase tracking-wider font-mono">
            实际计算总计
          </span>
          <span className="text-3xl font-black font-mono text-primary">
            ¥{(totalCost || 0).toLocaleString()}
          </span>
        </div>

        {/* 预设总预算 */}
        <div className="flex justify-between items-center text-xs font-mono text-foreground-secondary mb-4">
          <span>预设上限预算:</span>
          <span className="font-semibold">¥{(safeBudget || 0).toLocaleString()}</span>
        </div>

        {/* 状态徽章和进度条 */}
        <div className="mb-4">
          <div className="flex items-center gap-2 text-xs font-bold font-mono">
            <span 
              className="w-2.5 h-2.5 rounded-full" 
              style={{ backgroundColor: isOverBudget ? "#B85450" : "#6B8E6B" }}
            />
            <span style={{ color: isOverBudget ? "#B85450" : "#6B8E6B" }}>
              {isOverBudget ? "已超过预设预算" : "在预算合规范围内"}
            </span>
          </div>

          {/* 进度条容器 */}
          <div className="h-2 bg-background-tertiary rounded-full overflow-hidden mt-2.5 border border-border-light">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(utilization, 100)}%`,
                backgroundColor: isOverBudget ? "#B85450" : "#C9622A",
              }}
            />
          </div>
        </div>

        {/* 效率百分比 */}
        <div className="text-center font-mono text-xs text-foreground-tertiary">
          已消耗预算利用率：<strong className="text-foreground-secondary">{utilization}%</strong>
        </div>

      </div>

    </div>
  );
}