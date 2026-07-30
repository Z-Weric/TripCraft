import React, { useState } from "react";
import { Form, Input, Select, InputNumber, Checkbox, Button, message } from "antd";
import { MapPin, Calendar, CircleDollarSign, Compass } from "lucide-react";

const { Option } = Select;

const PREFERENCES = ["自然风光", "美食", "历史文化", "购物", "亲子"];
const HOT_CITIES = [
  { name: "杭州", desc: "烟雨西湖" },
  { name: "成都", desc: "天府熊猫" },
  { name: "西安", desc: "大唐长安" },
  { name: "大理", desc: "风花雪月" },
  { name: "厦门", desc: "鹭岛琴音" },
  { name: "苏州", desc: "江南园林" },
  { name: "南京", desc: "六朝金陵" },
  { name: "重庆", desc: "洪崖山城" },
  { name: "长沙", desc: "星城风味" },
  { name: "青岛", desc: "红瓦绿树" }
];

export default function SearchBar({ onGenerate, loading }) {
  const [destination, setDestination] = useState("杭州");
  const [days, setDays] = useState(3);
  const [budget, setBudget] = useState(2000);
  const [preferences, setPreferences] = useState(["自然风光", "美食", "亲子"]);

  const handleSubmit = () => {
    if (!destination.trim()) {
      message.warning("请输入或选择一个旅行目的地");
      return;
    }
    onGenerate({
      destination: destination.trim(),
      days,
      budget,
      preferences,
    });
  };

  return (
    <div className="relative my-8 px-1 md:px-3 pt-6 pb-2">
      {/* ─── 底层卡片 1：老旧复古航空信纸 (带红蓝斜条纹边缘) ─── */}
      <div className="absolute inset-0 bg-[#FBF7F0] border border-[#E4D7C1] rounded-lg shadow-sm transform rotate-[-2deg] -translate-x-2 translate-y-1.5 pointer-events-none overflow-hidden">
        {/* 航空条纹边缘 (Airmail borders) */}
        <div 
          className="absolute inset-0 p-1 opacity-25"
          style={{
            backgroundImage: "repeating-linear-gradient(-45deg, #C9622A, #C9622A 12px, #FFF9F0 12px, #FFF9F0 24px, #5A80A5 24px, #5A80A5 36px, #FFF9F0 36px, #FFF9F0 48px)"
          }}
        />
        <div className="absolute inset-1.5 bg-[#FFFDF9]" />
        {/* 复古文字装饰 */}
        <div className="absolute bottom-5 left-6 text-[9px] text-[#8B7355] font-mono tracking-widest opacity-40 transform rotate-[-2deg] select-none uppercase">
          ✦ PAR AVION / BY AIR MAIL ✦
        </div>
      </div>

      {/* ─── 底层卡片 2：古典牛皮纸明信片 (Kraft Paper) ─── */}
      <div className="absolute inset-0 bg-[#F4ECD8] border border-[#DFCEAF] rounded-lg shadow-md transform rotate-[1.5deg] translate-x-2.5 translate-y-2 pointer-events-none flex flex-col justify-between p-4 overflow-hidden">
        {/* 模拟老旧发黄的纸张边缘和质感 */}
        <div className="w-1/4 h-[1px] bg-[#E8DAB8] opacity-70 mb-1" />
        <div className="self-end w-24 h-16 border border-[#E8DAB8]/80 border-dashed opacity-40 flex items-center justify-center text-[9px] text-[#8B7355] font-mono scale-90">
          STAMP PLACE
        </div>
      </div>

      {/* ─── 底部交叠的复古小邮票 (Vintage Scalloped Stamp) ─── */}
      <div className="absolute -top-6 right-8 w-18 h-22 bg-[#FFFDF7] p-1 shadow-[0_3px_10px_rgba(44,24,16,0.15)] border border-[#DFCEAF] transform rotate-[12deg] pointer-events-none z-0 hidden sm:block overflow-hidden">
        {/* 邮票内边框和指南针图案 */}
        <div className="absolute inset-0 bg-[#FFFDF9] border-2 border-double border-primary/30 m-0.5 flex flex-col items-center justify-between p-1">
          <div className="text-[7px] font-bold text-primary/60 font-mono scale-75 tracking-wider">POSTAGE</div>
          <Compass className="w-7 h-7 text-primary/40 stroke-[1.25]" />
          <div className="text-[8px] font-bold text-[#5A4032] font-mono scale-90">¥ 1.20</div>
        </div>
        {/* 邮票四周边角齿状孔 (纯CSS模拟圆弧剪裁孔) */}
        <div className="absolute inset-x-0 -top-[3px] flex justify-between px-1">
          {[...Array(9)].map((_, i) => (
            <div key={i} className="w-1.5 h-1.5 bg-[#FBF7F0] rounded-full border border-[#DFCEAF]/40" />
          ))}
        </div>
        <div className="absolute inset-x-0 -bottom-[3px] flex justify-between px-1">
          {[...Array(9)].map((_, i) => (
            <div key={i} className="w-1.5 h-1.5 bg-[#FBF7F0] rounded-full border border-[#DFCEAF]/40" />
          ))}
        </div>
        <div className="absolute inset-y-0 -left-[3px] flex flex-col justify-between py-1">
          {[...Array(11)].map((_, i) => (
            <div key={i} className="w-1.5 h-1.5 bg-[#FBF7F0] rounded-full border border-[#DFCEAF]/40" />
          ))}
        </div>
        <div className="absolute inset-y-0 -right-[3px] flex flex-col justify-between py-1">
          {[...Array(11)].map((_, i) => (
            <div key={i} className="w-1.5 h-1.5 bg-[#FBF7F0] rounded-full border border-[#DFCEAF]/40" />
          ))}
        </div>
      </div>

      {/* ─── 顶层主表单卡片 (明信片正面精美视觉) ─── */}
      <div className="relative z-10 bg-[#FFFDF9] border-[3px] border-double border-primary rounded-lg p-6 md:p-8 shadow-[0_8px_25px_rgba(44,24,16,0.1)] transform rotate-[-0.2deg] hover:rotate-0 transition-transform duration-300">
        
        {/* 淡淡的复古经典邮戳水印背景 */}
        <div className="absolute top-3 right-10 opacity-10 pointer-events-none select-none">
          <svg className="w-20 h-20 text-primary" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="1.2">
            <circle cx="50" cy="50" r="42" strokeDasharray="3 3" />
            <circle cx="50" cy="50" r="32" />
            <line x1="8" y1="50" x2="92" y2="50" strokeWidth="1" />
            <text x="50" y="44" textAnchor="middle" fontSize="5.5" fontWeight="bold" fill="currentColor" tracking-wider="true">TRIPCRAFT</text>
            <text x="50" y="62" textAnchor="middle" fontSize="5.5" fill="currentColor" tracking-widest="true">POSTAL 1912</text>
          </svg>
        </div>

        {/* 标题 */}
        <div className="text-sm font-bold text-foreground-secondary uppercase tracking-widest mb-5 font-mono flex items-center gap-1.5">
          <span className="text-primary">◇</span> 规划你的个性化明信片旅程
        </div>

        <Form layout="vertical" onFinish={handleSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            
            {/* 目的地 */}
            <div className="md:col-span-1">
              <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-2 font-mono">
                目的地 / City
              </label>
              <div className="relative">
                <MapPin className="absolute left-3 top-2.5 h-4 w-4 text-foreground-tertiary" />
                <Input
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  placeholder="你想去哪里？"
                  className="pl-9 h-10 bg-background border-b border-t-0 border-l-0 border-r-0 border-border hover:border-primary focus:border-primary rounded-none shadow-none text-foreground font-semibold placeholder:text-foreground-disabled"
                />
              </div>
            </div>

            {/* 天数 */}
            <div>
              <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-2 font-mono">
                天数 / Days
              </label>
              <div className="relative">
                <Calendar className="absolute left-3 top-2.5 h-4 w-4 text-foreground-tertiary z-10" />
                <Select
                  value={days}
                  onChange={setDays}
                  className="w-full h-10 custom-select"
                  style={{ height: '40px' }}
                >
                  <Option value={2}>2 天行程</Option>
                  <Option value={3}>3 天精选</Option>
                  <Option value={5}>5 天深度</Option>
                </Select>
              </div>
            </div>

            {/* 预算 */}
            <div>
              <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-2 font-mono">
                人均预算 (元)
              </label>
              <div className="relative">
                <CircleDollarSign className="absolute left-3 top-2.5 h-4 w-4 text-foreground-tertiary z-10" />
                <InputNumber
                  value={budget}
                  onChange={(v) => setBudget(v || 2000)}
                  min={500}
                  max={50000}
                  step={500}
                  className="w-full pl-9 h-10 custom-input-number rounded-none border-b border-t-0 border-l-0 border-r-0 border-border hover:border-primary focus:border-primary"
                  controls={false}
                />
              </div>
            </div>

            {/* 按钮 */}
            <div>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                className="w-full h-10 bg-primary border-primary hover:bg-primary-dark active:scale-[0.98] transition-transform text-white font-bold tracking-wider rounded-[2px] text-sm uppercase"
              >
                {loading ? "生成攻略中..." : "生成旅行攻略"}
              </Button>
            </div>

          </div>

          {/* 热门城市快捷选择 */}
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <span className="text-xs text-foreground-tertiary font-mono mr-2">快捷推荐:</span>
            {HOT_CITIES.map((city) => (
              <button
                key={city.name}
                type="button"
                onClick={() => setDestination(city.name)}
                className={`px-3 py-1 text-xs rounded-full border transition-all duration-200 transform hover:-translate-y-0.5 active:scale-95 flex items-center gap-1 cursor-pointer ${
                  destination === city.name
                    ? "bg-primary/10 border-primary text-primary font-bold shadow-none"
                    : "bg-transparent border-border text-foreground-secondary hover:border-primary hover:text-primary"
                }`}
              >
                <span>📍 {city.name}</span>
                <span className="opacity-75 text-[10px] font-normal font-sans">· {city.desc}</span>
              </button>
            ))}
          </div>

          {/* 偏好筛选 */}
          <div className="mt-6 pt-4 border-t border-dashed border-border">
            <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-3 font-mono">
              选择你的旅行偏好 / Preferences
            </label>
            <Checkbox.Group
              value={preferences}
              onChange={(vals) => setPreferences(vals)}
              className="w-full"
            >
              <div className="flex flex-wrap gap-2.5">
                {PREFERENCES.map((pref) => {
                  const isActive = preferences.includes(pref);
                  return (
                    <Checkbox
                      key={pref}
                      value={pref}
                      className="custom-pref-checkbox"
                      style={{ margin: 0 }}
                    >
                      <span
                        className={`px-4 py-1.5 rounded-full text-xs font-semibold cursor-pointer transition-all border inline-block ${
                          isActive
                            ? "bg-primary border-primary text-background-secondary shadow-none animate-press-rebound"
                            : "bg-background-secondary border-border text-foreground-secondary hover:border-primary hover:text-primary"
                        }`}
                      >
                        {pref}
                      </span>
                    </Checkbox>
                  );
                })}
              </div>
            </Checkbox.Group>
          </div>
        </Form>
      </div>

      {/* 隐藏 Antd 自带 checkbox 的原始框，仅展现精美自定义标签 */}
      <style>{`
        .custom-pref-checkbox .ant-checkbox {
          display: none !important;
        }
        .custom-pref-checkbox.ant-checkbox-wrapper-checked span {
          color: inherit !important;
        }
        .custom-pref-checkbox span {
          padding-left: 0 !important;
          padding-right: 0 !important;
        }
        .custom-select .ant-select-selector {
          border-top: 0 !important;
          border-left: 0 !important;
          border-right: 0 !important;
          border-bottom: 1px solid #D4C5B0 !important;
          border-radius: 0 !important;
          box-shadow: none !important;
          background: transparent !important;
          padding-left: 36px !important;
        }
        .custom-select.ant-select-focused .ant-select-selector {
          border-bottom: 2px solid #C9622A !important;
        }
        .custom-input-number .ant-input-number-input {
          height: 38px !important;
          background: transparent !important;
          box-shadow: none !important;
          font-weight: 600;
        }
      `}</style>
    </div>
  );
}