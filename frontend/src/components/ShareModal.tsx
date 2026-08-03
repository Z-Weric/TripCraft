import { useState } from "react";
import { Modal, message, Tabs } from "antd";
import { Link as LinkIcon, Copy, Download } from "lucide-react";
import { createShareLink, exportTrip } from "../services/api";

interface ShareModalProps {
  open: boolean;
  tripId: number | null;
  onClose: () => void;
}

export default function ShareModal({ open, tripId, onClose }: ShareModalProps) {
  const [shareUrl, setShareUrl] = useState("");
  const [loading, setLoading] = useState(false);

  const handleCreateLink = async () => {
    if (!tripId) return;
    setLoading(true);
    try {
      const res = await createShareLink(tripId);
      const fullUrl = `${window.location.origin}${res.url}`;
      setShareUrl(fullUrl);
      message.success("分享链接已生成");
    } catch {
      message.error("生成分享链接失败");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(shareUrl);
    message.success("已复制到剪贴板");
  };

  const handleExport = async (format: "json" | "markdown") => {
    if (!tripId) return;
    try {
      const res = await exportTrip(tripId, format);
      const blob = new Blob([res.content], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `tripcraft-${tripId}.${format === "markdown" ? "md" : "json"}`;
      a.click();
      URL.revokeObjectURL(url);
      message.success(`已导出 ${format === "markdown" ? "Markdown" : "JSON"} 文件`);
    } catch {
      message.error("导出失败");
    }
  };

  return (
    <Modal
      title={<span className="font-display font-bold text-lg flex items-center gap-2"><LinkIcon className="w-4 h-4 text-primary" />分享行程</span>}
      open={open}
      onCancel={onClose}
      footer={null}
      width={460}
    >
      <Tabs
        items={[
          {
            key: "link",
            label: "分享链接",
            children: (
              <div className="py-2">
                <p className="text-xs text-foreground-secondary mb-3 font-mono">生成短链，任何人可通过链接查看你的行程明信片（只读模式）</p>
                {!shareUrl ? (
                  <button onClick={handleCreateLink} disabled={loading}
                    className="w-full h-10 bg-primary text-white font-bold rounded-sm hover:bg-primary-dark transition-all flex items-center justify-center gap-2">
                    <LinkIcon className="w-4 h-4" />{loading ? "生成中..." : "生成分享链接"}
                  </button>
                ) : (
                  <div className="flex gap-2">
                    <input readOnly value={shareUrl}
                      className="flex-1 h-10 px-3 text-xs font-mono border border-border rounded-sm bg-background-tertiary" />
                    <button onClick={handleCopy}
                      className="h-10 px-4 border border-primary text-primary rounded-sm hover:bg-primary/5 transition-all flex items-center gap-1 text-xs font-mono font-bold">
                      <Copy className="w-3.5 h-3.5" />复制
                    </button>
                  </div>
                )}
              </div>
            ),
          },
          {
            key: "export",
            label: "导出文件",
            children: (
              <div className="py-2 space-y-3">
                <p className="text-xs text-foreground-secondary mb-3 font-mono">导出行程文件，可离线保存或分享</p>
                <div className="flex gap-3">
                  <button onClick={() => handleExport("markdown")}
                    className="flex-1 h-10 border border-border rounded-sm hover:border-primary hover:text-primary transition-all flex items-center justify-center gap-2 text-xs font-mono font-bold">
                    <Download className="w-3.5 h-3.5" />Markdown
                  </button>
                  <button onClick={() => handleExport("json")}
                    className="flex-1 h-10 border border-border rounded-sm hover:border-primary hover:text-primary transition-all flex items-center justify-center gap-2 text-xs font-mono font-bold">
                    <Download className="w-3.5 h-3.5" />JSON
                  </button>
                </div>
              </div>
            ),
          },
        ]}
      />
    </Modal>
  );
}