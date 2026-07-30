import React, { useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useShallow } from 'zustand/react/shallow';
import { Tag, Button, message } from "antd";
import { ArrowLeft, CheckCircle2, AlertCircle, CalendarDays, Wallet, Sparkles } from "lucide-react";
import useItineraryStore from "@/stores/itineraryStore.js";
import PostcardFlipCard from "@/components/PostcardFlipCard.jsx";
import ItineraryTimeline from "@/components/ItineraryTimeline.jsx";
import MapView from "@/components/MapView.jsx";
import CostChart from "@/components/CostChart.jsx";
import FeedbackBar from "@/components/FeedbackBar.jsx";

export default function Detail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const {
    currentPlan,
    loading,
    error,
    getPlanDetail,
    clearCurrentPlan,
  } = useItineraryStore(useShallow((s) => ({
    currentPlan: s.currentPlan,
    loading: s.loading,
    error: s.error,
    getPlanDetail: s.getPlanDetail,
    clearCurrentPlan: s.clearCurrentPlan,
  })));

  useEffect(() => {
    if (id) {
      getPlanDetail(id);
    }
    return () => {
      clearCurrentPlan();
    };
  }, [id, getPlanDetail, clearCurrentPlan]);

  if (loading && !currentPlan) {
    return (
      <div className="py-32 text-center font-mono text-xs text-foreground-tertiary flex-1 flex flex-col justify-center">
        <div className="animate-spin inline-block w-6 h-6 border-2 border-primary border-t-transparent rounded-full mb-2 mx-auto" />
        <div>正在为您在书架中检索本明信片详情...</div>
      </div>
    );
  }

  if (error || !currentPlan) {
    return (
      <div className="max-w-md mx-auto px-6 py-20 text-center space-y-4 flex-1 flex flex-col justify-center">
        <AlertCircle className="w-10 h-10 text-error mx-auto" />
        <h2 className="text-xl font-bold font-display">未找到对应的旅行计划</h2>
        <p className="text-xs text-foreground-tertiary leading-relaxed font-mono">
          {error || "此行程可能已被原作者彻底删除。"}
        </p>
        <Link to="/history">
          <Button className="mt-2 h-9 bg-primary border-primary hover:bg-primary-dark text-white rounded-[2px] font-mono text-xs font-bold uppercase">
            返回我的档案清单
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 flex-1 w-full space-y-8">
      
      {/* 返回栏 */}
      <div className="flex justify-between items-center pb-4 border-b border-border">
        <Button
          onClick={() => navigate("/history")}
          icon={<ArrowLeft className="w-4 h-4 inline mr-1" />}
          className="h-9 border-border text-foreground-secondary hover:border-primary hover:text-primary rounded-[2px] text-xs font-mono font-bold"
        >
          返回我的档案 / Back
        </Button>
        <div className="text-xs font-mono text-foreground-tertiary uppercase">
          档案编号: {currentPlan.id}
        </div>
      </div>

      {/* 头部精美明信片排版 */}
      <section className="text-center md:text-left flex flex-col md:flex-row justify-between items-center gap-6">
        <div>
          <h1 className="text-4xl md:text-5xl font-black font-display text-foreground uppercase tracking-tight leading-none">
            {currentPlan.destination}
          </h1>
          <p className="text-sm font-mono text-primary font-bold uppercase tracking-widest mt-2">
            {currentPlan.summary || "专属定制明信片攻略"}
          </p>
        </div>

        {/* 顶部两个复古大标签 */}
        <div className="flex gap-4 font-mono">
          <div className="bg-background-secondary border border-border-dark py-2 px-4 rounded-[2px] text-center min-w-[80px]">
            <div className="text-[9px] uppercase text-foreground-tertiary">旅行时长</div>
            <div className="text-lg font-bold text-foreground font-display flex items-center justify-center gap-1">
              <CalendarDays className="w-4 h-4 text-primary" />
              <span>{currentPlan.days} 天</span>
            </div>
          </div>
          <div className="bg-background-secondary border border-border-dark py-2 px-4 rounded-[2px] text-center min-w-[80px]">
            <div className="text-[9px] uppercase text-foreground-tertiary">总预算</div>
            <div className="text-lg font-bold text-foreground font-display flex items-center justify-center gap-1">
              <Wallet className="w-4 h-4 text-primary" />
              <span>¥{currentPlan.budget}</span>
            </div>
          </div>
        </div>
      </section>

      {/* 偏好展现 */}
      {currentPlan.preferences?.length > 0 && (
        <section className="flex flex-wrap items-center gap-2 border-t border-b border-dashed border-border-light py-3">
          <span className="text-xs text-foreground-tertiary font-mono mr-2">旅行偏好:</span>
          {currentPlan.preferences.map((pref) => (
            <span
              key={pref}
              className="px-3 py-1 rounded-full border border-primary/20 bg-primary/5 text-xs text-primary font-bold font-mono"
            >
              #{pref}
            </span>
          ))}
        </section>
      )}

      {/* 校验通过徽章 */}
      {currentPlan.verification && (
        <div className="flex flex-wrap gap-3 items-center justify-center p-3 bg-background-tertiary border border-border-light rounded-[2px]">
          <span className="text-xs text-foreground-tertiary font-mono uppercase tracking-wider mr-2">
            系统验证结果:
          </span>
          <Tag
            icon={<CheckCircle2 className="w-3.5 h-3.5 inline mr-1 text-success" />}
            className="bg-background-secondary border-border text-xs py-1 px-2.5 rounded-[2px] font-semibold text-foreground flex items-center"
          >
            景点真实性 ({currentPlan.verification.spots_verified}/{currentPlan.verification.spots_total})
          </Tag>
          <Tag
            icon={
              currentPlan.verification.budget_valid ? (
                <CheckCircle2 className="w-3.5 h-3.5 inline mr-1 text-success" />
              ) : (
                <AlertCircle className="w-3.5 h-3.5 inline mr-1 text-error" />
              )
            }
            className={`border-border text-xs py-1 px-2.5 rounded-[2px] font-semibold flex items-center ${
              currentPlan.verification.budget_valid ? "bg-background-secondary text-foreground" : "bg-error/10 text-error"
            }`}
          >
            预算 {currentPlan.verification.budget_valid ? "合规内" : "已超预算"}
          </Tag>
          <Tag
            icon={<CheckCircle2 className="w-3.5 h-3.5 inline mr-1 text-success" />}
            className="bg-background-secondary border-border text-xs py-1 px-2.5 rounded-[2px] font-semibold text-foreground flex items-center"
          >
            路线轨迹 {currentPlan.verification.route_valid ? "合理" : "需调优"}
          </Tag>
        </div>
      )}

      {/* 3D 物理翻转明信片（正面为物理明信片，背面为时间轴日程，支持物理打印） */}
      <section>
        <PostcardFlipCard itinerary={currentPlan} userName="临心" workNo="549395" />
      </section>

      {/* 地图折线轨迹 */}
      <section>
        <h2 className="text-xl font-bold font-display text-foreground uppercase tracking-wider mb-4 border-l-4 border-primary pl-3">
          路线轨迹图
        </h2>
        <MapView itinerary={currentPlan} />
      </section>

      {/* ECharts 花费分析 */}
      <section>
        <h2 className="text-xl font-bold font-display text-foreground uppercase tracking-wider mb-4 border-l-4 border-primary pl-3">
          花费明细分析
        </h2>
        <CostChart itinerary={currentPlan} budget={currentPlan.budget} />
      </section>

      {/* 反馈条 */}
      <section className="py-6">
        <FeedbackBar
          destination={currentPlan.destination}
          days={currentPlan.days}
          budget={currentPlan.budget}
          preferences={currentPlan.preferences || []}
          onRegenerate={() => {
            message.info("此攻略是从归档库中读取的，如需修改，请返回主页重新输入参数配置生成。");
          }}
        />
      </section>

    </div>
  );
}