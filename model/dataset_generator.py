"""训练数据生成脚本

从 SQLite 景点数据库读取真实 POI 数据，
调用硅基流动 LongCat-2.0 生成结构化行程 JSON 作为 SFT 训练数据。

覆盖：10 城市 × 3 种天数 × 3 种预算 × 多种偏好 = 1000+ 条

用法:
    cd TripCraft
    source .venv/bin/activate
    python model/dataset_generator.py

输出: data/train/tripcraft_train.jsonl
"""

import os
import sys
import json
import time
import random
import httpx
from typing import List, Dict, Any

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from database.models import SessionLocal, POI

# ===== 配置 =====

# 加载 API Key
API_KEY = ""
LLM_MODEL = "meituan-longcat/LongCat-2.0"
_env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("SILICONFLOW_API_KEY="):
                API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("LLM_MODEL="):
                LLM_MODEL = line.split("=", 1)[1].strip().strip('"').strip("'")

API_BASE = "https://api.siliconflow.cn/v1/chat/completions"

# 生成参数
CITIES = ["杭州", "成都", "西安", "厦门", "苏州", "南京", "重庆", "长沙", "青岛", "大理"]
DAYS_OPTIONS = [2, 3, 5]
BUDGET_OPTIONS = [1000, 2000, 5000]
PREFERENCES_POOL = [
    ["美食"],
    ["自然风光"],
    ["历史文化"],
    ["美食", "自然风光"],
    ["美食", "历史文化"],
    ["自然风光", "历史文化"],
    ["美食", "自然风光", "亲子"],
    ["美食", "自然风光", "历史文化"],
    ["购物", "美食"],
    ["自然风光", "亲子"],
]

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "train", "tripcraft_train.jsonl")
OUTPUT_PATH = os.path.abspath(OUTPUT_PATH)

# 每个城市生成多少条（10 城市 × 100 = 1000 条）
PER_CITY = 100


def get_city_pois(city: str, db) -> List[Dict[str, Any]]:
    """从数据库查询城市景点"""
    pois = db.query(POI).filter(POI.city == city).all()
    return [
        {
            "name": p.name, "category": p.category, "lat": p.lat, "lng": p.lng,
            "cost": p.cost, "duration": p.duration, "note": p.note, "address": p.address,
        }
        for p in pois
    ]


def construct_prompt(destination: str, days: int, budget: int, preferences: List[str],
                     pois: List[Dict[str, Any]]) -> str:
    """构造 LLM prompt，包含真实 POI 供模型参考"""
    # 随机选 15 个景点作为参考
    sample_pois = random.sample(pois, min(15, len(pois)))
    poi_list = "\n".join([
        f"- {p['name']}（{p['category']}，门票{p['cost']}元，{p['duration']}，{p.get('note','')}）"
        for p in sample_pois
    ])

    pref_str = "、".join(preferences)
    return f"""你是旅游攻略生成专家。请根据以下信息生成一份结构化的旅行行程 JSON。

要求：
1. 只输出 JSON，不要输出其他任何内容
2. 严格按照下面的 JSON 格式
3. 每天安排 3 个景点（早、中、下午各一个）
4. 总花费不能超过预算 {budget} 元
5. 景点从以下真实景点中选取，可以适当添加备注

目的地：{destination}
天数：{days}
预算：{budget} 元
偏好：{pref_str}

可参考的真实景点：
{poi_list}

输出格式：
{{
  "destination": "{destination}",
  "days": {days},
  "itinerary": [
    {{
      "day": 1,
      "items": [
        {{
          "time": "09:00-12:00",
          "spot": "景点名",
          "category": "分类",
          "duration": "3h",
          "cost": 0,
          "lat": 30.0,
          "lng": 120.0,
          "note": "备注"
        }}
      ],
      "transport": "交通方式",
      "day_cost": 100
    }}
  ],
  "total_cost": 500,
  "summary": "行程总结"
}}"""


