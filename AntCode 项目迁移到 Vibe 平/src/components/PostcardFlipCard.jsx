import React, { useState, useEffect } from "react";
import { useShallow } from "zustand/react/shallow";
import { Rotate3d, Mail, Heart, Printer, Sparkles, MapPin, Landmark, Award } from "lucide-react";
import { Button, message } from "antd";
import ItineraryTimeline from "./ItineraryTimeline.jsx";

// 10个城市专属地标、印章和诗意文案配置
const CITY_CONFIGS = {
  "杭州": {
    sealName: "西湖烟雨",
    poem: "水光潋滟晴方好，山色空蒙雨亦奇。",
    stampDesc: "HANGZHOU • WEST LAKE",
    zipCode: "310000",
    sealSvg: (
      <svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="50" cy="50" r="45" strokeDasharray="3 3" />
        <circle cx="50" cy="50" r="38" />
        <path d="M25 65 C 35 55, 45 55, 55 65 C 65 75, 75 75, 85 65" />
        <path d="M30 65 L 75 65" />
        <rect x="42" y="35" width="16" height="20" rx="1" />
        <line x1="50" y1="35" x2="50" y2="25" />
        <text x="50" y="80" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">杭州 • 三潭印月</text>
      </svg>
    )
  },
  "西安": {
    sealName: "古都长安",
    poem: "春风得意马蹄疾，一日看尽长安花。",
    stampDesc: "XI'AN • CHANG'AN",
    zipCode: "710000",
    sealSvg: (
      <svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="50" cy="50" r="45" strokeDasharray="4 2" />
        <circle cx="50" cy="50" r="38" />
        <path d="M35 70 L 65 70 M 40 70 L 40 55 L 60 55 L 60 70 M 43 55 L 43 42 L 57 42 L 57 55 M 47 42 L 50 30 L 53 42" />
        <text x="50" y="82" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">西安 • 大雁塔印</text>
      </svg>
    )
  },
  "成都": {
    sealName: "天府锦官",
    poem: "晓看红湿处，花重锦官城。",
    stampDesc: "CHENGDU • SHU",
    zipCode: "610000",
    sealSvg: (
      <svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="50" cy="50" r="45" />
        <circle cx="50" cy="50" r="40" strokeDasharray="1 2" />
        {/* 极简熊猫 */}
        <circle cx="50" cy="50" r="20" />
        <circle cx="42" cy="42" r="6" fill="currentColor" />
        <circle cx="58" cy="42" r="6" fill="currentColor" />
        <circle cx="46" cy="48" r="3" fill="white" />
        <circle cx="54" cy="48" r="3" fill="white" />
        <text x="50" y="82" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">成都 • 大熊猫馆</text>
      </svg>
    )
  },
  "大理": {
    sealName: "苍山洱海",
    poem: "下关风，上关花，苍山雪，洱海月。",
    stampDesc: "DALI • ERHAI",
    zipCode: "671000",
    sealSvg: (
      <svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="50" cy="50" r="45" strokeDasharray="5 5" />
        <path d="M25 45 C 35 35, 45 55, 55 45 C 65 35, 75 55, 80 45" strokeWidth="1.5" />
        <path d="M20 70 C 35 60, 50 80, 80 70" />
        <polygon points="45,45 50,20 55,45" />
        <text x="50" y="82" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">大理 • 苍山洱海</text>
      </svg>
    )
  },
  "厦门": {
    sealName: "鹭岛琴音",
    poem: "鹭飞鱼跃琴声起，半城海水半城春。",
    stampDesc: "XIAMEN • AMOY",
    zipCode: "361000",
    sealSvg: (
      <svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="50" cy="50" r="45" />
        <path d="M20 65 Q 35 55, 50 65 T 80 65" />
        <path d="M45 65 L 45 40 L 55 40 L 55 65" />
        <polygon points="43,40 50,25 57,40" />
        <circle cx="50" cy="32" r="2" fill="currentColor" />
        <text x="50" y="82" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">厦门 • 鼓浪屿塔</text>
      </svg>
    )
  }
};

