import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { Spin, message } from "antd";
import { ArrowLeft, Heart, MessageSquare, Eye, MapPin, Send } from "lucide-react";
import MarkdownRenderer from "../components/MarkdownRenderer";
import PostcardFlipCard from "../components/PostcardFlipCard";
import { getPost, getComments, createComment, likePost, unlikePost, isLoggedIn, type PostDetail as PostDetailType, type Itinerary } from "../services/api";

interface Comment {
  id: number; content: string; created_at: string;
  author: { id: number; nickname: string };
}

export default function PostDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [post, setPost] = useState<PostDetailType | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [commentText, setCommentText] = useState("");
  const [liked, setLiked] = useState(false);
  const [tripJson, setTripJson] = useState<Itinerary | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getPost(parseInt(id)).then((data) => {
      if (data.error) { message.error(data.error); return; }
      setPost(data);
      if (data.trip_json) {
        try { setTripJson(JSON.parse(data.trip_json)); } catch {}
      }
      // 检查是否已点赞
      const token = localStorage.getItem("tripcraft-token");
      if (token) {
        likePost(parseInt(id)).catch(() => {});
      }
    }).finally(() => setLoading(false));

    getComments(parseInt(id)).then(setComments).catch(() => {});
  }, [id]);

  const handleLike = async () => {
    if (!isLoggedIn()) { message.info("请先登录后点赞"); return; }
    try {
      if (liked) {
        await unlikePost(parseInt(id!));
        setLiked(false);
        setPost(prev => prev ? { ...prev, like_count: prev.like_count - 1 } : prev);
      } else {
        await likePost(parseInt(id!));
        setLiked(true);
        setPost(prev => prev ? { ...prev, like_count: prev.like_count + 1 } : prev);
      }
    } catch { message.error("操作失败"); }
  };

  const handleComment = async () => {
    if (!isLoggedIn()) { message.info("请先登录后评论"); return; }
    if (!commentText.trim()) return;
    try {
      await createComment(parseInt(id!), commentText.trim());
      setCommentText("");
      message.success("评论成功");
      // 刷新评论
      getComments(parseInt(id!)).then(setComments);
      setPost(prev => prev ? { ...prev, comment_count: prev.comment_count + 1 } : prev);
    } catch { message.error("评论失败"); }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center"><Spin size="large" /></div>;
  }

  if (!post || post.error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="text-center">
          <p className="text-sm text-foreground-tertiary italic mb-4">帖子不存在</p>
          <Link to="/community" className="text-xs font-mono text-primary hover:underline">返回社区</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-transparent flex flex-col">
      <header className="sticky top-0 z-50 bg-background-secondary border-b border-border-light shadow-sm no-print">
        <div className="max-w-[888px] mx-auto px-6 h-16 flex items-center justify-between gap-6">
          <Link to="/community" className="flex items-center gap-1 text-xs text-foreground-tertiary hover:text-primary font-mono">
            <ArrowLeft className="w-3.5 h-3.5" />返回社区
          </Link>
        </div>
      </header>

      <div className="max-w-[888px] mx-auto px-6 py-10 flex-1 w-full">
        {/* 作者信息 */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-primary text-white text-sm font-bold flex items-center justify-center">
            {post.author.nickname?.[0]?.toUpperCase() || "U"}
          </div>
          <div>
            <div className="text-sm font-bold text-foreground">{post.author.nickname}</div>
            <div className="text-[10px] text-foreground-tertiary font-mono">{post.created_at}</div>
          </div>
        </div>

        {/* 文章内容 */}
        <div className="bg-background-secondary border border-border rounded-sm p-6 md:p-8 mb-6">
          <MarkdownRenderer content={post.content.replace(/<!--POSTCARD-->/g, "")} />
        </div>

        {/* 3D 明信片 */}
        {tripJson && (
          <div className="mb-6">
            <PostcardFlipCard itinerary={tripJson} userName={post.author.nickname} workNo="000000" />
          </div>
        )}

        {/* 操作栏 */}
        <div className="flex items-center gap-4 py-4 border-t border-border-light no-print">
          <button onClick={handleLike} className={`flex items-center gap-1.5 text-sm font-mono px-4 py-2 border rounded-sm transition-all ${liked ? "bg-primary text-white border-primary" : "border-border text-foreground-secondary hover:border-primary"}`}>
            <Heart className={`w-4 h-4 ${liked ? "fill-current" : ""}`} />{post.like_count}
          </button>
          <span className="flex items-center gap-1 text-sm text-foreground-tertiary font-mono">
            <MessageSquare className="w-4 h-4" />{post.comment_count}
          </span>
          <span className="flex items-center gap-1 text-sm text-foreground-tertiary font-mono">
            <Eye className="w-4 h-4" />{post.view_count}
          </span>
          {tripJson && (
            <button
              onClick={() => {
                sessionStorage.setItem("article-itinerary", JSON.stringify(tripJson));
                navigate("/home");
              }}
              className="ml-auto text-xs font-mono font-bold text-primary border border-primary px-4 py-2 rounded-sm hover:bg-primary hover:text-white transition-all"
            >
              生成我的行程
            </button>
          )}
        </div>

        {/* 评论区 */}
        <div className="mt-6 no-print">
          <h3 className="text-sm font-bold font-mono text-foreground mb-3">评论 ({comments.length})</h3>
          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="写评论..."
              className="flex-1 h-9 px-3 text-xs border border-border rounded-sm bg-background outline-none focus:border-primary"
              onKeyDown={(e) => { if (e.key === "Enter") handleComment(); }}
            />
            <button onClick={handleComment} className="h-9 px-3 bg-primary text-white text-xs font-mono font-bold rounded-sm hover:bg-primary-dark flex items-center gap-1">
              <Send className="w-3.5 h-3.5" />发送
            </button>
          </div>
          <div className="space-y-2">
            {comments.map((c) => (
              <div key={c.id} className="p-3 bg-background-tertiary rounded-sm">
                <div className="flex items-center gap-2 mb-1">
                  <span className="w-6 h-6 rounded-full bg-primary text-white text-[10px] font-bold flex items-center justify-center">
                    {c.author.nickname?.[0]?.toUpperCase() || "U"}
                  </span>
                  <span className="text-xs font-bold text-foreground">{c.author.nickname}</span>
                  <span className="text-[10px] text-foreground-tertiary font-mono ml-auto">{c.created_at}</span>
                </div>
                <p className="text-xs text-foreground-secondary pl-8">{c.content}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}