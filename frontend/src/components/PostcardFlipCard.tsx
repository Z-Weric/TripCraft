import { useState, useEffect } from "react";
import { Rotate3d, Mail, Printer, Sparkles } from "lucide-react";
import { Button } from "antd";
import ItineraryTimeline from "./ItineraryTimeline";
import type { Itinerary, ItineraryItem } from "../services/api";

/** 城市邮票图片映射 */
const STAMP_IMAGES: Record<string, string> = {
  "杭州": "/stamps/hangzhou.png",
  "成都": "/stamps/chengdu.png",
  "西安": "/stamps/xian.png",
  "大理": "/stamps/dali.png",
  "厦门": "/stamps/xiamen.png",
  "苏州": "/stamps/suzhou.png",
  "南京": "/stamps/nanjing.png",
  "重庆": "/stamps/chongqing.png",
  "长沙": "/stamps/changsha.png",
  "青岛": "/stamps/qingdao.png",
};
const DEFAULT_STAMP = "/stamps/default.png";

/** 城市明信片主体插图映射 */
const MAIN_IMAGES: Record<string, string> = {
  "杭州": "/stamps/hangzhou-main.png",
  "成都": "/stamps/chengdu-main.png",
  "西安": "/stamps/xian-main.png",
  "大理": "/stamps/dali-main.png",
  "厦门": "/stamps/xiamen-main.png",
  "苏州": "/stamps/suzhou-main.png",
  "南京": "/stamps/nanjing-main.png",
  "重庆": "/stamps/chongqing-main.png",
  "长沙": "/stamps/changsha-main.png",
  "青岛": "/stamps/qingdao-main.png",
};
const DEFAULT_MAIN = "/stamps/default-main.png";

