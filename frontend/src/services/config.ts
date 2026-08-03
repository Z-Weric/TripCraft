/**
 * 环境配置 — 通过 Vite 环境变量注入，支持多环境部署
 */
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export { API_BASE };