import React, { useState, useEffect, useRef } from "react";
import { Send, X, RotateCcw, Sparkles, MessageSquare, Compass, Footprints, Flame, Landmark } from "lucide-react";
import vibeSdk from "@alipay/weavefox-vibe-web";

// 之前用 AI 生成的邮差信鸽头像
const PET_IMAGE = "https://mdn.alipayobjects.com/fecodex_image/afts/img/w2HuSYUISTsAAAAAWzAAAAgAejH3AQBr/original";

// 快捷推荐问题列表
const QUICK_QUESTIONS = [
  { icon: <Compass className="w-3.5 h-3.5" />, text: "哪些城市最适合避暑和避寒？☀️" },
  { icon: <Flame className="w-3.5 h-3.5" />, text: "西安和杭州有什么本地特色美食？🍲" },
  { icon: <Landmark className="w-3.5 h-3.5" />, text: "推荐一些冷门但极具人文历史的景点景致 🧭" },
  { icon: <Footprints className="w-3.5 h-3.5" />, text: "首次独自旅行需要准备哪些怀旧物件？🧳" }
];

export default function TravelPet() {
  const [isOpen, setIsOpen] = useState(false);
  const [showBubble, setShowBubble] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      content: "咕咕~ 旅行者，我是你的专属邮政信差 **Crafty**！📬\n\n我是一只飞越过大江南北的信鸽。西安的肉夹馍、杭州的西湖雨、云南的大理风……我都了如指掌！\n\n你对哪里感到好奇？随时写封信告诉我，我立刻帮你去 AI 邮局送信打听！💌",
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [loading, setLoading] = useState(false);
  
  const messagesEndRef = useRef(null);

  // 挂载 3 秒后显示气泡提示，提示用户可以交互
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowBubble(true);
    }, 3000);
    return () => clearTimeout(timer);
  }, []);

  // 消息自动滚动到底部
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading]);

  // 关闭气泡
  const handleCloseBubble = (e) => {
    e.stopPropagation();
    setShowBubble(false);
  };

  // 切换信箱展开状态
  const handleToggleOpen = () => {
    setIsOpen(!isOpen);
    setShowBubble(false);
  };

  // 重置对话
  const handleReset = () => {
    if (window.confirm("确定要清空你与 Crafty 的往来信件吗？")) {
      setMessages([
        {
          id: "welcome",
          role: "assistant",
          content: "箱底已经拂去尘埃，信件已全部归档。咕咕~ 我们重新开始投递心事吧！📬",
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    }
  };

  // 发送消息
  const handleSendMessage = async (textToSend) => {
    const text = textToSend || inputValue.trim();
    if (!text || loading) return;

    // 清空输入框
    if (!textToSend) {
      setInputValue("");
    }

    const userMsg = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      // 拼接历史对话，以便 AI 理解上下文，限制在最近 4 轮以内
      const recentMessages = messages.slice(-8);
      const conversationHistory = recentMessages.map(m => {
        return `${m.role === 'user' ? '旅行者' : 'Crafty'}: ${m.content}`;
      }).join("\n");

      const systemPrompt = `你是一个生活在 1912 年古典邮政时代的旅行信使，名叫 'Crafty'。你是一只博学多才、周游世界的邮差信鸽。
你说话风格温和儒雅、温润细腻，经常使用 '咕咕~' 作为语气词，同时对中国各大城市的气候、历史、地道美食、人文景点了如指掌。
请用富有诗意、温暖而具有历史厚重感的文字回答旅行者的提问，不要使用死板的AI客服腔调。
请确保在 150 字以内解答问题。字里行间要有写在复古明信片上的纸墨质感。可以使用 Markdown 的加粗增强可读性。`;

      const prompt = `这里是当前旅行者与信使 Crafty 的对话记录：\n${conversationHistory}\n旅行者最新来信: ${text}\n\n请作为 Crafty 撰写你的回信（直接输出回信内容，字数在150字以内，带有“咕咕~”语气）：`;

      // TODO: 【AI API 实现】此处正使用 WeaveFox Vibe 平台的 vibeSdk.ai.completion 完成桌宠智能对话。
      //       如果您拥有私有化的 AI 接口或大语言模型（如通义千问、OpenAI 或公司内部网关），
      //       可以：
      //       1. 将此处调用修改为 fetch 请求您自己的后端 Functions（如 functions/aiRouter.js）。
      //       2. 在后端进行 API 密钥（API-Key）鉴权、实现流式输出（Server-Sent Events）。
      //       3. 在前端用 ReadableStream 完成打字机式流式对话效果。
      const response = await vibeSdk.ai.completion({
        system: systemPrompt,
        prompt: prompt
      });

      if (response?.success && response?.data?.text) {
        setMessages(prev => [...prev, {
          id: `ai-${Date.now()}`,
          role: "assistant",
          content: response.data.text.trim(),
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
      } else {
        throw new Error("AI 邮差由于雨雪天延误了回信...");
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        id: `ai-err-${Date.now()}`,
        role: "assistant",
        content: "咕咕... 抱歉旅行者，天空下起了大雨，我的翅膀被打湿了，没能成功联络到 AI 邮政总局。请稍后再寄一封信试试吧！⛈️",
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 print:hidden flex flex-col items-end">
      
      {/* 1. 弹出气泡提示（小浮窗未展开时，阶段性显示） */}
      {showBubble && !isOpen && (
        <div 
          onClick={handleToggleOpen}
          className="mr-3 mb-3 w-56 p-3 bg-[#FBF7F0] border border-primary/40 rounded-lg shadow-xl cursor-pointer hover:scale-102 transition-all duration-300 relative animate-[fadeInUp_0.3s_ease-out] text-left select-none"
        >
          {/* 复古齿孔贴边 */}
          <div className="absolute inset-1 border border-dashed border-primary/20 rounded-[6px]" />
          <button 
            onClick={handleCloseBubble}
            className="absolute top-1.5 right-1.5 text-foreground-tertiary hover:text-primary transition-colors p-0.5 rounded"
          >
            <X className="w-3 h-3" />
          </button>
          <div className="text-xs font-serif text-primary font-bold mb-1 flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-primary animate-pulse" />
            信使 Crafty 来信：
          </div>
          <p className="text-[11px] text-foreground-secondary leading-relaxed font-sans">
            “咕咕！听说你要去远行？对各地的气候美食有什么想打听的，点我写信询问吧~ 📬”
          </p>
          {/* 小气泡小三角 */}
          <div className="absolute bottom-[-6px] right-8 w-3 h-3 bg-[#FBF7F0] border-r border-b border-primary/30 rotate-45" />
        </div>
      )}

      {/* 2. 核心桌宠小摆件形象 */}
      {!isOpen && (
        <div 
          onClick={handleToggleOpen}
          className="relative group p-1.5 bg-[#FBF7F0] border-2 border-primary rounded-lg shadow-lg hover:shadow-xl cursor-pointer select-none transition-all duration-300 active:scale-95 animate-[float_3s_infinite_ease-in-out] w-18 h-22 flex flex-col items-center justify-center"
          title="点击召唤旅行小助理"
        >
          {/* 红蓝经典航空封边斑马线 */}
          <div className="absolute inset-0.5 border border-dashed border-[#C9622A]/40 rounded-[5px]" />
          
          {/* 桌宠主图：带复古双线框 */}
          <div className="w-13 h-13 overflow-hidden rounded-[3px] border border-border bg-[#F4ECD8] relative flex items-center justify-center">
            <img 
              src={PET_IMAGE} 
              alt="Crafty" 
              className="w-full h-full object-cover grayscale-15 group-hover:grayscale-0 group-hover:scale-105 transition-all duration-500"
            />
            {/* 邮戳角印 */}
            <div className="absolute -bottom-1 -right-1 w-6 h-6 border border-primary/20 rounded-full flex items-center justify-center bg-[#FBF7F0]/80 scale-75 rotate-12">
              <span className="text-[6px] font-mono text-primary/60">C.P</span>
            </div>
          </div>

          {/* 名字标签 */}
          <span className="text-[9px] font-mono font-black text-primary tracking-widest mt-1.5 scale-90 group-hover:text-primary-dark uppercase">
            CRAFTY
          </span>

          {/* 右上角红点/提示 */}
          {showBubble && (
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-primary rounded-full border border-white animate-ping" />
          )}
        </div>
      )}

      {/* 3. 信笺式对话面板 */}
      {isOpen && (
        <div className="w-[360px] h-[500px] bg-[#FBF7F0] border-2 border-primary rounded-lg shadow-2xl flex flex-col overflow-hidden animate-[fadeInUp_0.25s_ease-out] relative select-none">
          
          {/* 大马士革复古网格水印背景叠加 */}
          <div className="absolute inset-0 bg-[radial-gradient(#2C1810_1px,transparent_1px)] [background-size:16px_16px] opacity-[0.015] pointer-events-none" />
          
          {/* 顶栏：复古信封封口/信箱盖头样式 */}
          <div className="bg-[#F4ECD8] border-b border-primary/30 p-3 flex items-center justify-between relative shrink-0">
            {/* 红蓝斜条纹路贴边 */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-[repeating-linear-gradient(-45deg,#C9622A,#C9622A_6px,#FBF7F0_6px,#FBF7F0_12px,#2B5797_12px,#2B5797_18px,#FBF7F0_18px,#FBF7F0_24px)] opacity-60" />
            
            <div className="flex items-center gap-2 mt-1">
              <div className="w-5 h-5 rounded-full border border-primary bg-primary/10 flex items-center justify-center">
                <span className="text-[10px] font-mono text-primary font-bold">📬</span>
              </div>
              <span className="font-serif font-bold text-foreground text-sm tracking-wide">
                Crafty 的复古旅行便函
              </span>
            </div>

            <div className="flex items-center gap-1.5 mt-1">
              {/* 重置按钮 */}
              <button 
                onClick={handleReset}
                title="拂去尘埃(清空往来信件)"
                className="p-1 hover:bg-[#FBF7F0] rounded border border-transparent hover:border-primary/20 transition-all text-foreground-secondary hover:text-primary active:scale-95"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              {/* 关闭按钮 */}
              <button 
                onClick={handleToggleOpen}
                title="密封信封(收起助手)"
                className="p-1 hover:bg-[#FBF7F0] rounded border border-transparent hover:border-primary/20 transition-all text-foreground-secondary hover:text-primary active:scale-95"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* 消息滚动区域 */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0 relative scrollbar-thin">
            {messages.map((msg) => {
              const isAi = msg.role === "assistant";
              return (
                <div 
                  key={msg.id}
                  className={`flex gap-2.5 items-start ${isAi ? "justify-start" : "justify-end"}`}
                >
                  {/* AI 头像 */}
                  {isAi && (
                    <div className="w-8 h-8 rounded-full border border-primary/40 p-0.5 bg-background overflow-hidden shrink-0 shadow-sm">
                      <img src={PET_IMAGE} alt="Crafty" className="w-full h-full object-cover rounded-full" />
                    </div>
                  )}

                  {/* 消息气泡 */}
                  <div className={`max-w-[78%] flex flex-col ${isAi ? "items-start" : "items-end"}`}>
                    <div 
                      className={`p-3 rounded-lg text-xs leading-relaxed font-sans relative ${
                        isAi 
                          ? "bg-[#F4ECD8] border border-primary/20 text-[#2C1810] shadow-sm rounded-tl-none whitespace-pre-wrap" 
                          : "bg-[#2B5797]/10 border border-[#2B5797]/30 text-[#1F3D7A] rounded-tr-none"
                      }`}
                    >
                      {/* 信纸细横线装饰（仅 AI 回复有） */}
                      {isAi && (
                        <div className="absolute inset-0 bg-[linear-gradient(rgba(44,24,16,0.03)_1px,transparent_1px)] [background-size:100%_20px] pointer-events-none rounded-lg" />
                      )}
                      
                      {/* 文字内容 */}
                      <p className="relative z-10 font-sans tracking-wide">
                        {msg.content}
                      </p>
                    </div>
                    {/* 时间 */}
                    <span className="text-[9px] font-mono text-foreground-tertiary mt-1 px-1">
                      {msg.time}
                    </span>
                  </div>

                  {/* 用户头像占位 */}
                  {!isAi && (
                    <div className="w-8 h-8 rounded-full border border-[#2B5797]/30 bg-[#2B5797]/10 flex items-center justify-center shrink-0">
                      <span className="text-[10px] font-bold text-[#1F3D7A]">旅</span>
                    </div>
                  )}
                </div>
              );
            })}

            {/* AI 正在送信状态（loading） */}
            {loading && (
              <div className="flex gap-2.5 items-start justify-start animate-pulse">
                <div className="w-8 h-8 rounded-full border border-primary/40 p-0.5 bg-background overflow-hidden shrink-0 shadow-sm">
                  <img src={PET_IMAGE} alt="Crafty" className="w-full h-full object-cover rounded-full" />
                </div>
                <div className="max-w-[78%]">
                  <div className="p-3 rounded-lg text-xs bg-[#F4ECD8] border border-primary/20 text-foreground-secondary rounded-tl-none relative flex flex-col items-center justify-center gap-1.5 w-44">
                    <div className="flex items-center gap-1.5 text-primary font-mono text-[10px] font-black">
                      <span className="animate-bounce">💌</span>
                      <span>信件投递中...</span>
                    </div>
                    {/* 极简折线飞行模拟 */}
                    <div className="w-full h-0.5 bg-dashed border-b border-primary/30 animate-[pulse_1.5s_infinite]" />
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* 快捷推荐问题栏 */}
          <div className="px-3 py-2 bg-[#F4ECD8]/40 border-t border-primary/10 shrink-0">
            <span className="text-[10px] font-serif italic text-foreground-tertiary block mb-1.5 font-bold tracking-wider">
              ◇ 点击信纸快速打听：
            </span>
            <div className="flex flex-wrap gap-1.5">
              {QUICK_QUESTIONS.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(item.text)}
                  disabled={loading}
                  className="px-2.5 py-1 text-[10px] font-sans text-foreground-secondary bg-[#FBF7F0] border border-primary/20 rounded-full hover:border-primary hover:text-primary hover:bg-[#F4ECD8] disabled:opacity-50 transition-all duration-200 text-left flex items-center gap-1 select-none cursor-pointer"
                >
                  {item.icon}
                  <span>{item.text.replace(/ [☀️🍲🧭🧳]/, "")}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 输入底部栏 */}
          <div className="p-3 bg-[#F4ECD8] border-t border-primary/30 shrink-0 relative flex items-center gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSendMessage();
              }}
              placeholder="落笔写一封信(询问气候、美食、风物)..."
              disabled={loading}
              className="flex-1 bg-[#FBF7F0] border border-primary/30 rounded-[3px] py-1.5 px-3 text-xs text-foreground placeholder:text-foreground-tertiary focus:outline-none focus:border-primary font-sans h-8"
            />
            
            <button
              onClick={() => handleSendMessage()}
              disabled={!inputValue.trim() || loading}
              className="h-8 px-3 bg-primary text-[#FBF7F0] hover:bg-primary-dark disabled:bg-foreground-tertiary/40 disabled:text-foreground-tertiary transition-all duration-200 rounded-[3px] border border-primary flex items-center justify-center gap-1 cursor-pointer active:scale-95 shadow-sm"
              title="投递信件"
            >
              <Send className="w-3 h-3" />
              <span className="text-[10px] font-mono font-bold tracking-widest uppercase">寄出</span>
            </button>
          </div>

        </div>
      )}

      {/* 自定义局部滚动条和浮动特效样式 */}
      <style>{`
        @keyframes float {
          0%, 100% {
            transform: translateY(0);
          }
          50% {
            transform: translateY(-8px);
          }
        }
        .scrollbar-thin::-webkit-scrollbar {
          width: 5px;
        }
        .scrollbar-thin::-webkit-scrollbar-track {
          background: transparent;
        }
        .scrollbar-thin::-webkit-scrollbar-thumb {
          background-color: #C9622A;
          border-radius: 3px;
        }
      `}</style>
    </div>
  );
}