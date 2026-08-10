import { useState, useEffect } from "react";
import { Modal, Spin, Rate, message } from "antd";
import { Star, MapPin, Clock, DollarSign, Tag, Heart, MessageSquare } from "lucide-react";
import { getPoiDetail, toggleFavorite, submitReview, isLoggedIn } from "../services/api";

interface PoiDetail {
  id: number;
  name: string;
  category: string;
  city: string;
  lat: number;
  lng: number;
  address: string;
  cost: number;
  duration: string;
  note: string;
  amap_rating: number;
  user_rating_avg: number;
  review_count: number;
  composite_rating: number;
  is_favorited: boolean;
  reviews: { id: number; rating: number; comment: string; created_at: string }[];
}

interface PoiDetailModalProps {
  poiId: number | null;
  open: boolean;
  onClose: () => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  "自然风光": "#5B8C5A", "美食": "#C9622A", "历史文化": "#8B6F4E", "购物": "#B8860B", "亲子": "#6B4A8C",
};

export default function PoiDetailModal({ poiId, open, onClose }: PoiDetailModalProps) {
  const [detail, setDetail] = useState<PoiDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [favorited, setFavorited] = useState(false);
  const [userRating, setUserRating] = useState(0);
  const [userComment, setUserComment] = useState("");

  useEffect(() => {
    if (!open || !poiId) return;
    setLoading(true);
    getPoiDetail(poiId)
      .then((data) => {
        if (data.error) { message.error(data.error); return; }
        setDetail(data);
        setFavorited(data.is_favorited);
      })
      .catch(() => message.error("加载失败"))
      .finally(() => setLoading(false));
  }, [open, poiId]);

  const handleFavorite = async () => {
    if (!isLoggedIn()) { message.info("请先登录后收藏"); return; }
    try {
      const res = await toggleFavorite(poiId!, favorited);
      setFavorited(res.favorited);
      message.success(res.favorited ? "已收藏" : "已取消收藏");
    } catch { message.error("操作失败"); }
  };

  const handleReview = async () => {
    if (!isLoggedIn()) { message.info("请先登录后评论"); return; }
    if (userRating === 0) { message.warning("请选择评分"); return; }
    try {
      await submitReview(poiId!, userRating, userComment);
      message.success("评价已提交");
      setUserRating(0);
      setUserComment("");
      // 重新加载详情
      const data = await getPoiDetail(poiId!);
      if (!data.error) setDetail(data);
    } catch { message.error("提交失败"); }
  };

  return (
    <Modal
      title={detail ? detail.name : "景点详情"}
      open={open}
      onCancel={onClose}
      footer={null}
      width={480}
    >
      {loading ? (
        <div className="flex justify-center py-8"><Spin /></div>
      ) : detail ? (
        <div className="py-2 space-y-4">
          {/* 评分区 */}
          <div className="flex items-center justify-between p-3 bg-background-tertiary rounded-sm">
            <div className="flex items-center gap-3">
              <div className="text-center">
                <div className="text-2xl font-black font-mono text-primary">{detail.composite_rating}</div>
                <div className="text-[9px] text-foreground-tertiary font-mono">综合评分</div>
              </div>
              <div className="text-xs space-y-0.5">
                <div className="flex items-center gap-1"><Star className="w-3 h-3 text-primary" />高德: {detail.amap_rating}</div>
                <div className="flex items-center gap-1"><Star className="w-3 h-3 text-foreground-tertiary" />用户: {detail.user_rating_avg} ({detail.review_count}人)</div>
              </div>
            </div>
            <button onClick={handleFavorite} className={`flex items-center gap-1 px-3 py-1.5 border rounded-sm transition-all ${favorited ? "bg-primary text-white border-primary" : "border-border text-foreground-secondary hover:border-primary"}`}>
              <Heart className={`w-3.5 h-3.5 ${favorited ? "fill-current" : ""}`} />
              <span className="text-xs font-mono">{favorited ? "已收藏" : "收藏"}</span>
            </button>
          </div>

          {/* 基本信息 */}
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2 text-foreground-secondary">
              <Tag className="w-3.5 h-3.5 text-foreground-tertiary" />
              <span className="px-1.5 py-0.5 rounded-sm text-[10px]" style={{ color: CATEGORY_COLORS[detail.category] || "#8B6F4E", background: `${CATEGORY_COLORS[detail.category] || "#8B6F4E"}1f` }}>{detail.category}</span>
            </div>
            {detail.address && <div className="flex items-center gap-2 text-foreground-secondary"><MapPin className="w-3.5 h-3.5 text-foreground-tertiary" />{detail.address}</div>}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5 text-foreground-secondary"><Clock className="w-3.5 h-3.5 text-foreground-tertiary" />{detail.duration || "2h"}</div>
              <div className="flex items-center gap-1.5 text-foreground-secondary"><DollarSign className="w-3.5 h-3.5 text-foreground-tertiary" />{detail.cost === 0 ? "免费" : `¥${detail.cost}`}</div>
            </div>
            {detail.note && <div className="text-foreground-tertiary italic leading-relaxed pt-1">{detail.note}</div>}
          </div>

          {/* 用户评论 */}
          {detail.reviews.length > 0 && (
            <div className="border-t border-border-light pt-3">
              <div className="flex items-center gap-1 mb-2 text-xs font-bold text-foreground-secondary font-mono">
                <MessageSquare className="w-3.5 h-3.5" />用户评论
              </div>
              <div className="space-y-2">
                {detail.reviews.map((r) => (
                  <div key={r.id} className="text-xs p-2 bg-background-tertiary rounded-sm">
                    <div className="flex items-center gap-1 mb-1">
                      <Rate disabled value={r.rating} style={{ fontSize: 10 }} />
                      <span className="text-foreground-tertiary text-[10px] ml-auto">{r.created_at}</span>
                    </div>
                    {r.comment && <p className="text-foreground-secondary">{r.comment}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 评分输入 */}
          <div className="border-t border-border-light pt-3">
            <div className="text-xs font-bold text-foreground-secondary mb-2 font-mono">给景点打分</div>
            <div className="flex items-center gap-2 mb-2">
              <Rate value={userRating} onChange={setUserRating} />
            </div>
            <textarea
              value={userComment}
              onChange={(e) => setUserComment(e.target.value)}
              placeholder="写点评论（可选）..."
              className="w-full p-2 text-xs border border-border rounded-sm bg-background resize-none h-16 mb-2"
            />
            <button onClick={handleReview} className="w-full h-8 bg-primary text-white text-xs font-bold rounded-sm hover:bg-primary-dark transition-all">提交评价</button>
          </div>
        </div>
      ) : null}
    </Modal>
  );
}