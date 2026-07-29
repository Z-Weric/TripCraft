import { useState, useCallback } from "react";
import { Spin, Alert, Tag } from "antd";
import { CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import SearchBar from "./components/SearchBar";
import ItineraryTimeline from "./components/ItineraryTimeline";
import MapView from "./components/MapView";
import CostChart from "./components/CostChart";
import FeedbackBar from "./components/FeedbackBar";
import { generateItinerary, type Itinerary, type Verification, type GenerateRequest } from "./services/api";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [verification, setVerification] = useState<Verification | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastRequest, setLastRequest] = useState<GenerateRequest | null>(null);

  const handleGenerate = useCallback(async (req: GenerateRequest) => {
    setLoading(true);
    setError(null);
    setLastRequest(req);
    try {
      const res = await generateItinerary(req);
      if (res.itinerary.error) {
        setError(res.itinerary.error as string);
        setItinerary(null);
      } else {
        setItinerary(res.itinerary);
        setVerification(res.verification);
      }
    } catch (e: any) {
      setError(e?.message || "生成失败，请检查后端服务是否启动");
    } finally {
      setLoading(false);
    }
  }, []);

  const sectionTitleStyle: React.CSSProperties = {
    fontSize: 15,
    fontWeight: 600,
    color: "#6B5B4A",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    marginBottom: 16,
  };

  return (
    <div style={{ minHeight: "100vh", background: "#FBF7F0" }}>
      {/* 顶栏 */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "20px 32px",
          maxWidth: 800,
          margin: "0 auto",
          borderBottom: "1px solid #E8DCC8",
          gap: 16,
        }}
      >
        <div
          style={{
            fontSize: 22,
            fontWeight: 700,
            fontFamily: "Georgia, Songti SC, serif",
            letterSpacing: "0.04em",
          }}
        >
          Trip<span style={{ color: "#C9622A" }}>Craft</span>
        </div>
        {itinerary && (
          <div style={{ fontSize: 13, color: "#8B7B6A" }}>
            {itinerary.days} 天{itinerary.destination} · 预算 ¥{lastRequest?.budget}
          </div>
        )}
        <a
          href="#"
          style={{
            fontSize: 13,
            color: "#6B5B4A",
            textDecoration: "none",
            borderBottom: "1px solid #D4C4A8",
            paddingBottom: 1,
          }}
        >
          GitHub
        </a>
      </header>

      <div style={{ maxWidth: 800, margin: "0 auto", padding: "0 32px" }}>
        {/* 搜索栏 */}
        <section style={{ paddingTop: 40, paddingBottom: 32 }}>
          <SearchBar onGenerate={handleGenerate} loading={loading} />
        </section>

        {/* 加载中 */}
        {loading && (
          <div style={{ textAlign: "center", padding: "48px 0" }}>
            <Spin size="large" tip="生成中..." />
          </div>
        )}

        {/* 错误 */}
        {error && (
          <Alert
            type="warning"
            message={error}
            showIcon
            style={{ marginBottom: 24, borderRadius: 2 }}
          />
        )}

        {/* 结果 */}
        {itinerary && !loading && (
          <>
            {/* 验证徽章 */}
            {verification && (
              <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 24 }}>
                <Tag
                  icon={verification.spots_valid ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                  color={verification.spots_valid ? "success" : "error"}
                  style={{ fontSize: 12, padding: "2px 8px" }}
                >
                  景点真实性 {verification.spots_valid ? "通过" : "未通过"} ({verification.spots_verified}/{verification.spots_total})
                </Tag>
                <Tag
                  icon={verification.budget_valid ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                  color={verification.budget_valid ? "success" : "error"}
                  style={{ fontSize: 12, padding: "2px 8px" }}
                >
                  预算 {verification.budget_valid ? "合规" : "超支"}
                </Tag>
                <Tag
                  icon={verification.route_valid ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                  color={verification.route_valid ? "success" : "error"}
                  style={{ fontSize: 12, padding: "2px 8px" }}
                >
                  路线 {verification.route_valid ? "合理" : "需调整"}
                </Tag>
              </div>
            )}

            {/* 行程时间轴 */}
            <section style={{ paddingBottom: 32 }}>
              <ItineraryTimeline itinerary={itinerary} />
            </section>

            {/* 地图 */}
            <section style={{ paddingBottom: 32 }}>
              <div style={sectionTitleStyle}>路线地图</div>
              <MapView itinerary={itinerary} />
            </section>

            {/* 花费分析 */}
            <section style={{ paddingBottom: 32 }}>
              <div style={sectionTitleStyle}>花费分析</div>
              <div
                style={{
                  background: "#FFFFFF",
                  border: "1px solid #E8DCC8",
                  borderRadius: 2,
                  padding: 24,
                }}
              >
                <CostChart itinerary={itinerary} budget={lastRequest?.budget || 2000} />
              </div>
            </section>

            {/* 反馈 */}
            <section style={{ paddingBottom: 48 }}>
              <FeedbackBar
                destination={lastRequest?.destination || ""}
                days={lastRequest?.days || 3}
                budget={lastRequest?.budget || 2000}
                preferences={lastRequest?.preferences || []}
                onRegenerate={() => lastRequest && handleGenerate(lastRequest)}
              />
            </section>
          </>
        )}

        {/* 空状态 */}
        {!itinerary && !loading && !error && (
          <div
            style={{
              textAlign: "center",
              padding: "48px 0",
              color: "#8B7B6A",
              fontSize: 15,
              fontStyle: "italic",
            }}
          >
            输入目的地、天数、预算和偏好，生成你的专属行程
          </div>
        )}
      </div>
    </div>
  );
}