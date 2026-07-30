import React, { useEffect, useState } from "react";
import { Alert, Tag, Button, message } from "antd";
import { useShallow } from 'zustand/react/shallow';
import { CheckCircle2, AlertCircle, Sparkles, FolderHeart } from "lucide-react";
import useItineraryStore from "@/stores/itineraryStore.js";
import SearchBar from "@/components/SearchBar.jsx";
import PostcardFlipCard from "@/components/PostcardFlipCard.jsx";
import ItineraryTimeline from "@/components/ItineraryTimeline.jsx";
import MapView from "@/components/MapView.jsx";
import CostChart from "@/components/CostChart.jsx";
import FeedbackBar from "@/components/FeedbackBar.jsx";
import TravelPet from "@/components/TravelPet.jsx";

export default function Home() {
  const {
    currentPlan,
    loading,
    error,
    lastRequest,
    generateItinerary,
    savePlan,
    clearCurrentPlan
  } = useItineraryStore(useShallow((s) => ({
    currentPlan: s.currentPlan,
    loading: s.loading,
    error: s.error,
    lastRequest: s.lastRequest,
    generateItinerary: s.generateItinerary,
    savePlan: s.savePlan,
    clearCurrentPlan: s.clearCurrentPlan
  })));

  const [saving, setSaving] = useState(false);
  const [hasSaved, setHasSaved] = useState(false);

  // 每次进入主页清空残留的状态，保持纯净
  useEffect(() => {
    clearCurrentPlan();
    setHasSaved(false);
  }, [clearCurrentPlan]);

  const handleGenerate = async (req) => {
    setHasSaved(false);
    await generateItinerary(req);
  };

  const handleSave = async () => {
    if (hasSaved) {
      message.info("此攻略已收藏成功，无需重复保存。");
      return;
    }
    setSaving(true);
    try {
      const savedId = await savePlan();
      if (savedId) {
        message.success("行程攻略已成功归档到‘我的攻略’中！");
        setHasSaved(true);
      } else {
        message.error("保存失败，请检查登录态或稍后重试");
      }
    } catch {
      message.error("保存失败，请稍后重试");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 flex-1 w-full">
      
      {/* 顶部主标题杂志排版 */}
      <section className="text-center mb-10">
        <h1 className="text-4xl md:text-5xl font-black font-display tracking-tight leading-none text-foreground mb-3 uppercase">
          Trip<span className="text-primary">Craft</span> AI 行程
        </h1>
        <p className="text-sm font-mono text-foreground-secondary tracking-widest uppercase">
          ◇ 复古明信片式的旅行手册生成系统 ◇
        </p>
      </section>

      {/* 参数输入面板 */}
      <section className="mb-10">
        <SearchBar onGenerate={handleGenerate} loading={loading} />
      </section>

      {/* 状态反馈区 */}
      {loading && (
        <section className="py-20 text-center">
          <div className="inline-block relative">
            {/* 极简暖色 loading */}
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent mb-4" />
            <Sparkles className="absolute -top-1 -right-1 w-5 h-5 text-primary-light animate-pulse" />
          </div>
          <p className="text-lg font-display italic text-foreground-secondary font-semibold">
            正在通过微调模型精排最合理的明信片路线...
          </p>
          <p className="text-xs font-mono text-foreground-tertiary mt-2">
            AI GENERATION IN PROGRESS (ESTIMATED: 1-3 SECONDS)
          </p>
        </section>
      )}

      {error && !loading && (
        <section className="mb-8">
          <Alert
            message={<span className="font-sans font-semibold">无法生成攻略</span>}
            description={<span className="text-xs font-mono">{error}</span>}
            type="warning"
            showIcon
            className="rounded-[2px] bg-background-secondary border-primary/20"
          />
        </section>
      )}

      {/* 结果显示面板 */}
      {currentPlan && !loading && (
        <div className="space-y-10 animate-[fadeInUp_0.5s_ease-out]">
          
          {/* 行程验证徽章 */}
          {currentPlan.verification && (
            <div className="flex flex-wrap gap-3 items-center justify-center p-3 bg-background-tertiary border border-border-light rounded-[2px]">
              <span className="text-xs text-foreground-tertiary font-mono uppercase tracking-wider mr-2">
                系统验证结果:
              </span>
              
              {/* 真实性 */}
              <Tag
                icon={<CheckCircle2 className="w-3.5 h-3.5 inline mr-1 text-success" />}
                className="bg-background-secondary border-border text-xs py-1 px-2.5 rounded-[2px] font-semibold text-foreground flex items-center"
              >
                景点真实性 ({currentPlan.verification.spots_verified}/{currentPlan.verification.spots_total})
              </Tag>
              
              {/* 预算 */}
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
              
              {/* 路线 */}
              <Tag
                icon={<CheckCircle2 className="w-3.5 h-3.5 inline mr-1 text-success" />}
                className="bg-background-secondary border-border text-xs py-1 px-2.5 rounded-[2px] font-semibold text-foreground flex items-center"
              >
                路线轨迹 {currentPlan.verification.route_valid ? "合理" : "需调优"}
              </Tag>
            </div>
          )}

          {/* 一键收藏/保存到历史记录 */}
          <div className="flex justify-end">
            <Button
              type="primary"
              onClick={handleSave}
              loading={saving}
              disabled={hasSaved}
              icon={<FolderHeart className="w-4 h-4 inline mr-1" />}
              className={`h-9 font-mono font-bold tracking-wider rounded-[2px] text-xs uppercase ${
                hasSaved
                  ? "bg-success border-success hover:bg-success"
                  : "bg-primary border-primary hover:bg-primary-dark"
              }`}
            >
              {hasSaved ? "已成功归档到我的攻略" : "保存至‘我的攻略’"}
            </Button>
          </div>

          {/* 3D 物理翻转明信片（正面为物理明信片，背面为时间轴日程，支持物理打印） */}
          <section className="animate-[fadeInUp_0.5s_ease-out]">
            <PostcardFlipCard itinerary={currentPlan} userName="临心" workNo="549395" />
          </section>

          {/* 地图折线轨迹 */}
          <section>
            <h2 className="text-xl font-bold font-display text-foreground uppercase tracking-wider mb-4 border-l-4 border-primary pl-3">
              旅行轨迹地图
            </h2>
            <MapView itinerary={currentPlan} />
          </section>

          {/* ECharts 花费分析 */}
          <section>
            <h2 className="text-xl font-bold font-display text-foreground uppercase tracking-wider mb-4 border-l-4 border-primary pl-3">
              预计花费分析
            </h2>
            <CostChart itinerary={currentPlan} budget={lastRequest?.budget || 2000} />
          </section>

          {/* 反馈条 */}
          <section className="py-6">
            <FeedbackBar
              destination={lastRequest?.destination || ""}
              days={lastRequest?.days || 3}
              budget={lastRequest?.budget || 2000}
              preferences={lastRequest?.preferences || []}
              onRegenerate={() => lastRequest && handleGenerate(lastRequest)}
            />
          </section>

        </div>
      )}

      {/* 复古的空白说明状态：用户未搜索时展示 */}
      {!currentPlan && !loading && !error && (
        <section className="mt-12 py-16 px-6 border border-dashed border-border text-center rounded-[2px] bg-background-secondary/40">
          <div className="max-w-md mx-auto space-y-4">
            <img
              src="https://mdn.alipayobjects.com/fecodex_image/afts/img/JVKRQaNDtAIAAAAAgBAAAAgAejH3AQBr/original"
              alt="travel drawing"
              className="w-48 mx-auto grayscale opacity-80 mix-blend-multiply"
            />
            <h3 className="text-lg font-bold font-display text-foreground-secondary italic">
              “人生是一场明信片，风景总在寄出的瞬间”
            </h3>
            <p className="text-xs text-foreground-tertiary leading-relaxed font-mono">
              在上方的表单中选择你想游玩的城市、预定旅行的天数和总预算限额。我们的行程微调模块会自动核对当地的高德 LBS 真实经纬度与门票平均花费，为你排印一份高质感、高可读性的纯真行程。
            </p>
          </div>
        </section>
      )}

      <TravelPet />

      <style>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}