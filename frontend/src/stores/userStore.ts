import { create } from "zustand";
import {
  sendCode, register, login, getMe, logout as apiLogout,
  type UserInfo,
} from "../services/api";
import { API_BASE } from "../services/config";
import axios from "axios";

interface UserState {
  user: UserInfo | null;
  loading: boolean;
  isLoggedIn: boolean;

  sendCode: (email: string) => Promise<{ error?: string; dev_code?: string }>;
  register: (payload: { username: string; email: string; password: string; code: string }) => Promise<{ error?: string }>;
  login: (account: string, password: string) => Promise<{ error?: string }>;
  fetchMe: () => Promise<void>;
  logout: () => void;
}

export const useUserStore = create<UserState>((set) => ({
  user: null,
  loading: false,
  isLoggedIn: false,

  sendCode: async (email: string) => {
    set({ loading: true });
    try {
      const res = await sendCode(email);
      set({ loading: false });
      if (res.error) return { error: res.error };
      return { dev_code: res.dev_code };
    } catch {
      set({ loading: false });
      return { error: "发送验证码失败" };
    }
  },

  register: async (payload) => {
    set({ loading: true });
    try {
      const res = await register(payload);
      if (res.error) {
        set({ loading: false });
        return { error: res.error };
      }
      if (res.token) localStorage.setItem("tripcraft-token", res.token);
      set({ user: res.user || null, isLoggedIn: true, loading: false });
      return {};
    } catch {
      set({ loading: false });
      return { error: "注册失败" };
    }
  },

  login: async (account: string, password: string) => {
    set({ loading: true });
    try {
      const res = await login({ account, password });
      if (res.error) {
        set({ loading: false });
        return { error: res.error };
      }
      if (res.token) localStorage.setItem("tripcraft-token", res.token);
      set({ user: res.user || null, isLoggedIn: true, loading: false });
      return {};
    } catch {
      set({ loading: false });
      return { error: "登录失败" };
    }
  },

  fetchMe: async () => {
    const token = localStorage.getItem("tripcraft-token");
    if (!token) {
      set({ isLoggedIn: false, user: null });
      return;
    }
    try {
      const res = await getMe();
      if (res.error) {
        apiLogout();
        set({ isLoggedIn: false, user: null });
      } else {
        set({ user: res, isLoggedIn: true });
      }
    } catch {
      set({ isLoggedIn: false, user: null });
    }
  },

  logout: () => {
    const token = localStorage.getItem("tripcraft-token");
    if (token) {
      axios.post(`${API_BASE}/api/auth/logout`, {}, { headers: { Authorization: `Bearer ${token}` } }).catch(() => {});
    }
    apiLogout();
    set({ user: null, isLoggedIn: false });
  },
}));