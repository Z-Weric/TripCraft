import axios from "axios";
import { API_BASE } from "./config";

export interface ItineraryItem {
  time: string;
  spot: string;
  poi_id?: number;
  category: string;
  duration: string;
  cost: number;
  lat: number;
  lng: number;
  note: string;
}

export interface DayPlan {
  day: number;
  items: ItineraryItem[];
  transport: string;
  day_cost: number;
}

export interface Itinerary {
  destination: string;
  days: number;
  itinerary: DayPlan[];
  total_cost: number;
  summary: string;
  error?: string;
}

export interface Verification {
  overall_valid?: boolean;
  structure_valid?: boolean;
  spots_valid: boolean;
  spots_total?: number;
  spots_verified?: number;
  verification_source?: "external" | "local" | "mixed" | "unavailable";
  spot_results?: Array<{ spot: string; valid: boolean; source: "external" | "local" | "unavailable" | "failed" }>;
  budget_valid: boolean;
  budget_total?: number;
  budget_limit?: number;
  budget_utilization?: number;
  calculation_valid?: boolean;
  calculated_total?: number;
  route_valid: boolean;
  errors?: Array<{ code: string; message: string; path?: string }>;
}

export interface GenerateResponse {
  itinerary: Itinerary;
  verification: Verification;
  generation_source: GenerationSource;
  validation_status: ValidationStatus;
  fallback_reason?: string | null;
  model_version: string;
}

export type GenerationSource = "llm" | "llm_repaired" | "planner";
export type ValidationStatus = "valid" | "repaired" | "fallback";

export interface GenerationMetadata {
  generation_source: GenerationSource;
  validation_status: ValidationStatus;
  fallback_reason?: string | null;
  model_version: string;
}

export interface GenerateRequest {
  destination: string;
  days: number;
  budget: number;
  preferences: string[];
  favorite_poi_ids?: number[];
}

export async function generateItinerary(req: GenerateRequest): Promise<GenerateResponse> {
  const { data } = await axios.post<GenerateResponse>(`${API_BASE}/api/generate`, req);
  return data;
}

export interface StreamCallbacks {
  onProgress?: (stage: string, message: string) => void;
  onDone: (itinerary: Itinerary, verification: Verification, metadata: GenerationMetadata) => void;
  onError: (message: string) => void;
}

export async function generateItineraryStream(req: GenerateRequest, callbacks: StreamCallbacks): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/generate/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!resp.ok) {
    let message = `请求失败（HTTP ${resp.status}）`;
    try {
      const error = await resp.json();
      if (Array.isArray(error.detail)) {
        message = error.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join("；") || message;
      } else if (typeof error.detail === "string") {
        message = error.detail;
      }
    } catch { /* keep the HTTP status fallback */ }
    callbacks.onError(message);
    return;
  }

  const reader = resp.body?.getReader();
  if (!reader) { callbacks.onError("流式连接失败"); return; }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const data = JSON.parse(line.slice(6));
        if (data.type === "progress") callbacks.onProgress?.(data.stage, data.message);
        else if (data.type === "done") callbacks.onDone(data.itinerary, data.verification, {
          generation_source: data.generation_source,
          validation_status: data.validation_status,
          fallback_reason: data.fallback_reason,
          model_version: data.model_version,
        });
        else if (data.type === "error") callbacks.onError(data.message);
      } catch { /* skip */ }
    }
  }
}

export async function submitFeedback(payload: {
  destination: string;
  days: number;
  budget: number;
  preferences: string[];
  feedback_type: string;
  comment?: string;
}): Promise<{ status: string; id: number }> {
  const { data } = await axios.post(`${API_BASE}/api/feedback`, payload);
  return data;
}

// ===== 行程持久化 =====

export interface TripSummary {
  id: number;
  destination: string;
  days: number;
  budget: number;
  summary: string;
  total_cost: number;
  preferences: string;
  created_at: string;
  user_rating?: number;
  is_public?: number;
}

