import { Button, Space, message } from "antd";
import { LikeOutlined, DislikeOutlined, ReloadOutlined, FilePdfOutlined } from "@ant-design/icons";
import { useState } from "react";
import { submitFeedback } from "../services/api";

interface FeedbackBarProps {
  destination: string;
  days: number;
  budget: number;
  preferences: string[];
  onRegenerate: () => void;
}

export default function FeedbackBar({
  destination,
  days,
  budget,
  preferences,
  onRegenerate,
}: FeedbackBarProps) {
  const [loading, setLoading] = useState(false);

  const handleFeedback = async (type: "useful" | "improve") => {
    setLoading(true);
    try {
      await submitFeedback({
        destination,
        days,
        budget,
        preferences,
        feedback_type: type,
      });
      message.success(type === "useful" ? '感谢反馈！已记录"有用"' : "感谢反馈！请告诉我们哪里需要改进");
    } catch {
      message.error("反馈提交失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", gap: 12, flexWrap: "wrap" }}>
      <Space size={12}>
        <Button
          icon={<LikeOutlined />}
          onClick={() => handleFeedback("useful")}
          loading={loading}
          style={{ borderRadius: 2 }}
        >
          有用
        </Button>
        <Button
          icon={<DislikeOutlined />}
          onClick={() => handleFeedback("improve")}
          loading={loading}
          style={{ borderRadius: 2 }}
        >
          需改进
        </Button>
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          onClick={onRegenerate}
          style={{ background: "#C9622A", borderColor: "#C9622A", borderRadius: 2 }}
        >
          重新生成
        </Button>
        <Button
          icon={<FilePdfOutlined />}
          onClick={() => message.info("正在导出 PDF...")}
          style={{ borderRadius: 2 }}
        >
          导出 PDF
        </Button>
      </Space>
    </div>
  );
}