import vibeSdk from "@alipay/weavefox-vibe-web";
import { create } from 'zustand';

// TODO: 【Zustand 与接口对接实现】
//       以下 Zustand store 负责对接后端的 Hono router（functions/itineraryRouter.js）。
//       如果您在后期需要扩展状态，例如：
//       1. 增加本地缓存（LocalStorage）或离线保存功能；
//       2. 支持多用户切换、多日程对比状态；
//       3. 在 generate 之后加入更加丰富的前端统计分析（CostChart）和景点坐标（MapView）渲染状态；
//       您可以直接在此处添加对应的 state 和 action，并与前端组件进行优雅的状态绑定（注意取多字段时使用 useShallow 守卫）。
const useItineraryStore = create((set, get) => ({
  historyList: [],
  currentPlan: null,
  loading: false,
  error: null,
  lastRequest: null,

  // 获取用户的历史规划记录
  getHistoryList: async () => {
    set({ loading: true, error: null });
    try {
      const response = await vibeSdk.functions.get('itinerary/list');
      if (response && response.success) {
        set({ historyList: response.data || [], loading: false });
      } else {
        set({ error: response?.error || '获取历史规划失败', loading: false });
      }
    } catch (err) {
      set({ error: err.message || '获取历史规划失败', loading: false });
    }
  },

  // 获取方案详情
  getPlanDetail: async (id) => {
    set({ loading: true, error: null });
    try {
      const response = await vibeSdk.functions.get(`itinerary/detail/${id}`);
      if (response && response.success) {
        set({ currentPlan: response.data, loading: false });
        return response.data;
      } else {
        set({ error: response?.error || '方案不存在', loading: false });
      }
    } catch (err) {
      set({ error: err.message || '获取详情失败', loading: false });
    }
    return null;
  },

  // 删除攻略
  deletePlan: async (id) => {
    set({ loading: true });
    try {
      const response = await vibeSdk.functions.delete(`itinerary/delete/${id}`);
      if (response && response.success) {
        // 更新本地列表
        const updated = get().historyList.filter(p => p.id !== id);
        set({ historyList: updated, loading: false });
        return true;
      } else {
        set({ error: response?.error || '删除失败', loading: false });
      }
    } catch (err) {
      set({ error: err.message || '删除失败', loading: false });
    }
    return false;
  },

  // 核心：在线生成攻略
  generateItinerary: async (req) => {
    set({ loading: true, error: null, currentPlan: null, lastRequest: req });
    try {
      const response = await vibeSdk.functions.post('itinerary/generate', req);
      if (response && response.success) {
        if (response.itinerary && response.itinerary.error) {
          set({ error: response.itinerary.error, loading: false });
        } else {
          set({ currentPlan: { ...response.itinerary, verification: response.verification }, loading: false });
        }
      } else {
        set({ error: response?.error || '行程规划生成失败', loading: false });
      }
    } catch (err) {
      set({ error: err.message || '生成失败，网络请求异常', loading: false });
    }
  },

  // 保存当前攻略
  savePlan: async () => {
    const { currentPlan, lastRequest } = get();
    if (!currentPlan || !lastRequest) {
      set({ error: '当前无攻略可保存' });
      return null;
    }

    set({ loading: true });
    try {
      const payload = {
        destination: lastRequest.destination,
        days: lastRequest.days,
        budget: lastRequest.budget,
        preferences: lastRequest.preferences,
        itinerary: currentPlan.itinerary,
        totalCost: currentPlan.total_cost || currentPlan.totalCost,
        summary: currentPlan.summary,
        verification: currentPlan.verification,
      };

      const response = await vibeSdk.functions.post('itinerary/save', payload);
      set({ loading: false });
      if (response && response.success) {
        return response.data.id;
      } else {
        set({ error: response?.error || '保存失败' });
      }
    } catch (err) {
      set({ error: err.message || '保存失败', loading: false });
    }
    return null;
  },

  // 提交意见反馈
  submitFeedback: async (feedbackType, comment = '') => {
    const { lastRequest } = get();
    if (!lastRequest) return false;

    try {
      const payload = {
        destination: lastRequest.destination,
        days: lastRequest.days,
        budget: lastRequest.budget,
        preferences: lastRequest.preferences,
        feedback_type: feedbackType,
        comment,
      };
      const response = await vibeSdk.functions.post('itinerary/feedback', payload);
      return response && response.success;
    } catch (err) {
      console.error('Feedback submit error:', err);
      return false;
    }
  },

  // 清空当前详情状态
  clearCurrentPlan: () => {
    set({ currentPlan: null, error: null });
  }
}));

export default useItineraryStore;