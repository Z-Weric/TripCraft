import { create } from "zustand";
import {
  generateItineraryStream,
  saveTrip,
  updateTrip,
  type Itinerary,
  type Verification,
  type GenerateRequest,
  type ItineraryItem,
  type GenerationMetadata,
} from "../services/api";

let _currentTripId: number | null = null;
export const getCurrentTripId = () => _currentTripId;

interface TripState {
  loading: boolean;
  itinerary: Itinerary | null;
  verification: Verification | null;
  generationMetadata: GenerationMetadata | null;
  error: string | null;
  lastRequest: GenerateRequest | null;
  progressStage: string;
  progressMessage: string;

  generate: (req: GenerateRequest) => Promise<void>;
  regenerate: () => void;
  clear: () => void;
  editDayItems: (dayIndex: number, newItems: ItineraryItem[]) => void;
}

export const useTripStore = create<TripState>((set, get) => ({
  loading: false,
  itinerary: null,
  verification: null,
  generationMetadata: null,
  error: null,
  lastRequest: null,
  progressStage: "",
  progressMessage: "",

  generate: async (req: GenerateRequest) => {
    set({
      loading: true,
      error: null,
      lastRequest: req,
      itinerary: null,
      verification: null,
      generationMetadata: null,
      progressStage: "start",
      progressMessage: "正在启动生成...",
    });

    try {
      await generateItineraryStream(req, {
        onProgress: (stage, message) => {
          set({ progressStage: stage, progressMessage: message });
        },
        onDone: (itinerary, verification, generationMetadata) => {
          set({
            itinerary,
            verification,
            generationMetadata,
            loading: false,
            progressStage: "",
            progressMessage: "",
          });
          // 自动保存到历史记录（仅已登录用户）
          const token = localStorage.getItem("tripcraft-token");
          if (token) {
            saveTrip({
              destination: req.destination,
              days: req.days,
              budget: req.budget,
              preferences: req.preferences,
              itinerary,
              verification,
              ...generationMetadata,
            }).then((res) => { _currentTripId = res.id; }).catch(() => {/* 保存失败不阻塞用户 */});
          } else {
            _currentTripId = 0; // 游客模式
          }
        },
        onError: (message) => {
          set({
            error: message,
            loading: false,
            progressStage: "",
            progressMessage: "",
          });
        },
      });
    } catch (e: any) {
      set({
        error: e?.message || "生成失败，请检查后端服务是否启动",
        loading: false,
        progressStage: "",
        progressMessage: "",
      });
    }
  },

  regenerate: () => {
    const { lastRequest, generate } = get();
    if (lastRequest) generate(lastRequest);
  },

  clear: () => {
    set({
      loading: false,
      itinerary: null,
      verification: null,
      generationMetadata: null,
      error: null,
      lastRequest: null,
      progressStage: "",
      progressMessage: "",
    });
  },

  editDayItems: (dayIndex: number, newItems: ItineraryItem[]) => {
    set((state) => {
      if (!state.itinerary) return {};
      const newItinerary = { ...state.itinerary };
      const days = [...newItinerary.itinerary];
      const day = { ...days[dayIndex] };
      day.items = newItems;
      // 重新计算当天花费
      day.day_cost = newItems.reduce((s, i) => s + (i.cost || 0), 0) + 15; // +15 交通
      days[dayIndex] = day;
      newItinerary.itinerary = days;
      // 重新计算总花费
      newItinerary.total_cost = days.reduce((s, d) => s + (d.day_cost || 0), 0);
      return { itinerary: newItinerary };
    });
    const updated = get().itinerary;
    if (_currentTripId && _currentTripId > 0 && updated) {
      updateTrip(_currentTripId, updated).catch(() => {/* 编辑同步失败不阻塞本地操作 */});
    }
  },
}));
