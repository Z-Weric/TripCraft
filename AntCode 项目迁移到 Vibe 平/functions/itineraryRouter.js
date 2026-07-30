import { Hono } from 'hono';
import { randomUUID } from 'node:crypto';

const router = new Hono();

// 计算两点间哈弗辛距离（km）
function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371; // 地球半径
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// 1. 获取当前用户的所有历史旅行计划列表
// TODO: 【数据库实现】此处从 MySQL 数据表 t_travel_plans 查询数据。当前为基本 Knex 查询，可根据实际需求扩展高级关联或物理索引优化。
router.get('/list', async (c) => {
  try {
    const db = c.env.db;
    const user = c.env.user;
    
    if (!user || !user.workNo) {
      return c.json({ success: false, error: '未获取到用户信息' }, 401);
    }
    
    const records = await db('t_travel_plans')
      .where('f_user_id', user.workNo)
      .orderBy('f_create_time', 'desc');
      
    const data = records.map(r => ({
      id: r.f_id,
      userId: r.f_user_id,
      destination: r.f_destination,
      days: r.f_days,
      budget: r.f_budget,
      preferences: JSON.parse(r.f_preferences || '[]'),
      totalCost: r.f_total_cost,
      summary: r.f_summary,
      createTime: r.f_create_time,
    }));
    
    return c.json({ success: true, data });
  } catch (error) {
    return c.json({ success: false, error: error.message }, 500);
  }
});

// 2. 获取单个方案详情
// TODO: 【数据库实现】根据主键 ID 查询历史攻略。此处若有分表、分库或缓存需求，可在此对接 Redis/缓存服务。
router.get('/detail/:id', async (c) => {
  try {
    const db = c.env.db;
    const id = c.req.param('id');
    
    const record = await db('t_travel_plans')
      .where('f_id', id)
      .first();
      
    if (!record) {
      return c.json({ success: false, error: '旅行规划不存在或已被删除' }, 404);
    }
    
    const data = {
      id: record.f_id,
      userId: record.f_user_id,
      destination: record.f_destination,
      days: record.f_days,
      budget: record.f_budget,
      preferences: JSON.parse(record.f_preferences || '[]'),
      itinerary: JSON.parse(record.f_itinerary || '[]'),
      totalCost: record.f_total_cost,
      summary: record.f_summary,
      verification: JSON.parse(record.f_verification || '{}'),
      createTime: record.f_create_time,
    };
    
    return c.json({ success: true, data });
  } catch (error) {
    return c.json({ success: false, error: error.message }, 500);
  }
});

// 3. 删除旅行方案
// TODO: 【数据库实现】物理删除或逻辑删除当前用户的攻略记录。若要改成逻辑删除（soft delete），请在此修改为 Update 语句。
router.delete('/delete/:id', async (c) => {
  try {
    const db = c.env.db;
    const id = c.req.param('id');
    const user = c.env.user;
    
    if (!user || !user.workNo) {
      return c.json({ success: false, error: '未授权操作' }, 401);
    }
    
    const count = await db('t_travel_plans')
      .where({ f_id: id, f_user_id: user.workNo })
      .delete();
      
    if (count === 0) {
      return c.json({ success: false, error: '方案不存在或无权删除' }, 403);
    }
    
    return c.json({ success: true, message: '删除成功' });
  } catch (error) {
    return c.json({ success: false, error: error.message }, 500);
  }
});

// 4. 保存旅行方案
// TODO: 【数据库实现】将生成的旅行方案写入 t_travel_plans 表。如需支持方案多版本、分享态记录或关联订单，请在此扩展写入逻辑。
router.post('/save', async (c) => {
  try {
    const db = c.env.db;
    const user = c.env.user;
    const body = await c.req.json();
    
    if (!user || !user.workNo) {
      return c.json({ success: false, error: '未授权操作' }, 401);
    }
    
    const { destination, days, budget, preferences, itinerary, totalCost, summary, verification } = body;
    const id = randomUUID();
    
    await db('t_travel_plans').insert({
      f_id: id,
      f_user_id: user.workNo,
      f_destination: destination,
      f_days: parseInt(days, 10),
      f_budget: parseInt(budget, 10),
      f_preferences: JSON.stringify(preferences || []),
      f_itinerary: JSON.stringify(itinerary || []),
      f_total_cost: parseInt(totalCost, 10),
      f_summary: summary || '',
      f_verification: JSON.stringify(verification || {}),
    });
    
    return c.json({ success: true, data: { id } });
  } catch (error) {
    return c.json({ success: false, error: error.message }, 500);
  }
});

// 5. 提交用户意见反馈
// TODO: 【数据库实现】落库反馈数据。后续若需要自动触发钉钉告警或工单创建，可在这里接入消息通知或工作流服务。
router.post('/feedback', async (c) => {
  try {
    const db = c.env.db;
    const user = c.env.user;
    const body = await c.req.json();
    
    const { destination, days, budget, preferences, feedback_type, comment } = body;
    
    await db('t_feedbacks').insert({
      f_destination: destination,
      f_days: parseInt(days, 10),
      f_budget: parseInt(budget, 10),
      f_preferences: (preferences || []).join(','),
      f_feedback_type: feedback_type,
      f_comment: comment || '',
      f_user_id: user?.workNo || 'anonymous',
    });
    
    return c.json({ success: true, message: '反馈提交成功' });
  } catch (error) {
    return c.json({ success: false, error: error.message }, 500);
  }
});

