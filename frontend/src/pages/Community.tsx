import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Spin, Empty } from "antd";
import { Heart, MessageSquare, Eye, MapPin } from "lucide-react";
import { listPosts, type PostSummary } from "../services/api";

const TAGS = [
  { key: "", label: "全部" },
  { key: "攻略", label: "攻略" },
  { key: "感悟", label: "感悟" },
  { key: "美食", label: "美食" },
  { key: "住宿", label: "住宿" },
];

export default function Community({ embedded = false }: { embedded?: boolean }) {
  const [posts, setPosts] = useState<PostSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [tag, setTag] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    setLoading(true);
    listPosts(page, tag || undefined).then((res) => {
      setPosts(res.posts);
      setTotal(res.total);
    }).finally(() => setLoading(false));
  }, [page, tag]);

  const content = (
    <>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-black font-display tracking-tight text-foreground uppercase">旅行社区</h1>
        <Link to="/home" className="text-xs font-mono text-primary hover:underline">发布攻略 →</Link>
      </div>

      <div className="flex gap-2 mb-6">
        {TAGS.map((t) => (
          <button
            key={t.key}
            onClick={() => { setTag(t.key); setPage(1); }}
            className={`text-xs px-3 py-1.5 border rounded-full transition-all font-mono font-bold ${tag === t.key ? "bg-primary text-white border-primary" : "border-border text-foreground-secondary hover:border-primary hover:text-primary"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Spin /></div>
      ) : posts.length === 0 ? (
        <Empty description={<span className="text-sm text-foreground-tertiary italic">暂无帖子，去生成攻略发布吧</span>} />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {posts.map((post) => (
              <Link
                key={post.id}
                to={`/post/${post.id}`}
                className="bg-background-secondary border border-border rounded-sm p-4 hover:border-primary transition-all group"
              >
                <h3 className="text-base font-bold font-display text-foreground mb-2 line-clamp-2 group-hover:text-primary transition-colors">
                  {post.title}
                </h3>
                <div className="flex items-center gap-3 text-[10px] text-foreground-tertiary font-mono mb-2">
                  {post.city && <span className="flex items-center gap-0.5"><MapPin className="w-3 h-3" />{post.city}</span>}
                  {post.tags && <span className="px-1.5 py-0.5 bg-primary/10 text-primary rounded-sm">{post.tags}</span>}
                </div>
                <div className="flex items-center justify-between text-[10px] text-foreground-tertiary font-mono">
                  <span>{post.author.nickname}</span>
                  <span className="flex items-center gap-3">
                    <span className="flex items-center gap-0.5"><Heart className="w-3 h-3" />{post.like_count}</span>
                    <span className="flex items-center gap-0.5"><MessageSquare className="w-3 h-3" />{post.comment_count}</span>
                    <span className="flex items-center gap-0.5"><Eye className="w-3 h-3" />{post.view_count}</span>
                  </span>
                </div>
              </Link>
            ))}
          </div>

          {total > 10 && (
            <div className="flex justify-center gap-2 mt-6">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="text-xs font-mono px-3 py-1.5 border border-border rounded-sm disabled:opacity-30 hover:border-primary hover:text-primary transition-all"
              >
                上一页
              </button>
              <span className="text-xs font-mono text-foreground-tertiary px-3 py-1.5">{page} / {Math.ceil(total / 10)}</span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={page >= Math.ceil(total / 10)}
                className="text-xs font-mono px-3 py-1.5 border border-border rounded-sm disabled:opacity-30 hover:border-primary hover:text-primary transition-all"
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}
    </>
  );

  if (embedded) {
    return <div className="max-w-[888px] mx-auto px-6 py-10">{content}</div>;
  }

  return (
    <div className="min-h-screen bg-transparent flex flex-col">
      <header className="sticky top-0 z-50 bg-background-secondary border-b border-border-light shadow-sm">
        <div className="max-w-[888px] mx-auto px-6 h-16 flex items-center justify-between gap-6">
          <Link to="/home" className="text-2xl font-black font-display tracking-tight text-foreground hover:text-primary transition-colors">
            Trip<span className="text-primary font-bold">Craft</span>
          </Link>
          <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] uppercase font-bold tracking-widest border border-primary text-primary rounded-sm">旅游社区</span>
        </div>
      </header>

      <div className="max-w-[888px] mx-auto px-6 py-10 flex-1 w-full">
        {content}
      </div>
    </div>
  );
}
