import { useState, useEffect } from "react";
import { Spin, Drawer, message } from "antd";
import { Backpack, Check, Plus, X, Package } from "lucide-react";
import { getPackingList, type PackingList as PackingListType } from "../services/api";

interface PackingListProps {
  city: string;
  days: number;
  preferences: string[];
}

const CATEGORY_ICONS: Record<string, string> = {
  "证件": "📋", "日用品": "🧴", "衣物": "👕", "医药": "💊",
  "防护": "🛡️", "装备": "🎒", "儿童": "🧸", "工具": "🔧", "特产": "🛍️",
};

interface PackedItem {
  item: string;
  category: string;
}

export default function PackingList({ city, days, preferences }: PackingListProps) {
  const [data, setData] = useState<PackingListType | null>(null);
  const [loading, setLoading] = useState(true);
  const [backpack, setBackpack] = useState<PackedItem[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [bagBounce, setBagBounce] = useState(false);

  useEffect(() => {
    if (!city) return;
    setLoading(true);
    getPackingList(city, days, preferences)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [city, days, preferences]);

  const isInBackpack = (item: string) => backpack.some(b => b.item === item);

  const toggleItem = (item: string, category: string) => {
    if (isInBackpack(item)) {
      // 从背包移除
      setBackpack(prev => prev.filter(b => b.item !== item));
      message.info(`已从背包取出：${item}`);
    } else {
      // 加入背包
      setBackpack(prev => [...prev, { item, category }]);
      setBagBounce(true);
      setTimeout(() => setBagBounce(false), 400);
    }
  };

  const removeFromBackpack = (item: string) => {
    setBackpack(prev => prev.filter(b => b.item !== item));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Spin size="small" />
        <span className="ml-2 text-xs text-foreground-tertiary font-mono">生成清单中...</span>
      </div>
    );
  }

  if (!data) {
    return <div className="py-4 text-center text-xs text-foreground-tertiary italic font-mono">暂无打包清单</div>;
  }

  return (
    <div className="bg-background-secondary border border-border rounded-sm p-5 relative">
      {/* 标题栏 + 背包按钮 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-1.5">
          <Package className="w-4 h-4 text-primary" />
          <span className="text-xs font-bold text-foreground-secondary uppercase tracking-widest font-mono">行李打包清单</span>
          <span className="text-[10px] text-foreground-tertiary font-mono ml-1">{data.season}季</span>
        </div>

        {/* 背包按钮 */}
        <button
          onClick={() => setDrawerOpen(true)}
          className={`relative flex items-center gap-1.5 px-3 py-1.5 border-2 border-primary rounded-sm hover:bg-primary/5 transition-all ${bagBounce ? "animate-bounce" : ""}`}
        >
          <Backpack className="w-4 h-4 text-primary" />
          <span className="text-xs font-mono font-bold text-primary">我的背包</span>
          {backpack.length > 0 && (
            <span className="absolute -top-2 -right-2 w-5 h-5 bg-primary text-white text-[10px] font-mono font-black rounded-full flex items-center justify-center border-2 border-background-secondary">
              {backpack.length}
            </span>
          )}
        </button>
      </div>

      <p className="text-[10px] text-foreground-tertiary font-mono mb-4 italic">点击物品加入背包，再次点击取出</p>

      {/* 分类清单 — 每个物品都是可点击按钮 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(data.categories).map(([category, items]) => (
          <div key={category} className="border border-border-light rounded-sm p-3 bg-background-tertiary">
            <div className="text-xs font-bold font-mono text-foreground mb-2 flex items-center gap-1">
              <span>{CATEGORY_ICONS[category] || "📦"}</span>
              <span>{category}</span>
              <span className="text-foreground-tertiary ml-auto">{items.length}件可选</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {items.map((item) => {
                const packed = isInBackpack(item);
                return (
                  <button
                    key={item}
                    onClick={() => toggleItem(item, category)}
                    className={`text-xs px-2.5 py-1 border rounded-sm transition-all flex items-center gap-1 active:scale-95 ${
                      packed
                        ? "bg-primary text-white border-primary shadow-sm"
                        : "border-border text-foreground-secondary hover:border-primary hover:text-primary bg-background-secondary"
                    }`}
                  >
                    {packed ? <Check className="w-2.5 h-2.5" /> : <Plus className="w-2.5 h-2.5 opacity-50" />}
                    {item}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* 背包抽屉 */}
      <Drawer
        title={
          <div className="flex items-center gap-2">
            <Backpack className="w-4 h-4 text-primary" />
            <span className="font-display font-bold">我的背包</span>
            <span className="text-xs font-mono text-foreground-tertiary ml-2">{backpack.length} 件物品</span>
          </div>
        }
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={360}
        styles={{ body: { padding: 0 } }}
      >
        {backpack.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full p-8 text-center">
            <Backpack className="w-12 h-12 text-foreground-tertiary opacity-30 mb-4" />
            <p className="text-sm text-foreground-tertiary italic">背包是空的</p>
            <p className="text-xs text-foreground-disabled mt-2 font-mono">点击左侧清单中的物品加入背包</p>
          </div>
        ) : (
          <div className="p-4">
            {/* 按分类分组展示 */}
            {Object.entries(
              backpack.reduce((acc, item) => {
                if (!acc[item.category]) acc[item.category] = [];
                acc[item.category].push(item);
                return acc;
              }, {} as Record<string, PackedItem[]>)
            ).map(([category, items]) => (
              <div key={category} className="mb-4">
                <div className="text-xs font-bold font-mono text-foreground-secondary mb-2 flex items-center gap-1 border-b border-border-light pb-1">
                  <span>{CATEGORY_ICONS[category] || "📦"}</span>
                  <span>{category}</span>
                  <span className="text-foreground-tertiary ml-auto">{items.length}件</span>
                </div>
                <div className="space-y-1">
                  {items.map((packed) => (
                    <div
                      key={packed.item}
                      className="flex items-center justify-between px-3 py-2 bg-background-tertiary border border-border-light rounded-sm group"
                    >
                      <span className="text-xs text-foreground">{packed.item}</span>
                      <button
                        onClick={() => removeFromBackpack(packed.item)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-error/10 rounded border border-transparent hover:border-error/30"
                      >
                        <X className="w-3 h-3 text-error" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {/* 底部统计 */}
            <div className="mt-4 pt-3 border-t border-border-light flex items-center justify-between">
              <span className="text-xs font-mono text-foreground-tertiary">总重量估算：轻装上阵</span>
              <button
                onClick={() => {
                  setBackpack([]);
                  message.info("背包已清空");
                }}
                className="text-xs font-mono text-error hover:underline"
              >
                清空背包
              </button>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}