const CITY_CONFIGS: Record<string, any> = {
  "杭州": {
    sealName: "西湖十景",
    poem: "欲把西湖比西子，淡妆浓抹总相宜。",
    stampDesc: "HANGZHOU • WESTLAKE",
    zipCode: "310000",
    sealSvg: (<svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="50" cy="50" r="45" strokeDasharray="5 5" /><path d="M25 50 C 35 40, 45 60, 55 50 C 65 40, 75 60, 80 50" strokeWidth="1.5" /><path d="M20 75 C 35 65, 50 85, 80 75" /><polygon points="45,45 50,20 55,45" /><text x="50" y="82" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">杭州 • 西湖</text></svg>),
  },
  "成都": {
    sealName: "天府锦官",
    poem: "晓看红湿处，花重锦官城。",
    stampDesc: "CHENGDU • SHU",
    zipCode: "610000",
    sealSvg: (<svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="50" cy="50" r="45" /><path d="M30 35 Q 50 25 70 35" /><path d="M25 55 Q 50 45 75 55" /><circle cx="50" cy="65" r="10" /><text x="50" y="82" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">成都 • 锦官</text></svg>),
  },
  "西安": {
    sealName: "长安古道",
    poem: "春风得意马蹄疾，一日看尽长安花。",
    stampDesc: "XIAN • CHANGAN",
    zipCode: "710000",
    sealSvg: (<svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2"><rect x="20" y="30" width="60" height="50" /><rect x="30" y="40" width="40" height="30" /><polygon points="15,30 50,10 85,30" /><text x="50" y="82" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">西安 • 长安</text></svg>),
  },
  "大理": {
    sealName: "苍山洱海",
    poem: "下关风，上关花，苍山雪，洱海月。",
    stampDesc: "DALI • ERHAI",
    zipCode: "671000",
    sealSvg: (<svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="50" cy="50" r="45" strokeDasharray="5 5" /><path d="M25 45 C 35 35, 45 55, 55 45 C 65 35, 75 55, 80 45" strokeWidth="1.5" /><path d="M20 70 C 35 60, 50 80, 80 70" /><polygon points="45,45 50,20 55,45" /><text x="50" y="82" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">大理 • 苍山</text></svg>),
  },
  "厦门": {
    sealName: "鹭岛琴音",
    poem: "鹭飞鱼跃琴声起，半城海水半城春。",
    stampDesc: "XIAMEN • AMOY",
    zipCode: "361000",
    sealSvg: (<svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="50" cy="50" r="45" /><path d="M20 65 Q 35 55, 50 65 T 80 65" /><polygon points="43,40 50,25 57,40" /><text x="50" y="82" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">厦门 • 鹭岛</text></svg>),
  },
  "苏州": {
    sealName: "园林水乡",
    poem: "君到姑苏见，人家尽枕河。",
    stampDesc: "SUZHOU • GARDEN",
    zipCode: "215000",
    sealSvg: (<svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="50" cy="50" r="45" /><path d="M20 60 Q 50 30, 80 60" /><path d="M30 60 Q 50 40, 70 60" /><text x="50" y="82" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">苏州 • 园林</text></svg>),
  },
  "南京": {
    sealName: "六朝古都",
    poem: "江南佳丽地，金陵帝王州。",
    stampDesc: "NANJING • JINLING",
    zipCode: "210000",
    sealSvg: (<svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2"><rect x="25" y="35" width="50" height="40" /><polygon points="20,35 50,15 80,35" /><rect x="40" y="45" width="20" height="30" fill="none" /><text x="50" y="82" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">南京 • 金陵</text></svg>),
  },
  "重庆": {
    sealName: "山城夜色",
    poem: "君问归期未有期，巴山夜雨涨秋池。",
    stampDesc: "CHONGQING • MOUNTAIN",
    zipCode: "400000",
    sealSvg: (<svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="20,70 35,40 50,55 65,35 80,70" /><circle cx="60" cy="25" r="8" /><text x="50" y="82" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">重庆 • 山城</text></svg>),
  },
  "长沙": {
    sealName: "星城湘水",
    poem: "独立寒秋，湘江北去，橘子洲头。",
    stampDesc: "CHANGSHA • XIANG",
    zipCode: "410000",
    sealSvg: (<svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 60 Q 50 35, 80 60" /><circle cx="50" cy="30" r="6" /><path d="M44 30 L 50 18 L 56 30" /><text x="50" y="82" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">长沙 • 湘江</text></svg>),
  },
  "青岛": {
    sealName: "琴屿飘灯",
    poem: "红瓦绿树碧海天，琴屿飘灯映海湾。",
    stampDesc: "QINGDAO • SEA",
    zipCode: "266000",
    sealSvg: (<svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 65 Q 30 50, 50 60 Q 70 50, 85 65" /><circle cx="50" cy="30" r="8" /><path d="M42 30 L 50 15 L 58 30" /><text x="50" y="82" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">青岛 • 琴岛</text></svg>),
  },
};

const DEFAULT_CONFIG = {
  sealName: "华夏风物",
  poem: "读万卷书，行万里路，山河锦绣，皆在笔下。",
  stampDesc: "CHINA • TRAVEL",
  zipCode: "100000",
  sealSvg: (<svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="50" cy="50" r="45" strokeDasharray="3 1" /><polygon points="50,20 58,40 80,40 62,52 68,75 50,60 32,75 38,52 20,40 42,40" /><text x="50" y="84" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">华夏 • 山河</text></svg>),
};

interface PostcardFlipCardProps {
  itinerary: Itinerary;
  userName?: string;
  workNo?: string;
  onEditDayItems?: (dayIndex: number, newItems: ItineraryItem[]) => void;
}

export default function PostcardFlipCard({ itinerary, userName = "旅行者", workNo = "000000", onEditDayItems }: PostcardFlipCardProps) {
  const [isFlipped, setIsFlipped] = useState(false);
  const [stampTriggered, setStampTriggered] = useState(false);

  const destination = itinerary?.destination || "杭州";
  const cityConfig = CITY_CONFIGS[destination] || DEFAULT_CONFIG;

  useEffect(() => {
    setStampTriggered(false);
    const timer = setTimeout(() => setStampTriggered(true), 450);
    return () => clearTimeout(timer);
  }, [itinerary]);

  if (!itinerary) return null;

  return (
    <div className="space-y-4">
      {/* 顶栏控制条 */}
      <div className="flex justify-between items-center bg-background-tertiary border border-border px-4 py-2.5 rounded-sm no-print">
        <span className="text-xs font-mono text-foreground-secondary flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-primary animate-pulse" />
          <span>点击卡片或右侧按钮，体验 3D 物理翻转明信片</span>
        </span>
        <div className="flex gap-2">
          <Button size="small" icon={<Rotate3d className="w-3.5 h-3.5 inline" />} onClick={() => setIsFlipped(!isFlipped)}
            className="font-mono text-xs font-bold border-primary text-primary hover:bg-primary/5 h-7 rounded-sm">
            {isFlipped ? "看封面" : "看日程"}
          </Button>
          <Button size="small" icon={<Printer className="w-3.5 h-3.5 inline" />} onClick={() => window.print()}
            className="font-mono text-xs font-bold border-border-dark text-foreground-secondary hover:border-primary hover:text-primary h-7 rounded-sm">
            打印
          </Button>
        </div>
      </div>

      {/* 3D 卡片 */}
      <div className="postcard-perspective w-full min-h-[580px] cursor-pointer" onClick={() => setIsFlipped(!isFlipped)}>
        <div className={`postcard-inner ${isFlipped ? "is-flipped" : ""}`}>

          {/* 正面 */}
          <div className="postcard-front absolute top-0 left-0 w-full min-h-[580px] bg-background-secondary border-2 border-border-dark p-6 md:p-8 rounded-sm flex flex-col justify-between overflow-hidden">
            {/* 顶栏水印 */}
            <div className="flex justify-between items-center border-b border-border-light pb-3 mb-4 select-none">
              <span className="text-[10px] text-foreground-disabled font-mono tracking-widest uppercase flex items-center gap-1">
                <Mail className="w-3 h-3 text-primary-muted" /> TRIPCRAFT POSTCARD SERIES
              </span>
              <span className="text-[10px] text-foreground-disabled font-mono tracking-widest uppercase">
                NO. {String(workNo).padStart(8, "0").substring(0, 8)}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-12 gap-8 flex-1 items-stretch">
              {/* 左侧 */}
              <div className="md:col-span-7 flex flex-col justify-between space-y-4">
                <div className="space-y-3">
                  <div className="relative">
                    <span className="text-sm font-bold uppercase font-mono tracking-widest text-primary block">DESTINATION</span>
                    <h1 className="text-5xl md:text-6xl font-black font-display text-foreground tracking-tight uppercase leading-none mt-1">{destination}</h1>
                    <span className="text-[11px] font-mono text-foreground-tertiary tracking-widest uppercase absolute -top-1 right-2 block">{cityConfig.stampDesc}</span>
                  </div>
                  <p className="text-sm text-foreground-secondary italic font-display leading-relaxed border-l-2 border-primary-light pl-3 py-1">" {cityConfig.poem} "</p>
                </div>

                {/* 城市风情插图 — 像贴在明信片上的照片 */}
                <div className="relative w-full h-44 md:h-52 overflow-hidden border border-border-dark shadow-sm group">
                  <img
                    src={MAIN_IMAGES[destination] || DEFAULT_MAIN}
                    alt={`${destination} 风情`}
                    className="w-full h-full object-cover"
                    style={{ filter: "sepia(0.15) contrast(0.95) saturate(0.9)" }}
                    onError={(e) => { (e.target as HTMLImageElement).src = DEFAULT_MAIN; }}
                  />
                  {/* 胶带装饰 */}
                  <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-5 bg-primary/15 border border-primary/20 rotate-1 shadow-sm" />
                  {/* 底部标注 */}
                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/40 to-transparent px-3 py-1.5">
                    <span className="text-[9px] font-mono text-white/90 tracking-widest uppercase">{cityConfig.stampDesc}</span>
                  </div>
                </div>

                <div className="flex items-end justify-between gap-4">
                  <div className="space-y-1 font-display italic text-xs text-foreground-secondary leading-relaxed max-w-[70%]">
                    <p className="font-semibold text-foreground">{userName} 同志：</p>
                    <p className="indent-4">{itinerary.summary || "读万卷书，行万里路。"}</p>
                  </div>
                  <div className="text-primary hover:rotate-12 transition-transform duration-500 flex-shrink-0 select-none">{cityConfig.sealSvg}</div>
                </div>
              </div>

              {/* 分割线 */}
              <div className="hidden md:flex md:col-span-1 items-center justify-center relative">
                <div className="h-full border-l border-dashed border-border-dark" />
              </div>

              {/* 右侧 */}
              <div className="md:col-span-4 flex flex-col justify-between space-y-8 pl-0 md:pl-2">
                {/* 邮票与邮戳 */}
                <div className="flex justify-end items-start relative select-none">
                  <div className="w-24 h-32 bg-white p-1.5 border border-dashed border-foreground-disabled shadow-sm hover:rotate-2 transition-transform relative z-10 flex flex-col justify-between">
                    <div className="w-full h-20 overflow-hidden border border-border bg-[#F5EEE0]">
                      <img
                        src={STAMP_IMAGES[destination] || DEFAULT_STAMP}
                        alt={`${destination} 邮票`}
                        className="w-full h-full object-cover"
                        onError={(e) => { (e.target as HTMLImageElement).src = DEFAULT_STAMP; }}
                      />
                    </div>
                    <div className="text-[8px] font-mono font-bold text-center text-foreground-tertiary leading-none uppercase mt-1">CHINA POST ¥8.00</div>
                  </div>
                  {stampTriggered && (
                    <div className="absolute -left-10 top-4 z-20 w-28 h-28 border-2 border-primary text-primary rounded-full flex flex-col items-center justify-center p-1.5 font-mono text-[8px] font-bold tracking-tighter opacity-85 select-none animate-stamp-drop pointer-events-none uppercase">
                      <div className="border-b border-primary pb-0.5 mb-0.5">TRIPCRAFT</div>
                      <div className="text-[7px] text-center font-black leading-none">{destination} STATION</div>
                      <div className="my-0.5 px-1 bg-primary text-background-secondary text-[7px] leading-tight font-black">{workNo}</div>
                      <div className="text-[6px] text-center scale-90">{userName} TRAVELS</div>
                      <div className="border-t border-primary pt-0.5 mt-0.5">2026.07.30</div>
                    </div>
                  )}
                </div>

                {/* 收件人横线 */}
                <div className="space-y-4 font-mono select-none">
                  <div className="border-b border-border-dark pb-1 text-xs text-foreground-secondary flex justify-between">
                    <span>收件人:</span><span className="font-bold text-foreground font-display italic text-sm">{userName} 同志</span>
                  </div>
                  <div className="border-b border-border-dark pb-1 text-xs text-foreground-secondary">
                    <span>寄出地:</span><span className="font-semibold text-foreground ml-2">{destination} 智能微调算法中心</span>
                  </div>
                </div>

                {/* 邮编框 */}
                <div className="space-y-2 select-none">
                  <div className="text-[10px] font-mono font-bold text-foreground-tertiary uppercase">邮政编码 / ZIP CODE:</div>
                  <div className="flex gap-1.5">
                    {String(workNo).padStart(6, "0").split("").map((num, i) => (
                      <span key={i} className="w-7 h-8 border-2 border-error text-error font-mono font-black text-center text-lg flex items-center justify-center bg-white/50 rounded-sm">{num}</span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="border-t border-border-light pt-3 mt-4 text-center select-none">
              <span className="text-[9px] text-foreground-disabled font-mono tracking-widest uppercase">DESIGNED BY TRIPCRAFT DESIGN SYSTEM</span>
            </div>
          </div>

          {/* 背面 */}
          <div className="postcard-back absolute top-0 left-0 w-full min-h-[580px] bg-background-secondary border-2 border-border-dark p-6 md:p-8 rounded-sm">
            <div className="absolute top-4 right-4 text-[10px] text-foreground-disabled font-mono tracking-widest uppercase select-none no-print">TRIPCRAFT POSTCARD BACK</div>
            <ItineraryTimeline itinerary={itinerary} onEdit={onEditDayItems} />
          </div>

        </div>
      </div>
    </div>
  );
}