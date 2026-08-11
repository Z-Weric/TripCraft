import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { message, Spin } from "antd";
import { ArrowLeft, Send } from "lucide-react";
import { createPost } from "../services/api";

export default function PostPublish() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [city, setCity] = useState("");
  const [tags, setTags] = useState("攻略");
  const [tripJson, setTripJson] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const savedTitle = sessionStorage.getItem("article-title") || "";
    const savedContent = sessionStorage.getItem("article-content") || "";
    const tripJson = sessionStorage.getItem("article-itinerary") || "";
    setTitle(savedTitle);
    setContent(savedContent);
    setTripJson(tripJson);
    // 从行程中提取城市
    if (tripJson) {
      try {
        const trip = JSON.parse(tripJson);
        setCity(trip.destination || "");
      } catch {}
    }
  }, []);

  const handlePublish = async () => {
    if (!title.trim()) { message.warning("请输入标题"); return; }
    if (!content.trim()) { message.warning("内容不能为空"); return; }

    setLoading(true);
    try {
      const res = await createPost({
        title: title.trim(),
        content: content,
        city: city,
        tags: tags,
        trip_json: tripJson || undefined,
      });
      if (res.error) {
        message.error(res.error);
      } else {
        message.success("发布成功！");
        // 清理 sessionStorage
        sessionStorage.removeItem("article-content");
        sessionStorage.removeItem("article-title");
        sessionStorage.removeItem("article-itinerary");
        navigate(`/post/${res.id}`);
      }
    } catch {
      message.error("发布失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-transparent flex flex-col">
      <header className="sticky top-0 z-50 bg-background-secondary border-b border-border-light shadow-sm no-print">
        <div className="max-w-[888px] mx-auto px-6 h-16 flex items-center justify-between gap-6">
          <Link to="/article/edit" className="flex items-center gap-1 text-xs text-foreground-tertiary hover:text-primary font-mono">
            <ArrowLeft className="w-3.5 h-3.5" />返回编辑
          </Link>
        </div>
      </header>

      <div className="max-w-[888px] mx-auto px-6 py-10 flex-1 w-full">
        <h1 className="text-2xl font-black font-display tracking-tight text-foreground uppercase mb-6">发布到社区</h1>

        <div className="space-y-5">
          <div>
            <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-2 font-mono">标题</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="帖子标题"
              className="w-full h-10 px-3 text-sm border border-border rounded-sm bg-background-secondary outline-none focus:border-primary focus:ring-1 focus:ring-primary/30"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-2 font-mono">城市</label>
            <input
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="如：杭州"
              className="w-full h-10 px-3 text-sm border border-border rounded-sm bg-background-secondary outline-none focus:border-primary focus:ring-1 focus:ring-primary/30"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-2 font-mono">标签</label>
            <div className="flex gap-2">
              {["攻略", "感悟", "美食", "住宿"].map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTags(t)}
                  className={`px-4 py-2 text-xs font-mono font-bold border rounded-sm transition-all ${tags === t ? "bg-primary text-white border-primary" : "border-border text-foreground-secondary hover:border-primary hover:text-primary bg-background-secondary"}`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-2 font-mono">内容预览</label>
            <div className="p-4 bg-background-tertiary border border-border rounded-sm max-h-60 overflow-y-auto scrollbar-thin">
              <pre className="text-xs text-foreground-secondary whitespace-pre-wrap font-mono">{content.slice(0, 500)}...</pre>
            </div>
          </div>

          <div className="flex justify-center pt-4">
            <button
              onClick={handlePublish}
              disabled={loading}
              className="h-10 px-8 bg-primary text-white text-sm font-bold rounded-sm hover:bg-primary-dark transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {loading ? <Spin size="small" /> : <><Send className="w-4 h-4" />发布</>}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}