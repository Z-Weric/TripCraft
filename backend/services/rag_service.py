"""RAG 服务 — 基于 TF-IDF 的景点知识检索 (v2 持久化版)

优化点：
1. TF-IDF 索引持久化到 pickle，启动时加载
2. 增量更新支持
"""

import os
import pickle
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import jieba
from config import settings
from utils.logger import logger

INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "..", settings.rag_index_path)
INDEX_PATH = os.path.abspath(INDEX_PATH)

# 中文分词预处理
def _tokenize(text: str) -> str:
    words = jieba.cut(text)
    return " ".join(words)

# 内存中的景点知识库
_pois_db: List[Dict[str, Any]] = []
_tfidf_matrix = None
_vectorizer = None


def build_index_from_pois(pois: List[Dict[str, Any]], force_rebuild: bool = False):
    """构建 TF-IDF 索引。优先从磁盘加载，否则构建并持久化。"""
    global _pois_db, _tfidf_matrix, _vectorizer

    # 尝试从磁盘加载
    if not force_rebuild and os.path.exists(INDEX_PATH):
        try:
            with open(INDEX_PATH, "rb") as f:
                saved = pickle.load(f)
            # 校验 POI 数量是否一致
            if len(saved.get("pois", [])) == len(pois):
                _pois_db = saved["pois"]
                _tfidf_matrix = saved["tfidf_matrix"]
                _vectorizer = saved["vectorizer"]
                logger.info(f"从磁盘加载 TF-IDF 索引：{len(_pois_db)} 个景点")
                return True
            else:
                logger.info("POI 数量变化，重建索引")
        except Exception as e:
            logger.warning(f"加载索引失败，将重建: {e}")

    # 构建新索引
    _pois_db = pois
    docs = []
    for poi in pois:
        text = (
            f"{poi.get('city', '')} {poi.get('name', '')} "
            f"{poi.get('category', '')} {poi.get('note', '')} "
            f"{poi.get('address', '')}"
        )
        docs.append(_tokenize(text))

    _vectorizer = TfidfVectorizer(max_features=5000)
    _tfidf_matrix = _vectorizer.fit_transform(docs)
    logger.info(f"已构建 TF-IDF 索引：{len(docs)} 个景点")

    # 持久化到磁盘
    try:
        os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
        with open(INDEX_PATH, "wb") as f:
            pickle.dump({
                "pois": _pois_db,
                "tfidf_matrix": _tfidf_matrix,
                "vectorizer": _vectorizer,
            }, f)
        logger.info(f"索引已持久化到 {INDEX_PATH}")
    except Exception as e:
        logger.warning(f"索引持久化失败: {e}")

    return True


def is_index_ready() -> bool:
    return _tfidf_matrix is not None and len(_pois_db) > 0


def search_pois_by_rag(
    destination: str,
    preferences: List[str] = None,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """TF-IDF 检索：根据目的地和偏好检索最相关的景点。"""
    if not is_index_ready():
        return []

    query = f"{destination} 旅游景点"
    if preferences:
        query += " " + " ".join(preferences)

    query_vec = _vectorizer.transform([_tokenize(query)])
    scores = cosine_similarity(query_vec, _tfidf_matrix).flatten()

    results = []
    for i, poi in enumerate(_pois_db):
        if poi.get("city") == destination:
            score = float(scores[i])

            if preferences:
                pref_map = {
                    "自然风光": ["自然风光"],
                    "美食": ["美食"],
                    "历史文化": ["历史文化"],
                    "亲子": ["自然风光", "历史文化"],
                    "购物": ["购物"],
                }
                # preferences 已按权重降序排列，索引越小权重越高
                # 权重加分：第1个偏好 +0.5，第2个 +0.35，第3个 +0.2，之后 +0.1
                for pref_idx, pref in enumerate(preferences):
                    matched_cats = pref_map.get(pref, [])
                    if poi.get("category") in matched_cats:
                        bonus = max(0.5 - pref_idx * 0.15, 0.1)
                        score += bonus

            results.append({**poi, "_score": score})

    results.sort(key=lambda x: x["_score"], reverse=True)
    return results[:top_k]


def chat_with_rag(question: str, destination: str = None) -> str:
    """RAG 问答（v1 保留兼容，新代码应走 api/chat.py 流式接口）。"""
    if not is_index_ready():
        return "咕咕~ 知识库尚未初始化，请先生成一次行程以构建景点索引。"

    query_vec = _vectorizer.transform([_tokenize(question)])
    scores = cosine_similarity(query_vec, _tfidf_matrix).flatten()

    top_indices = np.argsort(scores)[::-1][:5]
    top_pois = [_pois_db[i] for i in top_indices if scores[i] > 0]

    if destination:
        city_pois = [p for p in top_pois if p.get("city") == destination]
        if city_pois:
            top_pois = city_pois

    context = ""
    if top_pois:
        context_parts = []
        for poi in top_pois[:5]:
            cost_str = "免费" if poi.get("cost", 0) == 0 else f"门票{poi['cost']}元"
            context_parts.append(
                f"- {poi.get('name', '')}（{poi.get('city', '')}，{poi.get('category', '')}）："
                f"{cost_str}，建议游玩{poi.get('duration', '')}。{poi.get('note', '')}"
            )
        context = "\n".join(context_parts)

    # 降级：模板回答
    answer_parts = ["咕咕~ 作为你的专属旅行信差 Crafty，我帮你查到了以下信息：\n"]
    for poi in top_pois[:3]:
        cost_str = "免费" if poi.get("cost", 0) == 0 else f"门票{poi['cost']}元"
        city = poi.get("city", "")
        answer_parts.append(
            f"📍 {poi.get('name', '未知景点')}（{city} · {poi.get('category', '')}）\n"
            f"   {cost_str} | 建议游玩{poi.get('duration', '2h')}\n"
            f"   {poi.get('note', '暂无备注信息')}\n"
        )
    answer_parts.append("\n如果你想了解更详细的行程安排，可以在上方搜索栏生成一份专属攻略明信片哦~ 📬")
    return "\n".join(answer_parts)