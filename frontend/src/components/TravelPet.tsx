import { useState, useEffect, useRef } from "react";
import { Send, X, RotateCcw, Sparkles, Compass, Footprints, Flame, Landmark } from "lucide-react";

const PET_IMAGE = "https://mdn.alipayobjects.com/fecodex_image/afts/img/w2HuSYUISTsAAAAAWzAAAAgAejH3AQBr/original";

const QUICK_QUESTIONS = [
  { icon: <Compass className="w-3.5 h-3.5" />, text: "哪些城市最适合避暑和避寒？" },
  { icon: <Flame className="w-3.5 h-3.5" />, text: "西安和杭州有什么本地特色美食？" },
  { icon: <Landmark className="w-3.5 h-3.5" />, text: "推荐一些冷门但极具人文历史的景点" },
  { icon: <Footprints className="w-3.5 h-3.5" />, text: "首次独自旅行需要准备什么？" }
];

interface Msg { id: string; role: string; content: string; time: string }

export default function TravelPet() {
  const [isOpen, setIsOpen] = useState(false);
  const [showBubble, setShowBubble] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "咕咕~ 旅行者，我是你的专属邮政信差 Crafty！\n\n我是一只飞越过大江南北的信鸽。西安的肉夹馍、杭州的西湖雨、云南的大理风……我都了如指掌！\n\n你对哪里感到好奇？随时写封信告诉我！",
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => setShowBubble(true), 3000);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = textToSend || inputValue;
    if (!text.trim() || loading) return;

    const userMsg: Msg = { id: Date.now().toString(), role: "user", content: text, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
    setMessages(prev => [...prev, userMsg]);
    setInputValue("");
    setLoading(true);

    // 模拟 AI 回复（本地无 LLM，用预设回复）
    setTimeout(() => {
      const replies = [
        "咕咕！好问题~ 让我想想……推荐你试试成都的宽窄巷子配一碗盖碗茶，或者大理洱海边骑行看日落，都是绝佳体验！",
        "哈哈，旅行者的好奇心真旺盛！关于这个问题，你可以试试在搜索栏输入目的地和偏好，让 TripCraft 为你生成专属行程明信片哦~",
        "咕咕~ 作为一只有文化的信鸽，我建议你关注景点的开放时间和最佳游览季节。比如西湖春天看花、秋天赏月最合适！",
      ];
      const reply = replies[Math.floor(Math.random() * replies.length)];
      setMessages(prev => [...prev, { id: Date.now().toString() + "r", role: "assistant", content: reply, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
      setLoading(false);
    }, 1200);
  };

  const handleReset = () => {
    if (window.confirm("确定要清空与 Crafty 的往来信件吗？")) {
      setMessages([{ id: "welcome", role: "assistant", content: "信件已清空~ 随时再写信给我哦！", time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 print:hidden flex flex-col items-end">
      {/* 气泡提示 */}
      {showBubble && !isOpen && (
        <div onClick={() => setIsOpen(true)} className="mr-3 mb-3 w-56 p-3 bg-background border border-primary/40 rounded-lg shadow-xl cursor-pointer transition-all relative text-left select-none">
          <button onClick={(e) => { e.stopPropagation(); setShowBubble(false); }} className="absolute top-1.5 right-1.5 text-foreground-tertiary hover:text-primary p-0.5"><X className="w-3 h-3" /></button>
          <div className="text-xs font-display text-primary font-bold mb-1 flex items-center gap-1"><Sparkles className="w-3.5 h-3.5 animate-pulse" />信使 Crafty 来信：</div>
          <p className="text-[11px] text-foreground-secondary leading-relaxed">"咕咕！听说你要去远行？对各地气候美食有什么想打听的，点我写信询问吧~"</p>
        </div>
      )}

      {/* 桌宠图标 */}
      {!isOpen && (
        <div onClick={() => setIsOpen(true)} className="relative group p-1.5 bg-background border-2 border-primary rounded-lg shadow-lg hover:shadow-xl cursor-pointer select-none transition-all active:scale-95 animate-float w-[72px] h-[88px] flex flex-col items-center justify-center" title="点击召唤旅行小助理">
          <div className="absolute inset-0.5 border border-dashed border-primary/40 rounded-md" />
          <div className="w-12 h-12 overflow-hidden rounded-sm border border-border bg-[#F4ECD8] flex items-center justify-center">
            <img src={PET_IMAGE} alt="Crafty" className="w-full h-full object-cover" />
          </div>
          <span className="text-[9px] font-mono font-black text-primary tracking-widest mt-1 uppercase">CRAFTY</span>
          {showBubble && <div className="absolute -top-1 -right-1 w-3 h-3 bg-primary rounded-full border border-white animate-ping" />}
        </div>
      )}

      {/* 对话面板 */}
      {isOpen && (
        <div className="w-[360px] h-[500px] bg-background border-2 border-primary rounded-lg shadow-2xl flex flex-col overflow-hidden relative select-none">
          {/* 顶栏 */}
          <div className="bg-[#F4ECD8] border-b border-primary/30 p-3 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <span className="text-lg">📬</span>
              <span className="font-display font-bold text-foreground text-sm">Crafty 的复古旅行便函</span>
            </div>
            <div className="flex items-center gap-1.5">
              <button onClick={handleReset} title="清空" className="p-1 hover:bg-background rounded border border-transparent hover:border-primary/20 transition-all text-foreground-secondary hover:text-primary"><RotateCcw className="w-3.5 h-3.5" /></button>
              <button onClick={() => setIsOpen(false)} title="关闭" className="p-1 hover:bg-background rounded border border-transparent hover:border-primary/20 transition-all text-foreground-secondary hover:text-primary"><X className="w-4 h-4" /></button>
            </div>
          </div>

          {/* 消息区 */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0 scrollbar-thin">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-2.5 items-start ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                {msg.role === "assistant" && (
                  <div className="w-8 h-8 rounded-full border border-primary/40 p-0.5 bg-background overflow-hidden shrink-0"><img src={PET_IMAGE} alt="Crafty" className="w-full h-full object-cover rounded-full" /></div>
                )}
                <div className={`max-w-[78%] p-3 rounded-lg text-xs ${msg.role === "user" ? "bg-primary text-background rounded-tr-none" : "bg-[#F4ECD8] border border-primary/20 text-foreground-secondary rounded-tl-none"}`}>
                  <p className="whitespace-pre-line leading-relaxed">{msg.content}</p>
                  <p className={`text-[9px] mt-1 font-mono ${msg.role === "user" ? "text-background/60" : "text-foreground-tertiary"}`}>{msg.time}</p>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-2.5 items-start justify-start animate-pulse">
                <div className="w-8 h-8 rounded-full border border-primary/40 p-0.5 bg-background overflow-hidden shrink-0"><img src={PET_IMAGE} alt="Crafty" className="w-full h-full object-cover rounded-full" /></div>
                <div className="p-3 rounded-lg text-xs bg-[#F4ECD8] border border-primary/20 rounded-tl-none flex items-center gap-1.5 text-primary font-mono text-[10px] font-black"><span className="animate-bounce">💌</span><span>信件投递中...</span></div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 快捷问题 */}
          <div className="px-3 py-2 bg-[#F4ECD8]/40 border-t border-primary/10 shrink-0">
            <span className="text-[10px] font-display italic text-foreground-tertiary block mb-1.5 font-bold">点击信纸快速打听：</span>
            <div className="flex flex-wrap gap-1.5">
              {QUICK_QUESTIONS.map((item, idx) => (
                <button key={idx} onClick={() => handleSendMessage(item.text)} className="text-[10px] px-2 py-1 border border-border rounded-sm hover:border-primary hover:text-primary text-foreground-secondary transition-all flex items-center gap-1">{item.icon}{item.text}</button>
              ))}
            </div>
          </div>

          {/* 输入栏 */}
          <div className="p-3 bg-[#F4ECD8] border-t border-primary/30 shrink-0 flex items-center gap-2">
            <input type="text" value={inputValue} onChange={(e) => setInputValue(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") handleSendMessage(); }} placeholder="落笔写一封信..." disabled={loading}
              className="flex-1 bg-background border border-primary/30 rounded-sm py-1.5 px-3 text-xs text-foreground placeholder:text-foreground-tertiary focus:outline-none focus:border-primary h-8" />
            <button onClick={() => handleSendMessage()} disabled={!inputValue.trim() || loading}
              className="h-8 px-3 bg-primary text-background hover:bg-primary-dark disabled:bg-foreground-tertiary/40 transition-all rounded-sm border border-primary flex items-center justify-center gap-1 active:scale-95">
              <Send className="w-3 h-3" /><span className="text-[10px] font-mono font-bold tracking-widest uppercase">寄出</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}