def call_llm(prompt: str) -> str:
    """调用硅基流动 LLM"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 2000,
    }

    try:
        resp = httpx.post(API_BASE, json=payload, headers=headers, timeout=60)
        data = resp.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"].strip()
        return ""
    except Exception as e:
        print(f"  [LLM 错误] {e}")
        return ""


def extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except:
        pass

    # 尝试提取 ```json ... ``` 中的内容
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        try:
            return json.loads(text[start:end].strip())
        except:
            pass

    # 尝试提取第一个 { 到最后一个 }
    if "{" in text and "}" in text:
        start = text.index("{")
        end = text.rindex("}") + 1
        try:
            return json.loads(text[start:end])
        except:
            pass

    return None


def validate_itinerary(data: dict, destination: str, days: int, budget: int) -> bool:
    """验证生成的行程 JSON 是否合规"""
    if not data:
        return False

    if data.get("destination") != destination:
        return False
    if data.get("days") != days:
        return False

    itinerary = data.get("itinerary", [])
    if not isinstance(itinerary, list) or len(itinerary) != days:
        return False

    for day in itinerary:
        items = day.get("items", [])
        if not isinstance(items, list) or len(items) < 2:
            return False
        for item in items:
            if not item.get("spot") or not item.get("time"):
                return False
            if "lat" not in item or "lng" not in item:
                return False

    if "total_cost" not in data:
        return False

    return True


def generate_dataset():
    """生成完整的训练数据集"""
    if not API_KEY:
        print("错误: 未找到 SILICONFLOW_API_KEY")
        return

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    db = SessionLocal()
    total = 0
    valid = 0
    invalid = 0

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for city in CITIES:
            pois = get_city_pois(city, db)
            if not pois:
                print(f"[跳过] {city}: 无景点数据")
                continue

            print(f"\n=== 生成 {city} ({len(pois)} 个景点可用) ===")

            for i in range(PER_CITY):
                # 随机参数组合
                days = random.choice(DAYS_OPTIONS)
                budget = random.choice(BUDGET_OPTIONS)
                preferences = random.choice(PREFERENCES_POOL)

                prompt = construct_prompt(city, days, budget, preferences, pois)
                response = call_llm(prompt)

                total += 1

                if not response:
                    invalid += 1
                    continue

                # 提取并验证 JSON
                itinerary_json = extract_json(response)
                if not itinerary_json or not validate_itinerary(itinerary_json, city, days, budget):
                    invalid += 1
                    if total % 10 == 0:
                        print(f"  进度: {total}/{PER_CITY * len(CITIES)} (有效 {valid}, 无效 {invalid})")
                    continue

                # 写入 JSONL
                prompt_text = f"生成行程：目的地={city}, 天数={days}, 预算={budget}, 偏好={'、'.join(preferences)}"
                record = {
                    "prompt": prompt_text,
                    "response": json.dumps(itinerary_json, ensure_ascii=False),
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                valid += 1

                # 进度打印
                if (i + 1) % 10 == 0:
                    print(f"  {city}: {i+1}/{PER_CITY} (有效 {valid}, 无效 {invalid})")

                # 避免触发 API 限流
                time.sleep(0.3)

    db.close()

    print(f"\n========== 完成 ==========")
    print(f"总生成: {total}")
    print(f"有效: {valid}")
    print(f"无效: {invalid}")
    print(f"合法率: {valid/total*100:.1f}%" if total > 0 else "N/A")
    print(f"输出文件: {OUTPUT_PATH}")

    return valid


def verify_dataset():
    """验证生成的训练数据"""
    if not os.path.exists(OUTPUT_PATH):
        print("文件不存在")
        return

    count = 0
    valid = 0
    cities = set()

    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            count += 1
            try:
                record = json.loads(line)
                prompt = record.get("prompt", "")
                response = record.get("response", "")

                # 检查 response 是否是合法 JSON
                data = json.loads(response)
                if "destination" in data and "itinerary" in data:
                    valid += 1
                    cities.add(data["destination"])
            except:
                pass

    print(f"\n========== 数据验证 ==========")
    print(f"总条数: {count}")
    print(f"合法 JSON: {valid}")
    print(f"合法率: {valid/count*100:.1f}%" if count > 0 else "N/A")
    print(f"覆盖城市: {', '.join(sorted(cities))}")

    # 打印一条示例
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        first_line = f.readline()
        record = json.loads(first_line)
        print(f"\n示例 prompt: {record['prompt'][:80]}...")
        data = json.loads(record['response'])
        print(f"示例 destination: {data.get('destination')}")
        print(f"示例 days: {data.get('days')}")
        print(f"示例 total_cost: {data.get('total_cost')}")


if __name__ == "__main__":
    print(f"LLM 模型: {LLM_MODEL}")
    print(f"API Key: {API_KEY[:8]}...")
    print(f"目标: 10 城市 × {PER_CITY} 条 = {PER_CITY * len(CITIES)} 条")
    print(f"输出: {OUTPUT_PATH}")
    print()

    # 生成
    generate_dataset()

    # 验证
    verify_dataset()