export interface TripDetail extends Omit<TripSummary, "preferences"> {
  preferences: string[];
  itinerary: Itinerary;
  verification: Verification | null;
  model_version?: string;
  planner_version?: string;
  poi_version?: string | null;
  generation_source?: GenerationSource;
  validation_status?: ValidationStatus;
  fallback_reason?: string | null;
  version?: number;
}

export async function saveTrip(payload: {
  destination: string;
  days: number;
  budget: number;
  preferences: string[];
  itinerary: Itinerary;
  verification?: Verification | null;
  generation_source?: GenerationSource;
  validation_status?: ValidationStatus;
  fallback_reason?: string | null;
  model_version?: string;
}): Promise<{ status: string; id: number; guest?: boolean }> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const { data } = await axios.post(`${API_BASE}/api/itineraries`, payload, { headers });
  return data;
}

export async function listTrips(): Promise<TripSummary[]> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const { data } = await axios.get<TripSummary[]>(`${API_BASE}/api/itineraries`, { headers });
  return data;
}

export async function getTrip(id: number): Promise<TripDetail> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const { data } = await axios.get<TripDetail>(`${API_BASE}/api/itineraries/${id}`, { headers });
  return data;
}

export async function deleteTrip(id: number): Promise<{ status: string }> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = { Authorization: `Bearer ${token}` };
  const { data } = await axios.delete(`${API_BASE}/api/itineraries/${id}`, { headers });
  return data;
}

export async function chatWithPet(message: string, destination?: string): Promise<{ reply: string }> {
  const { data } = await axios.post(`${API_BASE}/api/chat`, { message, destination });
  return data;
}

// ===== 用户认证 =====

export interface UserInfo {
  id: number;
  email: string;
  username?: string;
  nickname: string;
  avatar: string;
  created_at?: string;
}

export async function sendCode(email: string): Promise<{ status?: string; error?: string; dev_code?: string }> {
  const { data } = await axios.post(`${API_BASE}/api/auth/send-code`, { email });
  return data;
}

export async function register(payload: { username: string; email: string; password: string; code: string }): Promise<{ status?: string; token?: string; user?: UserInfo; error?: string }> {
  const { data } = await axios.post(`${API_BASE}/api/auth/register`, payload);
  return data;
}

export async function login(payload: { account: string; password: string }): Promise<{ status?: string; token?: string; user?: UserInfo; error?: string }> {
  const { data } = await axios.post(`${API_BASE}/api/auth/login`, payload);
  return data;
}

