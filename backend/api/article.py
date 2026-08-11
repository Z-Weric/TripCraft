"""AI 攻略文章生成 API — 行程 JSON → 小红书风格 Markdown 文章"""

import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from database.models import get_db, POI
from services.llm_service import has_api_key, chat_completion
from utils.auth import get_current_user
from utils.logger import logger

router = APIRouter()


class GenerateArticleRequest(BaseModel):
    itinerary: dict
    packed_items: List[str] = []
    extra_foods: List[dict] = []


@router.post("/api/article/generate")
async def generate_article(req: GenerateArticleRequest, db: Session = Depends(get_db)):
    """生成小红书风格攻略文章"""
    itinerary = req.itinerary
    packed_items = req.packed_items
    extra_foods = req.extra_foods

    # 如果没有额外美食，从数据库查
    if not extra_foods:
        city = itinerary.get("destination", "")
        food_pois = db.query(POI).filter(POI.city == city, POI.category == "美食").limit(5).all()
        extra_foods = [
            {"name": p.name, "note": p.note or "", "cost": p.cost, "rating": p.rating}
            for p in food_pois
        ]

    # 构建 prompt
    system_prompt = """你是小红书旅行博主，擅长写生动活泼的旅行攻略。
风格要求：
1. 标题吸引眼球，带 emoji
2. 正文轻松活泼，有体验感，穿插实用 tips
3. 用 emoji 标注关键信息
4. Markdown 格式
5. 严格按照给定的文章结构模板输出"""

    # 提取行程中的美食
    trip_foods = []
    for day in itinerary.get("itinerary", []):
        for item in day.get("items", []):
            if item.get("category") == "美食":
                trip_foods.append({"name": item["spot"], "cost": item.get("cost", 0), "note": item.get("note", "")})

    # 计算花费明细
    total_cost = itinerary.get("total_cost", 0)
    ticket_cost = sum(
        item.get("cost", 0)
        for day in itinerary.get("itinerary", [])
        for item in day.get("items", [])
        if item.get("category") != "美食"
    )
    food_cost = sum(
        item.get("cost", 0)
        for day in itinerary.get("itinerary", [])
        for item in day.get("items", [])
        if item.get("category") == "美食"
    )

    user_prompt = f"""请根据以下行程数据生成一篇小红书风格旅行攻略文章。

行程数据：
{json.dumps(itinerary, ensure_ascii=False, indent=2)}

行程中品尝的美食：
{json.dumps(trip_foods, ensure_ascii=False)}

该城市其他推荐美食：
{json.dumps(extra_foods, ensure_ascii=False)}

用户准备的背包物品：
{json.dumps(packed_items, ensure_ascii=False)}

花费明细：门票 ¥{ticket_cost}，餐饮 ¥{food_cost}，总计 ¥{total_cost}

请严格按照以下结构输出（Markdown 格式）：

# {{吸引眼球的标题，带 emoji}}

> 💰 总花费 ¥{total_cost} | 📍 {itinerary.get("destination", "")} | ⏰ {itinerary.get("days", 0)}天

## Day 1 · {{当日主题标题}}

{{景点体验描述，生动活泼，穿插实用 tips，每个景点 2-3 句}}

🍜 **午餐推荐**：{{餐厅名}} — {{推荐理由}}

## Day 2 · {{当日主题标题}}
...

## 🍜 美食推荐

### 行程中品尝的
{{逐个列出行程中的美食，1 句描述}}

### 周边别错过
{{逐个列出额外推荐美食，1 句描述}}

## 📋 实用攻略

### 🎒 行前准备
{{逐个列出用户背包物品}}

### 💰 花费明细
- 门票：¥{ticket_cost}
- 餐饮：¥{food_cost}
- 总计：¥{total_cost}

### ⏰ 注意事项
{{2-3 条实用注意事项}}

注意：每天都要写，不要省略任何一天。只输出文章内容，不要加其他说明。"""

    if not has_api_key():
        # 降级：生成简单模板文章
        return _fallback_article(itinerary, packed_items, extra_foods, trip_foods, ticket_cost, food_cost, total_cost)

    try:
        article = await chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=3000,
        )

        # 检查 LLM 是否返回错误
        if article.startswith("LLM") or article.startswith("API Key"):
            logger.warning(f"LLM 返回错误: {article[:50]}，降级到模板生成")
            return _fallback_article(itinerary, packed_items, extra_foods, trip_foods, ticket_cost, food_cost, total_cost)

        # 文末添加明信片标记
        article = article.strip() + "\n\n<!--POSTCARD-->"

        logger.info(f"攻略文章生成成功: {itinerary.get('destination', '')} {itinerary.get('days', 0)}天")
        return {"status": "ok", "article": article}

    except Exception as e:
        logger.error(f"文章生成失败: {e}")
        return _fallback_article(itinerary, packed_items, extra_foods, trip_foods, ticket_cost, food_cost, total_cost)


def _fallback_article(itinerary, packed_items, extra_foods, trip_foods, ticket_cost, food_cost, total_cost):
    """降级：模板生成文章"""
    destination = itinerary.get("destination", "")
    days = itinerary.get("days", 0)

    lines = [f"# 🗺️ {days}天{destination}深度游 | 超详细攻略\n"]
    lines.append(f"> 💰 总花费 ¥{total_cost} | 📍 {destination} | ⏰ {days}天\n")

    for day in itinerary.get("itinerary", []):
        day_num = day.get("day", 1)
        items = day.get("items", [])
        first_spot = items[0]["spot"] if items else destination
        lines.append(f"## Day {day_num} · {first_spot}一带\n")

        for item in items:
            time = item.get("time", "")
            spot = item.get("spot", "")
            cat = item.get("category", "")
            cost = item.get("cost", 0)
            note = item.get("note", "")
            emoji = "🍜" if cat == "美食" else "📍"
            cost_str = "免费" if cost == 0 else f"¥{cost}"
            lines.append(f"- {emoji} **{time}** {spot}（{cost_str}）{note}\n")

        transport = day.get("transport", "")
        lines.append(f"\n🚗 交通：{transport}\n")

    # 美食推荐
    lines.append("## 🍜 美食推荐\n")
    lines.append("### 行程中品尝的\n")
    for f in trip_foods:
        cost_str = "免费" if f.get("cost", 0) == 0 else f"¥{f['cost']}"
        lines.append(f"- **{f['name']}** — {cost_str}，{f.get('note', '推荐品尝')}\n")

    if extra_foods:
        lines.append("\n### 周边别错过\n")
        for f in extra_foods:
            cost_str = "免费" if f.get("cost", 0) == 0 else f"¥{f.get('cost', 0)}"
            lines.append(f"- **{f['name']}** — {cost_str}，{f.get('note', '值得一试')}\n")

    # 实用攻略
    lines.append("\n## 📋 实用攻略\n")
    if packed_items:
        lines.append("### 🎒 行前准备\n")
        for item in packed_items:
            lines.append(f"- ✅ {item}\n")

    lines.append(f"\n### 💰 花费明细\n")
    lines.append(f"- 门票：¥{ticket_cost}\n")
    lines.append(f"- 餐饮：¥{food_cost}\n")
    lines.append(f"- 总计：¥{total_cost}\n")

    lines.append("\n### ⏰ 注意事项\n")
    lines.append("- 建议提前预约热门景点\n")
    lines.append("- 注意防晒和补水\n")
    lines.append("- 保管好个人物品\n")

    article = "\n".join(lines) + "\n\n<!--POSTCARD-->"
    return {"status": "ok", "article": article}