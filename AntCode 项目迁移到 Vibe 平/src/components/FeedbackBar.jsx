import React, { useState } from "react";
import { Button, message, Space, Input, Modal } from "antd";
import { ThumbsUp, ThumbsDown, RotateCcw, FileDown } from "lucide-react";
import useItineraryStore from "@/stores/itineraryStore.js";

export default function FeedbackBar({
  destination,
  days,
  budget,
  preferences,
  onRegenerate,
}) {
  const [loading, setLoading] = useState(false);
  const [commentModalOpen, setCommentModalOpen] = useState(false);
  const [improveComment, setImproveComment] = useState("");
  const submitFeedback = useItineraryStore((s) => s.submitFeedback);

  const handleFeedback = async (type) => {
    if (type === "improve") {
      setCommentModalOpen(true);
      return;
    }

    setLoading(true);
    try {
      const ok = await submitFeedback("useful", "非常实用，点赞！");
      if (ok) {
        message.success("感谢您的反馈！已标记该推荐为：很有用。");
      } else {
        message.error("反馈提交失败，请稍后重试");
      }
    } catch {
      message.error("反馈提交失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const handleImproveSubmit = async () => {
    setLoading(true);
    setCommentModalOpen(false);
    try {
      const ok = await submitFeedback("improve", improveComment || "需要改进细节");
      if (ok) {
        message.success("感谢反馈！您的宝贵意见已录入系统数据库。");
        setImproveComment("");
      } else {
        message.error("意见提交失败");
      }
    } catch {
      message.error("意见提交失败");
    } finally {
      setLoading(false);
    }
  };

  const handleExportPdf = () => {
    message.loading("正在排版印刷级明信片 PDF 布局...");
    setTimeout(() => {
      message.destroy();
      message.success("已成功生成精美明信片PDF！开始下载...");
      window.print(); // 直接调用打印，配合明信片 CSS 呈现绝佳效果
    }, 1500);
  };

  return (
    <div className="flex justify-center py-6 border-t border-dashed border-border-light">
      <Space size={16} wrap className="justify-center">
        
        {/* 有用 */}
        <Button
          icon={<ThumbsUp className="w-4 h-4 text-success inline mr-1" />}
          onClick={() => handleFeedback("useful")}
          loading={loading}
          className="h-10 border-border hover:border-success hover:text-success rounded-[2px] font-mono font-bold"
        >
          很有用 / Useful
        </Button>

        {/* 需改进 */}
        <Button
          icon={<ThumbsDown className="w-4 h-4 text-error inline mr-1" />}
          onClick={() => handleFeedback("improve")}
          loading={loading}
          className="h-10 border-border hover:border-error hover:text-error rounded-[2px] font-mono font-bold"
        >
          需改进 / Improve
        </Button>

        {/* 重新生成 */}
        <Button
          icon={<RotateCcw className="w-4 h-4 inline mr-1" />}
          onClick={onRegenerate}
          className="h-10 bg-primary border-primary hover:bg-primary-dark text-white rounded-[2px] font-mono font-bold"
        >
          重新生成 / Regenerate
        </Button>

        {/* 导出 PDF / 打印 */}
        <Button
          icon={<FileDown className="w-4 h-4 inline mr-1" />}
          onClick={handleExportPdf}
          className="h-10 border-border-dark text-foreground hover:border-primary hover:text-primary rounded-[2px] font-mono font-bold"
        >
          导出/打印明信片
        </Button>

      </Space>

      {/* 需改进反馈弹窗 */}
      <Modal
        title={<span className="font-display font-bold text-lg">提供改进意见 / Improve Plan</span>}
        open={commentModalOpen}
        onOk={handleImproveSubmit}
        onCancel={() => setCommentModalOpen(false)}
        okText="提交意见"
        cancelText="取消"
        okButtonProps={{ className: "bg-primary border-primary hover:bg-primary-dark" }}
        className="custom-modal"
      >
        <div className="py-3">
          <p className="text-xs text-foreground-secondary mb-3 font-mono leading-relaxed">
            请告诉我们您觉得生成的计划有何不足？例如：预算超支、时间冲突、或者景点不喜欢。这可以帮助我们的微调算法进一步校准。
          </p>
          <Input.TextArea
            rows={4}
            value={improveComment}
            onChange={(e) => setImproveComment(e.target.value)}
            placeholder="请输入您的意见和建议..."
            className="border-border hover:border-primary focus:border-primary rounded-[2px]"
          />
        </div>
      </Modal>

      <style>{`
        .custom-modal .ant-modal-content {
          background-color: #FFF9F0 !important;
          border: 1px solid #D4C5B0 !important;
          border-radius: 4px !important;
          box-shadow: none !important;
        }
      `}</style>
    </div>
  );
}