// 6. 核心行程生成及校验算法
// TODO: 【AI API 实现】当前为基于本地 POI 数据库的规则拼接与推荐校验算法。
//       如果要接入大语言模型（LLM）进行智能攻略生成：
//       1. 可在此处引入 LLM 完成对用户偏好的语义理解。
//       2. 通过 prompt 设计让 AI 按指定 JSON 格式输出多天行程。
//       3. 结合本地的数据库（t_pois）对 AI 生成的景点坐标和预算进行验证，确保真实验证逻辑不失效。
router.post('/generate', async (c) => {
  try {
    const db = c.env.db;
    const body = await c.req.json();
    const { destination, days, budget, preferences = [] } = body;
    
    if (!destination) {
      return c.json({ success: false, error: '目的地不能为空' }, 400);
    }
    
    // 从本地景点库查询匹配的 POI 列表
    const pois = await db('t_pois')
      .where('f_city', 'like', `%${destination}%`);
      
    if (!pois || pois.length === 0) {
      return c.json({
        success: true,
        itinerary: { error: `暂不支持目的地：${destination}` },
        verification: {}
      });
    }
    
    // 过滤 POI
    let filtered = [];
    if (preferences.length === 0) {
      filtered = [...pois];
    } else {
      // 偏好映射：自然风光→自然，美食→美食，历史文化→历史文化，亲子→自然风光+历史文化，购物→购物
      const prefMap = {
        '自然风光': ['自然风光'],
        '美食': ['美食'],
        '历史文化': ['历史文化'],
        '亲子': ['自然风光', '历史文化'],
        '购物': ['购物'],
      };
      
      const matchedCats = new Set();
      preferences.forEach(pref => {
        const cats = prefMap[pref] || [];
        cats.forEach(c => matchedCats.add(c));
      });
      
      filtered = pois.filter(p => matchedCats.has(p.f_category));
    }
    
    // 如果过滤后景点太少，补充其他景点
    const needCount = days * 3;
    if (filtered.length < needCount) {
      const remaining = pois.filter(p => !filtered.some(f => f.f_id === p.f_id));
      filtered = filtered.concat(remaining);
    }
    
    // 乱序打乱
    filtered.sort(() => 0.5 - Math.random());
    const selected = filtered.slice(0, needCount);
    
    // 构建 Itinerary
    const itinerary = [];
    let totalCost = 0;
    const timeSlots = [
      { time: '09:00-12:00', defaultDur: '3h' },
      { time: '12:00-13:30', defaultDur: '1.5h' },
      { time: '14:00-16:00', defaultDur: '2h' },
    ];
    
    const transports = [
      '步行 + 公交，约15元',
      '地铁 + 步行，约10元',
      '自驾 / 大巴，约80元',
      '打车，约40元'
    ];
    
    for (let dayIdx = 0; dayIdx < days; dayIdx++) {
      const items = [];
      let dayCost = 0;
      const dayPois = selected.slice(dayIdx * 3, (dayIdx + 1) * 3);
      
      dayPois.forEach((poi, i) => {
        const slot = timeSlots[i % 3];
        const cost = poi.f_cost || 0;
        items.push({
          time: slot.time,
          spot: poi.f_name,
          category: poi.f_category || '自然风光',
          duration: poi.f_duration || slot.defaultDur,
          cost: cost,
          lat: poi.f_lat,
          lng: poi.f_lng,
          note: poi.f_note || '',
        });
        dayCost += cost;
      });
      
      const transportCost = dayIdx === 0 ? 15 : [10, 15, 40, 80][Math.floor(Math.random() * 4)];
      dayCost += transportCost;
      totalCost += dayCost;
      
      itinerary.push({
        day: dayIdx + 1,
        items,
        transport: transports[dayIdx % transports.length],
        day_cost: dayCost,
      });
    }
    
    const prefStr = preferences.length > 0 ? preferences.join('、') : '综合';
    const summary = `${days}天${destination}${prefStr}之旅`;
    
    const resultItinerary = {
      destination,
      days,
      itinerary,
      total_cost: totalCost,
      summary,
    };
    
    // 路线真实性及距离验证
    // 这里我们对景点进行核对
    const allItems = [];
    itinerary.forEach(day => allItems.push(...day.items));
    
    let spotsVerified = 0;
    allItems.forEach(item => {
      const match = pois.find(p => p.f_name === item.spot);
      if (match && Math.abs(match.f_lat - item.lat) < 0.02 && Math.abs(match.f_lng - item.lng) < 0.02) {
        spotsVerified++;
      }
    });
    
    // 路线距离检查 (相邻距离 <= 50km)
    let routeValid = true;
    for (let dayIdx = 0; dayIdx < itinerary.length; dayIdx++) {
      const items = itinerary[dayIdx].items;
      for (let i = 0; i < items.length - 1; i++) {
        const dist = haversine(items[i].lat, items[i].lng, items[i+1].lat, items[i+1].lng);
        if (dist > 50) {
          routeValid = false;
          break;
        }
      }
      if (!routeValid) break;
    }
    
    const verification = {
      spots_valid: spotsVerified === allItems.length,
      spots_total: allItems.length,
      spots_verified: spotsVerified,
      budget_valid: totalCost <= budget,
      budget_total: totalCost,
      budget_limit: budget,
      budget_utilization: budget > 0 ? Math.round((totalCost / budget) * 100) : 0,
      route_valid: routeValid,
    };
    
    return c.json({
      success: true,
      itinerary: resultItinerary,
      verification,
    });
  } catch (error) {
    return c.json({ success: false, error: error.message }, 500);
  }
});

export default router;