const DEFAULT_CONFIG = {
  sealName: "华夏风物",
  poem: "读万卷书，行万里路，山河锦绣，皆在笔下。",
  stampDesc: "CHINA • TRAVEL",
  zipCode: "100000",
  sealSvg: (
    <svg className="w-16 h-16 opacity-75" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="50" cy="50" r="45" strokeDasharray="3 1" />
      <polygon points="50,20 58,40 80,40 62,52 68,75 50,60 32,75 38,52 20,40 42,40" />
      <text x="50" y="84" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor" stroke="none">华夏 • 锦绣山河</text>
    </svg>
  )
};

export default function PostcardFlipCard({ itinerary, userName = "临心", workNo = "549395" }) {
  const [isFlipped, setIsFlipped] = useState(false);
  const [stampTriggered, setStampTriggered] = useState(false);

  const destination = itinerary?.destination || "杭州";
  const cityConfig = CITY_CONFIGS[destination] || DEFAULT_CONFIG;

  // 每次攻略改变时，重置并触发极具仪式感的“盖印章”动画
  useEffect(() => {
    setStampTriggered(false);
    const timer = setTimeout(() => {
      setStampTriggered(true);
    }, 450);
    return () => clearTimeout(timer);
  }, [itinerary?.id]);

  if (!itinerary) return null;

  const handleCardClick = (e) => {
    // 如果点击的是按钮、链接或 Timeline，不触发翻转
    if (
      e.target.closest("button") ||
      e.target.closest("a") ||
      e.target.closest(".ant-timeline") ||
      e.target.closest(".no-flip-zone")
    ) {
      return;
    }
    setIsFlipped(!isFlipped);
  };

  const triggerPrint = () => {
    window.print();
  };

  return (
    <div className="space-y-4">
      
      {/* 顶栏控制条 */}
      <div className="flex justify-between items-center bg-background-tertiary border border-border px-4 py-2.5 rounded-[2px] no-print">
        <span className="text-xs font-mono text-foreground-secondary flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-primary animate-pulse" />
          <span>点击卡片或右侧按钮，体验 3D 物理翻转明信片</span>
        </span>
        <div className="flex gap-2">
          <Button
            size="small"
            icon={<Rotate3d className="w-3.5 h-3.5 inline" />}
            onClick={() => setIsFlipped(!isFlipped)}
            className="font-mono text-xs font-bold border-primary text-primary hover:bg-primary/5 h-7 rounded-[2px]"
          >
            {isFlipped ? "看封面 (正面)" : "看日程 (背面)"}
          </Button>
          <Button
            size="small"
            icon={<Printer className="w-3.5 h-3.5 inline" />}
            onClick={triggerPrint}
            className="font-mono text-xs font-bold border-border-dark text-foreground-secondary hover:border-primary hover:text-primary h-7 rounded-[2px]"
          >
            打印实物
          </Button>
        </div>
      </div>

      {/* 3D 卡片外层视角容器 */}
      <div className="postcard-perspective w-full min-h-[580px] cursor-pointer" onClick={handleCardClick}>
        <div className={`postcard-inner shadow-sm hover:shadow-md transition-shadow duration-300 ${isFlipped ? "is-flipped" : ""}`}>
          
          {/* =========================================================================
              明信片正面 (Postcard Front)
              ========================================================================= */}
          <div className="postcard-front absolute top-0 left-0 w-full min-h-[580px] bg-background-secondary border-2 border-border-dark p-6 md:p-8 rounded-[2px] flex flex-col justify-between overflow-hidden">
            
            {/* 顶栏装饰水印 */}
            <div className="flex justify-between items-center border-b border-border-light pb-3 mb-4 select-none">
              <span className="text-[10px] text-foreground-disabled font-mono tracking-widest uppercase flex items-center gap-1">
                <Mail className="w-3 h-3 text-primary-muted" />
                TRIPCRAFT POSTCARD SERIES
              </span>
              <span className="text-[10px] text-foreground-disabled font-mono tracking-widest uppercase">
                NO. {itinerary.id?.substring(0, 8) || "00000000"}
              </span>
            </div>

            {/* 中间核心物理明信片板式 */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-8 flex-1 items-stretch">
              
              {/* 左侧：精美风景插画 + 城市文化印章 */}
              <div className="md:col-span-7 flex flex-col justify-between space-y-6">
                
                {/* 城市特色标题大字与诗词 (手绘印刷感) */}
                <div className="space-y-3">
                  <div className="relative">
                    <span className="text-sm font-bold uppercase font-mono tracking-widest text-primary block">DESTINATION</span>
                    <h1 className="text-5xl md:text-6xl font-black font-display text-foreground tracking-tight uppercase leading-none mt-1">
                      {destination}
                    </h1>
                    {/* 微缩拼音/英文 */}
                    <span className="text-[11px] font-mono text-foreground-tertiary tracking-widest uppercase absolute -top-1 right-2 block">
                      {cityConfig.stampDesc}
                    </span>
                  </div>
                  
                  {/* 经典诗句 - 杂志式斜体 */}
                  <p className="text-sm text-foreground-secondary italic font-display leading-relaxed border-l-2 border-primary-light pl-3 py-1">
                    “ {cityConfig.poem} ”
                  </p>
                </div>

                {/* 精美封面大图 */}
                <div className="w-full h-44 rounded-[2px] overflow-hidden border border-border relative select-none">
                  <img
                    src="https://mdn.alipayobjects.com/fecodex_image/afts/img/JzGoSpm__QUAAAAAgBAAAAgAejH3AQBr/original"
                    alt="cover view"
                    className="w-full h-full object-cover grayscale contrast-[1.1] opacity-90 mix-blend-multiply"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-background-secondary/80 to-transparent" />
                  <div className="absolute bottom-2 left-3 text-xs font-mono font-bold text-foreground-secondary uppercase tracking-widest">
                    🗺️ {destination} • 城市风情手绘印相
                  </div>
                </div>

                {/* 左下：手写寄语与城市文化圆章 */}
                <div className="flex items-end justify-between gap-4">
                  <div className="space-y-1 font-display italic text-xs text-foreground-secondary leading-relaxed max-w-[70%]">
                    <p className="font-semibold text-foreground">临心 同志：</p>
                    <p className="indent-4">
                      {itinerary.summary || "读万卷书，行万里路。这份为你精心裁剪的明信片旅行攻略，带上它，去感受风的自由与大地的呼吸吧。"}
                    </p>
                    <p className="text-right text-[10px] text-foreground-tertiary font-mono not-italic mt-2">
                      ◇ 2026年7月30日 笔于西溪
                    </p>
                  </div>
                  
                  {/* 城市特色印章 - 红色/赤陶橙斑驳 SVG */}
                  <div className="text-primary hover:rotate-12 transition-transform duration-500 flex-shrink-0 select-none">
                    {cityConfig.sealSvg}
                  </div>
                </div>

              </div>

              {/* 中间古典分割锯齿线 */}
              <div className="hidden md:flex md:col-span-1 items-center justify-center relative">
                <div className="h-full border-l border-dashed border-border-dark" />
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-background-secondary px-1 text-foreground-disabled font-mono text-[9px] rotate-90 tracking-widest uppercase select-none">
                  TRIPCRAFT
                </div>
              </div>

              {/* 右侧：贴邮票处 + 邮戳盖章 + 信件横线 + 邮政编码框 */}
              <div className="md:col-span-4 flex flex-col justify-between space-y-8 pl-0 md:pl-2">
                
                {/* 右上角：邮票与盖章 */}
                <div className="flex justify-end items-start relative select-none">
                  
                  {/* 物理复古邮票 */}
                  <div className="w-24 h-32 bg-white p-1.5 border border-dashed border-foreground-disabled shadow-sm hover:rotate-2 transition-transform relative z-10 flex flex-col justify-between">
                    <div className="w-full h-20 bg-background-tertiary overflow-hidden border border-border">
                      <img
                        src="https://mdn.alipayobjects.com/fecodex_image/afts/img/pFaSS4_ImuEAAAAAYPAAAAgAejH3AQBr/original"
                        alt="stamp"
                        className="w-full h-full object-cover grayscale"
                      />
                    </div>
                    <div className="text-[8px] font-mono font-bold text-center text-foreground-tertiary leading-none uppercase mt-1">
                      CHINA POST ¥8.00
                    </div>
                  </div>

                  {/* 物理专属复古邮戳：在邮票上层，盖上去的动效 */}
                  {stampTriggered && (
                    <div className="absolute -left-10 top-4 z-20 w-28 h-28 border-2 border-primary text-primary rounded-full flex flex-col items-center justify-center p-1.5 font-mono text-[8px] font-bold tracking-tighter opacity-85 select-none animate-stamp-drop pointer-events-none uppercase">
                      <div className="border-b border-primary pb-0.5 mb-0.5">TRIPCRAFT 🏣</div>
                      <div className="text-[7px] text-center font-black leading-none">{destination} STATION</div>
                      <div className="my-0.5 px-1 bg-primary text-background-secondary text-[7px] leading-tight font-black">{workNo}</div>
                      <div className="text-[6px] text-center scale-90">{userName} TRAVELS</div>
                      <div className="border-t border-primary pt-0.5 mt-0.5">2026.07.30</div>
                    </div>
                  )}

                </div>

                {/* 右中：收件人寄语横线 (信纸横线) */}
                <div className="space-y-4 font-mono select-none">
                  <div className="border-b border-border-dark pb-1 text-xs text-foreground-secondary flex justify-between">
                    <span>收件人 (To):</span>
                    <span className="font-bold text-foreground font-display italic text-sm">{userName} 同志</span>
                  </div>
                  <div className="border-b border-border-dark pb-1 text-xs text-foreground-secondary">
                    <span>地址 (Add):</span>
                    <span className="font-semibold text-foreground ml-2">杭州市余杭区文一西路969号</span>
                  </div>
                  <div className="border-b border-border-dark pb-1 text-xs text-foreground-secondary flex justify-between">
                    <span>寄出地 (From):</span>
                    <span className="font-semibold text-foreground">{destination} 智能微调算法中心</span>
                  </div>
                </div>

                {/* 右下：6格标准红色邮政编码框 */}
                <div className="space-y-2 select-none">
                  <div className="text-[10px] font-mono font-bold text-foreground-tertiary uppercase flex items-center gap-1">
                    <span>✉️ 邮政编码 / ZIP CODE:</span>
                  </div>
                  <div className="flex gap-1.5">
                    {/* 使用当前工号数字填入邮编框以增强代入感 */}
                    {String(workNo).padStart(6, "0").split("").map((num, i) => (
                      <span
                        key={i}
                        className="w-7 h-8 border-2 border-error text-error font-mono font-black text-center text-lg flex items-center justify-center bg-white/50 rounded-[1px]"
                      >
                        {num}
                      </span>
                    ))}
                  </div>
                </div>

              </div>

            </div>

            {/* 物理明信片底部签名 */}
            <div className="border-t border-border-light pt-3 mt-4 text-center select-none">
              <span className="text-[9px] text-foreground-disabled font-mono tracking-widest uppercase">
                ◇ DESIGNED BY TRIPCRAFT DESIGN SYSTEM • ALL RIGHTS RESERVED ◇
              </span>
            </div>

          </div>

          {/* =========================================================================
              明信片背面 (Postcard Back)
              ========================================================================= */}
          <div className="postcard-back absolute top-0 left-0 w-full min-h-[580px] bg-background-secondary border-2 border-border-dark p-6 md:p-8 rounded-[2px]">
            <div className="absolute top-4 right-4 text-[10px] text-foreground-disabled font-mono tracking-widest uppercase select-none no-print">
              TRIPCRAFT POSTCARD BACK
            </div>
            {/* 时间线内容 */}
            <div className="no-flip-zone">
              <ItineraryTimeline itinerary={itinerary} />
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}