export async function getMe(): Promise<UserInfo & { error?: string }> {
  const token = localStorage.getItem("tripcraft-token");
  const { data } = await axios.get(`${API_BASE}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}

export async function updateProfile(payload: { nickname?: string; avatar?: string }): Promise<{ status?: string; error?: string }> {
  const token = localStorage.getItem("tripcraft-token");
  const { data } = await axios.put(`${API_BASE}/api/auth/profile`, payload, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}

export function getAuthToken(): string | null {
  return localStorage.getItem("tripcraft-token");
}

// ===== 景点详情 + 收藏 =====

export async function getPoiDetail(poiId: number): Promise<any> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const { data } = await axios.get(`${API_BASE}/api/pois/${poiId}/detail`, { headers });
  return data;
}

export async function toggleFavorite(poiId: number, favorited: boolean): Promise<{ favorited: boolean }> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = { Authorization: `Bearer ${token}` };
  if (favorited) {
    await axios.delete(`${API_BASE}/api/pois/${poiId}/favorite`, { headers });
    return { favorited: false };
  } else {
    await axios.post(`${API_BASE}/api/pois/${poiId}/favorite`, {}, { headers });
    return { favorited: true };
  }
}

export async function submitReview(poiId: number, rating: number, comment: string): Promise<{ status: string }> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = { Authorization: `Bearer ${token}` };
  const { data } = await axios.post(`${API_BASE}/api/pois/${poiId}/review`, { rating, comment }, { headers });
  return data;
}

export function isLoggedIn(): boolean {
  return !!localStorage.getItem("tripcraft-token");
}

export function logout() {
  localStorage.removeItem("tripcraft-token");
}

// ===== AI 攻略文章 =====

export async function generateArticle(payload: {
  itinerary: Itinerary;
  packed_items: string[];
  extra_foods?: { name: string; note?: string; cost?: number }[];
}): Promise<{ status?: string; article?: string; error?: string }> {
  const { data } = await axios.post(`${API_BASE}/api/article/generate`, payload);
  return data;
}

// ===== 社区 =====

export interface PostSummary {
  id: number;
  title: string;
  city: string;
  tags: string;
  cover_image: string;
  view_count: number;
  like_count: number;
  comment_count: number;
  created_at: string;
  author: { id: number; nickname: string };
}

export interface PostDetail {
  id: number;
  title: string;
  content: string;
  city: string;
  tags: string;
  trip_json: string | null;
  view_count: number;
  like_count: number;
  comment_count: number;
  created_at: string;
  author: { id: number; nickname: string; avatar: string };
}

export async function listPosts(page: number = 1, tag?: string, city?: string): Promise<{ posts: PostSummary[]; total: number; page: number; pages: number }> {
  const params: any = { page };
  if (tag) params.tag = tag;
  if (city) params.city = city;
  const { data } = await axios.get(`${API_BASE}/api/posts`, { params });
  return data;
}

export async function getPost(id: number): Promise<PostDetail & { error?: string }> {
  const { data } = await axios.get<PostDetail & { error?: string }>(`${API_BASE}/api/posts/${id}`);
  return data;
}

export async function createPost(payload: {
  title: string;
  content: string;
  city: string;
  tags: string;
  trip_id?: number;
  trip_json?: string;
}): Promise<{ status?: string; id?: number; error?: string }> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = { Authorization: `Bearer ${token}` };
  const { data } = await axios.post(`${API_BASE}/api/posts`, payload, { headers });
  return data;
}

export async function deletePost(id: number): Promise<{ status?: string }> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = { Authorization: `Bearer ${token}` };
  const { data } = await axios.delete(`${API_BASE}/api/posts/${id}`, { headers });
  return data;
}

export async function likePost(id: number): Promise<{ status?: string; liked?: boolean }> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = { Authorization: `Bearer ${token}` };
  const { data } = await axios.post(`${API_BASE}/api/posts/${id}/like`, {}, { headers });
  return data;
}

export async function unlikePost(id: number): Promise<{ status?: string; liked?: boolean }> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = { Authorization: `Bearer ${token}` };
  const { data } = await axios.delete(`${API_BASE}/api/posts/${id}/like`, { headers });
  return data;
}

export interface PostComment {
  id: string;
  content: string;
  user_nickname: string;
  created_at: string;
}

export async function getComments(postId: number): Promise<PostComment[]> {
  const { data } = await axios.get(`${API_BASE}/api/posts/${postId}/comments`);
  return data;
}

export async function createComment(postId: number, content: string): Promise<{ status?: string; id?: string }> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = { Authorization: `Bearer ${token}` };
  const { data } = await axios.post(`${API_BASE}/api/posts/${postId}/comments`, { content }, { headers });
  return data;
}

// ===== 行程分享 =====

export async function createShareLink(tripId: number): Promise<{ url: string; token: string; expires_at: string }> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const { data } = await axios.post(`${API_BASE}/api/share/${tripId}`, {}, { headers });
  return data;
}

export async function getSharedTrip(token: string): Promise<TripDetail> {
  const { data } = await axios.get<TripDetail>(`${API_BASE}/api/share/${token}`);
  return data;
}

export async function exportTrip(tripId: number, format: "json" | "markdown" = "json"): Promise<{ format: string; content: string }> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const { data } = await axios.get(`${API_BASE}/api/export/${tripId}`, { params: { format }, headers });
  return data;
}

// ===== 天气 =====

export interface WeatherDay {
  date: string;
  week: string;
  dayweather: string;
  nightweather: string;
  daytemp: string;
  nighttemp: string;
  daywind: string;
  daypower: string;
  temp_diff: number;
  clothing: string;
}

export async function getWeather(city: string, days: number = 3): Promise<{ city: string; forecasts: WeatherDay[]; message?: string }> {
  const { data } = await axios.get(`${API_BASE}/api/weather`, { params: { city, days } });
  return data;
}

// ===== Packing 清单 =====

export interface PackingList {
  destination: string;
  days: number;
  season: string;
  categories: Record<string, string[]>;
  total_items: number;
}

export async function getPackingList(city: string, days: number, preferences: string[] = []): Promise<PackingList> {
  const { data } = await axios.get<PackingList>(`${API_BASE}/api/packing`, {
    params: { city, days, preferences: preferences.join(",") },
  });
  return data;
}

export async function chatWithPetStream(
  message: string,
  destination: string | undefined,
  onThinking: (text: string) => void,
  onContent: (chunk: string) => void,
  onDone: () => void,
): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, destination }),
  });

  const reader = resp.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const data = JSON.parse(line.slice(6));
        if (data.type === "thinking") onThinking(data.content);
        else if (data.type === "content") onContent(data.content);
        else if (data.type === "done") onDone();
      } catch { /* skip */ }
    }
  }
  onDone();
}

export async function updateTrip(id: number, itinerary: Itinerary): Promise<{ status: string; version: number; changed: boolean; action_types?: string[] }> {
  const token = localStorage.getItem("tripcraft-token");
  const headers = { Authorization: `Bearer ${token}` };
  const { data } = await axios.put(`${API_BASE}/api/itineraries/${id}`, { itinerary }, { headers });
  return data;
}

// ===== 训练样本审核（仅 TRAINING_REVIEWER_EMAILS 白名单账号） =====

export type TrainingReviewStatus = "pending" | "needs_adjudication" | "approved" | "rejected";
export type TrainingLabel = "gold" | "silver" | "rejected";
export type TrainingDimensionValue = "pass" | "minor_issue" | "reject";

export type TrainingReviewDimensions = Record<
  "poi_accuracy" | "route_reasonableness" | "budget" | "schedule" | "readability" | "preference_match",
  TrainingDimensionValue
>;

export interface TrainingReviewCandidate {
  trip_id: number;
  destination: string;
  days: number;
  budget: number;
  preferences: string[];
  itinerary: Itinerary;
  verification: Verification | null;
  traceability: Pick<TripDetail, "model_version" | "planner_version" | "poi_version" | "generation_source" | "validation_status">;
  review: {
    status: TrainingReviewStatus;
    final_label: TrainingLabel | null;
    decision_count: number;
    decisions: Array<{ label: TrainingLabel; dimensions: TrainingReviewDimensions; error_codes: string[]; created_at: string | null }>;
  };
}

function trainingReviewHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem("tripcraft-token")}` };
}

export async function listTrainingReviewCandidates(status: TrainingReviewStatus = "pending"): Promise<{ items: TrainingReviewCandidate[]; status: TrainingReviewStatus }> {
  const { data } = await axios.get(`${API_BASE}/api/training-reviews/candidates`, { params: { status }, headers: trainingReviewHeaders() });
  return data;
}

export async function submitTrainingReview(tripId: number, payload: { label: TrainingLabel; dimensions: TrainingReviewDimensions; error_codes: string[] }): Promise<{ status: TrainingReviewStatus; final_label: TrainingLabel | null; decision_count: number }> {
  const { data } = await axios.post(`${API_BASE}/api/training-reviews/${tripId}`, payload, { headers: trainingReviewHeaders() });
  return data;
}

export async function resolveTrainingReview(tripId: number, label: TrainingLabel): Promise<{ status: TrainingReviewStatus; final_label: TrainingLabel }> {
  const { data } = await axios.post(`${API_BASE}/api/training-reviews/${tripId}/resolve`, { label }, { headers: trainingReviewHeaders() });
  return data;
}
