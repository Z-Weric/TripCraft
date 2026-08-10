import { useNavigate } from "react-router-dom";
import { Mail, Compass, Sparkles } from "lucide-react";
import { useUserStore } from "../stores/userStore";

export default function Welcome() {
  const navigate = useNavigate();
  useUserStore(); // 初始化 store

  const handleGuest = () => {
    navigate("/");
  };

  const handleLogin = () => {
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6 relative overflow-hidden">
      {/* 背景装饰 */}
      <div className="absolute inset-0 opacity-[0.04] pointer-events-none"
        style={{ backgroundImage: "url(/stamps/default-main.png)", backgroundSize: "cover", backgroundPosition: "center" }}
      />

      <div className="relative z-10 w-full max-w-md text-center">
        {/* Logo */}
        <div className="mb-8">
          <h1 className="text-5xl font-black font-display tracking-tight text-foreground mb-2">
            Trip<span className="text-primary">Craft</span>
          </h1>
          <p className="text-xs font-mono text-foreground-tertiary tracking-widest uppercase">
            ◇ 复古明信片式的旅行手册生成系统 ◇
          </p>
        </div>

        {/* 功能亮点 */}
        <div className="flex items-center justify-center gap-6 mb-8 text-xs text-foreground-secondary font-mono">
          <span className="flex items-center gap-1"><Sparkles className="w-3.5 h-3.5 text-primary" />AI 智能规划</span>
          <span className="flex items-center gap-1"><Compass className="w-3.5 h-3.5 text-primary" />3126 景点</span>
        </div>

        {/* 选择按钮 */}
        <div className="space-y-3">
          <button
            onClick={handleLogin}
            className="w-full h-12 bg-primary text-white font-bold rounded-sm hover:bg-primary-dark transition-all flex items-center justify-center gap-2 text-sm tracking-wider uppercase"
          >
            <Mail className="w-4 h-4" />
            邮箱登录 / 注册
          </button>

          <button
            onClick={handleGuest}
            className="w-full h-12 border-2 border-border text-foreground-secondary font-bold rounded-sm hover:border-primary hover:text-primary transition-all flex items-center justify-center gap-2 text-sm tracking-wider uppercase"
          >
            <Compass className="w-4 h-4" />
            游客体验
          </button>
        </div>

        <p className="text-[10px] text-foreground-tertiary font-mono mt-6 leading-relaxed">
          游客可生成行程但不会保存 · 登录后可保存历史、收藏景点、评分评论
        </p>
      </div>
    </div>
  );
}