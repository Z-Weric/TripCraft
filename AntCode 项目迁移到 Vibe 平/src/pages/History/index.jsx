import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useShallow } from 'zustand/react/shallow';
import { Input, Button, Popconfirm, message } from "antd";
import { Search, MapPin, CalendarDays, Wallet, Trash2, ArrowUpRight } from "lucide-react";
import useItineraryStore from "@/stores/itineraryStore.js";

export default function History() {
  const { historyList, loading, getHistoryList, deletePlan } = useItineraryStore(
    useShallow((s) => ({
      historyList: s.historyList,
      loading: s.loading,
      getHistoryList: s.getHistoryList,
      deletePlan: s.deletePlan,
    }))
  );

  const [searchText, setSearchText] = useState("");

  useEffect(() => {
    getHistoryList();
  }, [getHistoryList]);

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    e.preventDefault();
    const success = await deletePlan(id);
    if (success) {
      message.success("该旅行攻略已被移出你的清单");
    } else {
      message.error("删除失败");
    }
  };

  // 本地根据目的地进行模糊搜索过滤
  const filteredList = historyList.filter((item) =>
    (item.destination || "").toLowerCase().includes(searchText.toLowerCase())
  );

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 flex-1 w-full">
      
      {/* 头部杂志式排版 */}
      <section className="mb-10 text-center md:text-left flex flex-col md:flex-row justify-between items-center border-b border-border pb-6 gap-4">
        <div>
          <h1 className="text-3xl font-black font-display text-foreground uppercase tracking-tight">
            我的攻略档案 / Plans
          </h1>
          <p className="text-xs font-mono text-foreground-tertiary uppercase tracking-widest mt-1">
            ◇ 已保存的历史旅行明信片记录 (共计 {historyList.length} 份)
          </p>
        </div>

        {/* 极细边框检索输入框 */}
        <div className="relative w-full md:w-64">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-foreground-tertiary" />
          <Input
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="检索目的地城市..."
            className="pl-9 h-9 bg-background-secondary border border-border focus:border-primary focus:border-width-2 rounded-[2px] shadow-none text-xs"
          />
        </div>
      </section>

      {/* 历史卡片网格 */}
      {loading && historyList.length === 0 ? (
        <div className="py-20 text-center font-mono text-xs text-foreground-tertiary">
          <div className="animate-spin inline-block w-6 h-6 border-2 border-primary border-t-transparent rounded-full mb-2" />
          <div>正在翻阅您的旅行档案库...</div>
        </div>
      ) : filteredList.length === 0 ? (
        <section className="py-16 px-6 text-center border border-dashed border-border rounded-[2px] bg-background-secondary/30">
          <div className="max-w-xs mx-auto space-y-3">
            <img
              src="https://mdn.alipayobjects.com/fecodex_image/afts/img/JVKRQaNDtAIAAAAAgBAAAAgAejH3AQBr/original"
              alt="blank history"
              className="w-32 mx-auto grayscale opacity-40 mix-blend-multiply"
            />
            <h3 className="text-sm font-bold text-foreground-secondary font-display italic">
              {searchText ? "没有检索到相符的明信片" : "尚无归档的旅行明信片"}
            </h3>
            <p className="text-[11px] text-foreground-tertiary leading-relaxed font-mono">
              {searchText ? "请更换关键词重试" : "生成全新旅行路线并点击‘保存至我的攻略’，已归档明信片即会在下方呈现。"}
            </p>
            {!searchText && (
              <Link to="/">
                <Button className="mt-2 h-8 bg-primary border-primary hover:bg-primary-dark text-white rounded-[2px] font-mono text-xs font-bold uppercase">
                  立即生成第一份攻略
                </Button>
              </Link>
            )}
          </div>
        </section>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredList.map((plan) => (
            <Link
              key={plan.id}
              to={`/detail/${plan.id}`}
              className="group block bg-background-secondary border border-border hover:border-primary rounded-[2px] p-5 transition-all relative overflow-hidden shadow-sm hover:-translate-y-0.5 duration-200"
            >
              {/* 装饰卡角 */}
              <div className="absolute top-0 right-0 w-8 h-8 bg-background-tertiary border-l border-b border-border group-hover:bg-primary-light/20 group-hover:border-primary transition-colors flex items-center justify-center">
                <ArrowUpRight className="w-3 h-3 text-foreground-tertiary group-hover:text-primary transition-colors" />
              </div>

              {/* 城市名 */}
              <h2 className="text-2xl font-black font-display text-foreground tracking-tight mb-1 group-hover:text-primary transition-colors pr-6">
                {plan.destination}
              </h2>
              
              <div className="text-[11px] font-mono text-primary font-bold uppercase tracking-wider mb-4 border-b border-dashed border-border-light pb-2">
                {plan.summary || "专属定制明信片攻略"}
              </div>

              {/* 攻略核心参数元信息 */}
              <div className="space-y-2 text-xs font-mono text-foreground-secondary">
                <div className="flex items-center gap-2">
                  <CalendarDays className="w-3.5 h-3.5 text-foreground-tertiary" />
                  <span>游玩时数: <strong className="text-foreground">{plan.days} 天</strong></span>
                </div>
                <div className="flex items-center gap-2">
                  <Wallet className="w-3.5 h-3.5 text-foreground-tertiary" />
                  <span>预设预算: <strong className="text-foreground">¥{plan.budget}</strong></span>
                </div>
                {plan.totalCost && (
                  <div className="flex items-center gap-2">
                    <MapPin className="w-3.5 h-3.5 text-foreground-tertiary" />
                    <span>预计花费: <strong className="text-primary font-bold">¥{plan.totalCost}</strong></span>
                  </div>
                )}
              </div>

              {/* 卡片底栏操作区 */}
              <div className="mt-5 pt-3 border-t border-border-light flex justify-between items-center">
                <span className="text-[10px] text-foreground-tertiary font-mono">
                  归档日期: {new Date(plan.createTime).toLocaleDateString()}
                </span>
                
                {/* 气泡确认删除 */}
                <Popconfirm
                  title="确认删除该旅行攻略档案吗？"
                  okText="确认删除"
                  cancelText="手滑了"
                  okButtonProps={{ className: "bg-error border-error hover:bg-error/80" }}
                  onConfirm={(e) => handleDelete(plan.id, e)}
                  onCancel={(e) => { e.stopPropagation(); e.preventDefault(); }}
                >
                  <button
                    onClick={(e) => { e.stopPropagation(); e.preventDefault(); }}
                    className="p-1.5 text-foreground-tertiary hover:text-error rounded hover:bg-background-tertiary transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </Popconfirm>
              </div>

            </Link>
          ))}
        </div>
      )}

    </div>
  );
}