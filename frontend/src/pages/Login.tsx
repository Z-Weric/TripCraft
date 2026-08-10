import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { message, Spin } from "antd";
import { Mail, KeyRound, ArrowLeft, User, Lock } from "lucide-react";
import { useUserStore } from "../stores/userStore";

export default function Login() {
  const navigate = useNavigate();
  const { login, register, sendCode, loading } = useUserStore();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [account, setAccount] = useState(""); // 用户名或邮箱
  const [password, setPassword] = useState("");
  const [regUsername, setRegUsername] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regCode, setRegCode] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [countdown, setCountdown] = useState(0);

  // 倒计时
  useState(() => {
    const timer = setInterval(() => {
      setCountdown((c) => (c > 0 ? c - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  });

  const handleSendCode = async () => {
    if (!regEmail.trim() || !regEmail.includes("@")) {
      message.warning("请输入有效邮箱");
      return;
    }
    const res = await sendCode(regEmail.trim());
    if (res.error) {
      message.error(res.error);
    } else {
      message.success("验证码已发送");
      setDevCode(res.dev_code || null);
      setCountdown(60);
    }
  };

  const handleLogin = async () => {
    if (!account.trim() || !password) {
      message.warning("请输入账号和密码");
      return;
    }
    const res = await login(account.trim(), password);
    if (res.error) {
      message.error(res.error);
    } else {
      message.success("登录成功");
      navigate("/home");
    }
  };

  const handleRegister = async () => {
    if (!regUsername.trim() || regUsername.length < 2) {
      message.warning("用户名至少 2 个字符");
      return;
    }
    if (!regEmail.trim() || !regEmail.includes("@")) {
      message.warning("请输入有效邮箱");
      return;
    }
    if (regPassword.length < 6) {
      message.warning("密码至少 6 个字符");
      return;
    }
    if (!regCode.trim()) {
      message.warning("请输入验证码");
      return;
    }
    const res = await register({
      username: regUsername.trim(),
      email: regEmail.trim(),
      password: regPassword,
      code: regCode.trim(),
    });
    if (res.error) {
      message.error(res.error);
    } else {
      message.success("注册成功");
      navigate("/home");
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <Link to="/" className="flex items-center gap-1 text-xs text-foreground-tertiary hover:text-primary transition-colors font-mono mb-6">
          <ArrowLeft className="w-3.5 h-3.5" />返回
        </Link>

        <div className="bg-background-secondary border-2 border-double border-primary rounded-sm p-8 shadow-lg">
          <div className="text-center mb-6">
            <h1 className="text-2xl font-black font-display tracking-tight text-foreground">
              Trip<span className="text-primary">Craft</span>
            </h1>
          </div>

          {/* 模式切换 */}
          <div className="flex border-b border-border-light mb-6">
            <button
              onClick={() => setMode("login")}
              className={`flex-1 pb-2 text-sm font-bold font-mono uppercase tracking-wider border-b-2 transition-all ${mode === "login" ? "border-primary text-primary" : "border-transparent text-foreground-tertiary"}`}
            >
              登录
            </button>
            <button
              onClick={() => setMode("register")}
              className={`flex-1 pb-2 text-sm font-bold font-mono uppercase tracking-wider border-b-2 transition-all ${mode === "register" ? "border-primary text-primary" : "border-transparent text-foreground-tertiary"}`}
            >
              注册
            </button>
          </div>

          {/* 登录表单 */}
          {mode === "login" && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-2 font-mono">用户名 / 邮箱</label>
                <div className="relative">
                  <User className="absolute left-3 top-2.5 h-4 w-4 text-foreground-tertiary z-10" />
                  <input
                    type="text"
                    value={account}
                    onChange={(e) => setAccount(e.target.value)}
                    placeholder="输入用户名或邮箱"
                    className="w-full pl-9 h-10 border-b border-t-0 border-l-0 border-r-0 border-border focus:border-primary outline-none bg-transparent font-semibold text-sm"
                    onKeyDown={(e) => { if (e.key === "Enter") handleLogin(); }}
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-2 font-mono">密码</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 h-4 w-4 text-foreground-tertiary z-10" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="输入密码"
                    className="w-full pl-9 h-10 border-b border-t-0 border-l-0 border-r-0 border-border focus:border-primary outline-none bg-transparent font-semibold text-sm"
                    onKeyDown={(e) => { if (e.key === "Enter") handleLogin(); }}
                  />
                </div>
              </div>
              <button
                onClick={handleLogin}
                disabled={loading}
                className="w-full h-10 bg-primary text-white font-bold rounded-sm hover:bg-primary-dark transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {loading ? <Spin size="small" /> : "登录"}
              </button>
            </div>
          )}

          {/* 注册表单 */}
          {mode === "register" && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-1.5 font-mono">用户名</label>
                <div className="relative">
                  <User className="absolute left-3 top-2.5 h-4 w-4 text-foreground-tertiary z-10" />
                  <input
                    type="text"
                    value={regUsername}
                    onChange={(e) => setRegUsername(e.target.value)}
                    placeholder="设置用户名（至少 2 字符）"
                    className="w-full pl-9 h-10 border-b border-t-0 border-l-0 border-r-0 border-border focus:border-primary outline-none bg-transparent font-semibold text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-1.5 font-mono">邮箱</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 h-4 w-4 text-foreground-tertiary z-10" />
                  <input
                    type="email"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="w-full pl-9 h-10 border-b border-t-0 border-l-0 border-r-0 border-border focus:border-primary outline-none bg-transparent font-semibold text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-1.5 font-mono">密码</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 h-4 w-4 text-foreground-tertiary z-10" />
                  <input
                    type="password"
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="设置密码（至少 6 字符）"
                    className="w-full pl-9 h-10 border-b border-t-0 border-l-0 border-r-0 border-border focus:border-primary outline-none bg-transparent font-semibold text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-foreground-secondary uppercase tracking-wider mb-1.5 font-mono">
                  验证码 {devCode && <span className="text-primary">（{devCode}）</span>}
                </label>
                <div>
                  <div className="relative">
                    <KeyRound className="absolute left-3 top-2.5 h-4 w-4 text-foreground-tertiary z-10" />
                    <input
                      type="text"
                      value={regCode}
                      onChange={(e) => setRegCode(e.target.value)}
                      placeholder="6 位验证码"
                      maxLength={6}
                      className="pl-9 pr-2 h-10 border-b border-t-0 border-l-0 border-r-0 border-border focus:border-primary outline-none bg-transparent font-semibold text-sm tracking-widest"
                      style={{ width: "calc(100% - 70px)" }}
                    />
                    <button
                      onClick={handleSendCode}
                      disabled={countdown > 0}
                      className="absolute right-0 top-0 h-10 px-3 text-xs font-mono font-bold text-primary hover:text-primary-dark transition-all disabled:opacity-50 whitespace-nowrap bg-transparent border-0"
                    >
                      {countdown > 0 ? `${countdown}s` : "发送"}
                    </button>
                  </div>
                </div>
              </div>
              <button
                onClick={handleRegister}
                disabled={loading}
                className="w-full h-10 bg-primary text-white font-bold rounded-sm hover:bg-primary-dark transition-all flex items-center justify-center gap-2 disabled:opacity-50 mt-2"
              >
                {loading ? <Spin size="small" /> : "注册"}
              </button>
              <p className="text-[10px] text-foreground-tertiary text-center font-mono">
                注册即同意 TripCraft 用户协议
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}