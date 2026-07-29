import ReactECharts from "echarts-for-react";
import type { Itinerary } from "../services/api";

const CATEGORY_COLORS: Record<string, string> = {
  "美食": "#C9622A",
  "自然风光": "#5B8C5A",
  "历史文化": "#8B6F4E",
  "购物": "#B8860B",
};

interface CostChartProps {
  itinerary: Itinerary;
  budget: number;
}

export default function CostChart({ itinerary, budget }: CostChartProps) {
  // 按分类汇总花费
  const costByCategory: Record<string, number> = {};
  itinerary.itinerary.forEach((day) => {
    day.items.forEach((item) => {
      if (!costByCategory[item.category]) {
        costByCategory[item.category] = 0;
      }
      costByCategory[item.category] += item.cost;
    });
  });

  const pieData = Object.entries(costByCategory).map(([name, value]) => ({
    name,
    value,
    itemStyle: { color: CATEGORY_COLORS[name] || "#8B6F4E" },
  }));

  const utilization = budget > 0 ? Math.round((itinerary.total_cost / budget) * 100) : 0;

  const option = {
    tooltip: {
      trigger: "item",
      formatter: "{b}: ¥{c} ({d}%)",
    },
    legend: {
      bottom: 0,
      textStyle: { fontSize: 12, color: "#6B5B4A" },
    },
    series: [
      {
        type: "pie",
        radius: ["40%", "65%"],
        center: ["50%", "40%"],
        label: {
          show: true,
          formatter: "¥{c}",
          fontSize: 13,
          color: "#2C2418",
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: "rgba(0, 0, 0, 0.2)",
          },
        },
        data: pieData,
        animationDuration: 600,
      },
    ],
  };

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 32,
        alignItems: "center",
      }}
    >
      {/* 饼图 */}
      <div>
        <div
          style={{
            fontSize: 15,
            fontWeight: 600,
            color: "#6B5B4A",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: 16,
          }}
        >
          花费分布
        </div>
        <ReactECharts option={option} style={{ height: 240 }} />
      </div>

      {/* 汇总 */}
      <div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            paddingBottom: 8,
            borderBottom: "2px solid #2C2418",
          }}
        >
          <span style={{ fontSize: 14, fontWeight: 600 }}>总计</span>
          <span
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: "#C9622A",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            ¥{itinerary.total_cost.toLocaleString()}
          </span>
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 13,
            color: "#6B5B4A",
            marginTop: 8,
          }}
        >
          <span>预算</span>
          <span style={{ fontVariantNumeric: "tabular-nums" }}>¥{budget.toLocaleString()}</span>
        </div>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 13,
            fontWeight: 600,
            color: itinerary.total_cost <= budget ? "#5B8C5A" : "#C9622A",
            marginTop: 8,
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: itinerary.total_cost <= budget ? "#5B8C5A" : "#C9622A",
              display: "inline-block",
            }}
          />
          {itinerary.total_cost <= budget ? "预算内" : "已超支"}
        </div>
        {/* 利用率进度条 */}
        <div
          style={{
            height: 6,
            background: "#FBF7F0",
            borderRadius: 3,
            overflow: "hidden",
            marginTop: 8,
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${Math.min(utilization, 100)}%`,
              background: "#C9622A",
              borderRadius: 3,
              transition: "width 0.6s ease",
            }}
          />
        </div>
        <div
          style={{
            fontSize: 12,
            color: "#8B7B6A",
            textAlign: "center",
            marginTop: 4,
          }}
        >
          预算利用率 {utilization}%
        </div>
      </div>
    </div>
  );
}