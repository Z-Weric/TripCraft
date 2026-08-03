"""Packing 清单服务 — 规则引擎生成行李清单

根据目的地、天数、季节、偏好生成结构化打包清单。
"""

from typing import List, Dict, Any
from datetime import datetime
from utils.logger import logger


def _get_season() -> str:
    """根据当前月份判断季节"""
    month = datetime.now().month
    if month in (3, 4, 5):
        return "spring"
    elif month in (6, 7, 8):
        return "summer"
    elif month in (9, 10, 11):
        return "autumn"
    else:
        return "winter"


# 基础清单（所有行程都需要的）
BASE_ITEMS = {
    "证件": ["身份证", "手机", "充电宝", "充电线"],
    "日用品": ["纸巾", "湿巾", "水杯", "雨伞"],
    "衣物": ["换洗衣物", "睡衣", "袜子"],
    "医药": ["创可贴", "感冒药", "肠胃药"],
}

# 季节补充
SEASON_ITEMS = {
    "spring": {"衣物": ["薄外套", "长裤"], "防护": ["防晒霜 SPF30", "口罩"]},
    "summer": {"衣物": ["短袖 x3", "短裤", "凉鞋"], "防护": ["防晒霜 SPF50", "墨镜", "遮阳帽", "驱蚊液"]},
    "autumn": {"衣物": ["厚外套", "长裤", "围巾"], "防护": ["防晒霜 SPF30", "润唇膏"]},
    "winter": {"衣物": ["羽绒服", "毛衣", "保暖内衣", "手套", "围巾"], "防护": ["润唇膏", "护手霜"]},
}

# 偏好补充
PREFERENCE_ITEMS = {
    "自然风光": {"装备": ["登山鞋", "双肩包", "望远镜"]},
    "美食": {"工具": ["肠胃药(加强)", "口香糖"]},
    "历史文化": {"装备": ["相机", "笔记本"]},
    "购物": {"装备": ["折叠购物袋", "大行李箱"]},
    "亲子": {"儿童": ["儿童水壶", "零食", "湿巾(加强)", "小玩具"]},
}

# 城市特色补充
CITY_ITEMS = {
    "杭州": {"特产": ["茶叶包装袋(买龙井用)"]},
    "成都": {"特产": ["辣度测试贴(火锅用)"]},
    "西安": {"装备": ["舒适步行鞋(兵马俑走很多路)"]},
    "厦门": {"装备": ["泳衣", "拖鞋", "防水手机袋"]},
    "青岛": {"装备": ["泳衣", "沙滩巾", "防晒霜(加强)"]},
    "大理": {"装备": ["墨镜(高原紫外线强)", "润唇膏(加强)"]},
    "重庆": {"装备": ["舒适步行鞋(山城爬坡多)"]},
    "长沙": {"特产": ["零食收纳袋(小吃多)"]},
}


def generate_packing_list(destination: str, days: int, preferences: List[str] = None) -> Dict[str, Any]:
    """生成打包清单"""
    season = _get_season()
    preferences = preferences or []

    # 合并所有分类
    categories: Dict[str, List[str]] = {}

    # 基础
    for cat, items in BASE_ITEMS.items():
        categories[cat] = list(items)

    # 天数补充衣物数量
    categories["衣物"].append(f"内衣 x{days}")
    categories["衣物"].append(f"袜子 x{days}")

    # 季节
    for cat, items in SEASON_ITEMS.get(season, {}).items():
        if cat not in categories:
            categories[cat] = []
        categories[cat].extend(items)

    # 偏好
    for pref in preferences:
        for cat, items in PREFERENCE_ITEMS.get(pref, {}).items():
            if cat not in categories:
                categories[cat] = []
            categories[cat].extend(items)

    # 城市特色
    for cat, items in CITY_ITEMS.get(destination, {}).items():
        if cat not in categories:
            categories[cat] = []
        categories[cat].extend(items)

    # 去重
    for cat in categories:
        categories[cat] = list(dict.fromkeys(categories[cat]))  # 保序去重

    season_name = {"spring": "春季", "summer": "夏季", "autumn": "秋季", "winter": "冬季"}[season]

    result = {
        "destination": destination,
        "days": days,
        "season": season_name,
        "categories": categories,
        "total_items": sum(len(v) for v in categories.values()),
    }

    logger.info(f"Packing 清单生成: {destination} {days}天 {result['total_items']}件物品")
    return result