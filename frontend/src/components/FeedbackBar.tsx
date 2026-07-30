import { useState } from "react";
import { Button, Space, Input, Modal, message } from "antd";
import { ThumbsUp, ThumbsDown, RotateCcw, FileDown } from "lucide-react";
import { submitFeedback } from "../services/api";

interface FeedbackBarProps {
  destination: string;
  days: number;
  budget: number;
  preferences: string[];
  onRegenerate: () => void;
}

export default function FeedbackBar({ destination, days, budget, preferences, onRegenerate }: FeedbackBarProps) {
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [comment, setComment] = useState("");

  const handleFeedback = async (type: "useful" | "improve") => {
    if (type === "improve") { setModalOpen(true); return; }
    setLoading(true);
    try {
      await submitFeedback({ destination, days, budget, preferences, feedback_type: "useful" });
      message.success("感谢反馈！已标记为：很有用");
    } catch { message.error("提交失败"); }
    finally { setLoading(false); }
  };

  const handleImproveSubmit = async () => {
    setLoading(true); setModalOpen(false);
    try {
      await submitFeedback({ destination, days, budget, preferences, feedback_type: "improve", comment });
      message.success("感谢反馈！意见已录入系统");
      setComment("");
    } catch { message.error("提交失败"); }
    finally { setLoading(false); }
  };

  return (
    <div className="flex justify-center py-6 border-t border-dashed border-border-light no-print">
      <Space size={16} wrap className="justify-center">
        <Button icon={<ThumbsUp className="w-4 h-4 text-success inline mr-1" />} onClick={() => handleFeedback("useful")} loading={loading}
          className="h-10 border-border hover:border-success hover:text-success rounded-sm font-mono font-bold">很有用</Button>
        <Button icon={<ThumbsDown className="w-4 h-4 text-error inline mr-1" />} onClick={() => handleFeedback("improve")} loading={loading}
          className="h-10 border-border hover:border-error hover:text-error rounded-sm font-mono font-bold">需改进</Button>
        <Button icon={<RotateCcw className="w-4 h-4 inline mr-1" />} onClick={onRegenerate}
          className="h-10 bg-primary border-primary hover:bg-primary-dark text-white rounded-sm font-mono font-bold">重新生成</Button>
        <Button icon={<FileDown className="w-4 h-4 inline mr-1" />} onClick={() => window.print()}
          className="h-10 border-border-dark text-foreground hover:border-primary hover:text-primary rounded-sm font-mono font-bold">导出/打印</Button>
      </Space>
      <Modal title={<span className="font-display font-bold text-lg">提供改进意见</span>} open={modalOpen} onOk={handleImproveSubmit} onCancel={() => setModalOpen(false)}
        okText="提交意见" cancelText="取消" okButtonProps={{ className: "bg-primary border-primary" }}>
        <div className="py-3">
          <p className="text-xs text-foreground-secondary mb-3 font-mono">请告诉我们您觉得生成的计划有何不足？这可以帮助微调算法进一步校准。</p>
          <Input.TextArea rows={4} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="请输入您的意见和建议..." />
        </div>
      </Modal>
    </div>
  );
}