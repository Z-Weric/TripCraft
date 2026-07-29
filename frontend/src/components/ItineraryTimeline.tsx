import { Timeline, Tag } from "antd";
import type { Itinerary } from "../services/api";

const CATEGORY_COLORS: Record<string, string> = {
  "自然风光": "#5B8C5A",
  "美食": "#C9622A",
  "历史文化": "#8B6F4E",
  "购物": "#B8860B",
};

interface ItineraryTimelineProps {
  itinerary: Itinerary;
}

export default function ItineraryTimeline({ itinerary }: ItineraryTimelineProps) {
  return (
    <div>
      {/* 摘要 */}
      <div
        style={{
          textAlign: "center",
          fontSize: 16,
          color: "#6B5B4A",
          fontStyle: "italic",
          fontFamily: "Georgia, Songti SC, serif",
          margin: "24px 0",
          lineHeight: 1.8,
        }}
      >
        {itinerary.summary}
      </div>

      {/* 每日行程 */}
      {itinerary.itinerary.map((day) => (
        <div key={day.day} style={{ marginBottom: 48 }}>
          {/* 日标题 */}
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              justifyContent: "space-between",
              paddingBottom: 12,
              borderBottom: "2px solid #2C2418",
              marginBottom: 24,
            }}
          >
            <span
              style={{
                fontSize: 28,
                fontWeight: 700,
                fontFamily: "Georgia, Songti SC, serif",
              }}
            >
              Day {day.day}
            </span>
            <span
              style={{
                fontSize: 15,
                color: "#C9622A",
                fontWeight: 600,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              ¥{day.day_cost}
            </span>
          </div>

          {/* 时间轴 */}
          <Timeline
            items={day.items.map((item) => ({
              color: "#C9622A",
              children: (
                <div>
                  <div
                    style={{
                      fontSize: 12,
                      color: "#8B7B6A",
                      fontFamily: "SF Mono, Roboto Mono, monospace",
                      marginBottom: 2,
                    }}
                  >
                    {item.time}
                  </div>
                  <div
                    style={{
                      fontSize: 18,
                      fontWeight: 600,
                      fontFamily: "Georgia, Songti SC, serif",
                      marginBottom: 4,
                    }}
                  >
                    {item.spot}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: 12,
                      fontSize: 13,
                      color: "#6B5B4A",
                      alignItems: "center",
                    }}
                  >
                    <Tag
                      style={{
                        fontSize: 11,
                        padding: "2px 8px",
                        borderRadius: 2,
                        color: CATEGORY_COLORS[item.category] || "#8B6F4E",
                        background: `${CATEGORY_COLORS[item.category] || "#8B6F4E"}1f`,
                        border: "none",
                      }}
                    >
                      {item.category}
                    </Tag>
                    <span>{item.duration}</span>
                    <span
                      style={{
                        fontWeight: 600,
                        color: item.cost === 0 ? "#5B8C5A" : "#2C2418",
                      }}
                    >
                      {item.cost === 0 ? "免费" : `¥${item.cost}`}
                    </span>
                  </div>
                  {item.note && (
                    <div
                      style={{
                        fontSize: 13,
                        color: "#8B7B6A",
                        marginTop: 4,
                        lineHeight: 1.6,
                        fontStyle: "italic",
                      }}
                    >
                      {item.note}
                    </div>
                  )}
                </div>
              ),
            }))}
          />

          {/* 交通 */}
          <div
            style={{
              fontSize: 13,
              color: "#6B5B4A",
              marginTop: 8,
              paddingTop: 8,
              borderTop: "1px dashed #E8DCC8",
              paddingLeft: 28,
            }}
          >
            交通：{day.transport}
          </div>
        </div>
      ))}
    </div>
  );
}