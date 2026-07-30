import React from "react";
import { Link } from "react-router-dom";
import { Button } from "antd";
import { Compass, BookOpen, HeartHandshake, ShieldCheck, Mail } from "lucide-react";

export default function About() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12 flex-1 w-full space-y-12">
      
      {/* 封面：大面积暖米色纸张感与手绘大图 */}
      <section className="text-center md:text-left grid grid-cols-1 md:grid-cols-2 gap-8 items-center bg-background-secondary border border-border p-6 md:p-8 rounded-[2px]">
        <div className="space-y-4">
          <span className="text-[10px] uppercase font-bold font-mono tracking-widest text-primary border border-primary px-2 py-0.5 rounded-[2px]">
            关于本产品 / Preface
          </span>
          <h1 className="text-4xl font-black font-display text-foreground leading-tight tracking-tight uppercase">
            让旅行重新具有<br />
            “明信片般的温度”
          </h1>
          <p className="text-xs text-foreground-secondary leading-relaxed font-mono">
            TripCraft 是一款极具编辑美学、专为旅行者打造的智能定制系统。摒弃现代移动端浮躁繁杂的流光溢彩，回归纸张印刷、极细边框与纯粹留白的温度。
          </p>
          <div className="pt-2">
            <Link to="/">
              <Button className="h-10 bg-primary border-primary hover:bg-primary-dark text-white rounded-[2px] font-mono font-bold tracking-wider uppercase text-xs">
                开始定制我的攻略
              </Button>
            </Link>
          </div>
        </div>

        {/* 我们生成的精美复古地图图片 */}
        <div>
          <img
            src="https://mdn.alipayobjects.com/fecodex_image/afts/img/wsLCRZ5qPPoAAAAAgBAAAAgAejH3AQBr/original"
            alt="postcard world map"
            className="w-full h-56 object-cover border border-border-dark grayscale hover:grayscale-0 transition-all duration-500 rounded-[2px]"
          />
        </div>
      </section>

      {/* 核心特色板块（4栏） */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 font-mono text-xs">
        
        {/* 指南 */}
        <div className="bg-background-secondary border border-border p-5 rounded-[2px]">
          <Compass className="w-5 h-5 text-primary mb-3" />
          <h3 className="font-bold text-foreground font-display text-sm mb-2">智能定制</h3>
          <p className="text-foreground-secondary leading-relaxed">
            根据您设定的目的地城市及多维旅行偏好，系统快速输出极佳路线。
          </p>
        </div>

        {/* 地图 */}
        <div className="bg-background-secondary border border-border p-5 rounded-[2px]">
          <BookOpen className="w-5 h-5 text-primary mb-3" />
          <h3 className="font-bold text-foreground font-display text-sm mb-2">明信片书美学</h3>
          <p className="text-foreground-secondary leading-relaxed">
            完全摒弃发光阴影与乱象动效，秉持精排细线的纯正旅行书籍视觉。
          </p>
        </div>

        {/* 校验 */}
        <div className="bg-background-secondary border border-border p-5 rounded-[2px]">
          <ShieldCheck className="w-5 h-5 text-primary mb-3" />
          <h3 className="font-bold text-foreground font-display text-sm mb-2">多重校验</h3>
          <p className="text-foreground-secondary leading-relaxed">
            自动利用高德 LBS 实地数据校验景点真实性、价格合规性与轨迹距离合理度。
          </p>
        </div>

        {/* 反馈 */}
        <div className="bg-background-secondary border border-border p-5 rounded-[2px]">
          <HeartHandshake className="w-5 h-5 text-primary mb-3" />
          <h3 className="font-bold text-foreground font-display text-sm mb-2">反馈迭代</h3>
          <p className="text-foreground-secondary leading-relaxed">
            每一次点赞“有用”或改进反馈都回填模型，帮助微调模块不断优化算法。
          </p>
        </div>

      </section>

      {/* 产品理念及步骤介绍（纸张排版） */}
      <section className="border-t border-dashed border-border-light pt-10">
        <h2 className="text-2xl font-black font-display text-foreground uppercase tracking-tight mb-6">
          如何玩转 TripCraft？
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          
          <div className="space-y-2">
            <div className="text-3xl font-black font-display text-primary/30 font-mono">01.</div>
            <h4 className="font-bold text-foreground font-display text-base">选定并检索目的地</h4>
            <p className="text-xs text-foreground-secondary font-mono leading-relaxed">
              输入你心仪的国内热门城市。系统支持在杭州、成都、西安等 10+ 知名城市中快速定制，首期包含 50+ 精选高质感地标景点数据。
            </p>
          </div>

          <div className="space-y-2">
            <div className="text-3xl font-black font-display text-primary/30 font-mono">02.</div>
            <h4 className="font-bold text-foreground font-display text-base">一键获取精编图文</h4>
            <p className="text-xs text-foreground-secondary font-mono leading-relaxed">
              行程会按上午、中午、下午科学排列游玩时间，自动折算门票人均，并在 ECharts 及 Leaflet 中完美渲染，无惧多端展现。
            </p>
          </div>

          <div className="space-y-2">
            <div className="text-3xl font-black font-display text-primary/30 font-mono">03.</div>
            <h4 className="font-bold text-foreground font-display text-base">收藏与打印明信片</h4>
            <p className="text-xs text-foreground-secondary font-mono leading-relaxed">
              点击‘保存攻略’将其归档在‘我的攻略’卡片流中。不仅如此，您还可以点击‘导出/打印明信片’生成实物印刷排版，永久留存。
            </p>
          </div>

        </div>
      </section>

      {/* 页脚联系 */}
      <section className="bg-background-tertiary border border-border p-6 rounded-[2px] text-center space-y-3 font-mono text-xs">
        <Mail className="w-5 h-5 text-primary mx-auto" />
        <h4 className="font-bold text-foreground font-display text-sm">反馈与合作建议</h4>
        <p className="text-foreground-secondary">
          若有更多目的地数据扩展、微调大模型算法联合优化、或产品想法，欢迎联系 WeaveFox 团队：
        </p>
        <p className="text-primary font-bold">
          weavefox-vibe-team@alibaba-inc.com
        </p>
      </section>

    </div>
  );
}