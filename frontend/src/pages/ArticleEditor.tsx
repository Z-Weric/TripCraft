import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Spin, message, Button } from "antd";
import { ArrowLeft, Edit3, Eye, FileText, Share2, Download } from "lucide-react";
import MarkdownRenderer from "../components/MarkdownRenderer";
import PostcardFlipCard from "../components/PostcardFlipCard";
import { generateArticle, type Itinerary } from "../services/api";

export default function ArticleEditor() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [article, setArticle] = useState("");
  const [mode, setMode] = useState<"preview" | "edit">("preview");
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [packedItems, setPackedItems] = useState<string[]>([]);

  useEffect(() => {
    // 从 sessionStorage 获取行程数据
    const tripJson = sessionStorage.getItem("article-itinerary");
    const itemsJson = sessionStorage.getItem("article-items");
    if (!tripJson) {
      message.error("没有行程数据");
      navigate("/home");
      return;
    }
    const trip = JSON.parse(tripJson) as Itinerary;
    setItinerary(trip);
    setPackedItems(itemsJson ? JSON.parse(itemsJson) : []);

    // 调用 AI 生成文章
    setLoading(true);
    generateArticle({ itinerary: trip, packed_items: itemsJson ? JSON.parse(itemsJson) : [] })
      .then((res) => {
        if (res.error) { message.error(res.error); return; }
        setArticle(res.article || "");
      })
      .catch(() => message.error("文章生成失败"))
      .finally(() => setLoading(false));
  }, []);

  const handleSaveArticle = () => {
    // 保存文章到 sessionStorage 供社区发布使用
    sessionStorage.setItem("article-content", article);
    sessionStorage.setItem("article-title", article.split("\n")[0].replace(/^#+\s*/, "") || "旅行攻略");
  };

  return (
    <div className="min-h-screen bg-transparent flex flex-col">
      <header className="sticky top-0 z-50 bg-background-secondary border-b border-border-light shadow-sm no-print">
        <div className="max-w-[888px] mx-auto px-6 h-16 flex items-center justify-between gap-4">
          <button onClick={() => navigate("/home")} className="flex items-center gap-1 text-xs text-foreground-tertiary hover:text-primary font-mono">
            <ArrowLeft className="w-3.5 h-3.5" />返回
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setMode(mode === "preview" ? "edit" : "preview")}
              className="flex items-center gap-1 text-xs font-mono font-bold px-3 py-1.5 border border-border rounded-sm hover:border-primary hover:text-primary transition-all"
            >
              {mode === "preview" ? <><Edit3 className="w-3.5 h-3.5" />编辑</> : <><Eye className="w-3.5 h-3.5" />预览</>}
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-[888px] mx-auto px-6 py-10 flex-1 w-full">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Spin size="large" />
            <p className="mt-4 text-sm font-display italic text-foreground-secondary">AI 正在撰写你的旅行攻略...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* 文章内容 */}
            <div className="bg-background-secondary border border-border rounded-sm p-6 md:p-8">
              {mode === "preview" ? (
                <MarkdownRenderer content={article.replace(/<!--POSTCARD-->/g, "")} />
              ) : (
                <textarea
                  value={article}
                  onChange={(e) => setArticle(e.target.value)}
                  className="w-full min-h-[600px] p-4 text-sm font-mono border border-border rounded-sm bg-background outline-none focus:border-primary resize-y leading-relaxed"
                  placeholder="编辑你的攻略文章..."
                />
              )}
            </div>

            {/* 3D 明信片 */}
            {itinerary && (
              <div>
                <h2 className="text-lg font-bold font-display text-foreground mb-3 flex items-center gap-1.5">
                  <FileText className="w-4 h-4 text-primary" />行程明信片
                </h2>
                <PostcardFlipCard itinerary={itinerary} userName="旅行者" workNo="000000" />
              </div>
            )}

            {/* 底部操作栏 */}
            <div className="flex justify-center gap-4 py-6 border-t border-dashed border-border-light no-print">
              <Button
                icon={<Share2 className="w-4 h-4 inline mr-1" />}
                onClick={() => {
                  handleSaveArticle();
                  navigate("/community/post");
                }}
                className="h-10 bg-primary border-primary text-white hover:bg-primary-dark rounded-sm font-mono font-bold"
              >
                发布到社区
              </Button>
              <Button
                icon={<Download className="w-4 h-4 inline mr-1" />}
                onClick={() => {
                  handleSaveArticle();
                  window.print();
                }}
                className="h-10 border-border-dark text-foreground hover:border-primary hover:text-primary rounded-sm font-mono font-bold"
              >
                导出攻略卡片
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}