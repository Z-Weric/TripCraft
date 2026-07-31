"""RAG 服务 — 基于 TF-IDF 的景点知识检索（纯本地，零网络依赖）

两个场景：
1. 行程生成：根据"目的地+偏好"检索 top-K 景点，注入模型 prompt
2. 桌宠客服：根据用户问题检索景点知识，生成专业回答

说明：当前使用 scikit-learn 的 TF-IDF 做文本相似度检索。
后续接入 vLLM 后，可升级为 LangChain + ChromaDB 向量检索，
但在本地无网络环境下 TF-IDF 是最可靠的方案。
"""

from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import jieba

# 中文分词预处理
def _tokenize(text: str) -> str:
    """用 jieba 分词，返回空格分隔的词序列"""
    words = jieba.cut(text)
    return " ".join(words)

# 内存中的景点知识库
_pois_db: List[Dict[str, Any]] = []
_tfidf_matrix = None
_vectorizer = None


def build_index_from_pois(pois: List[Dict[str, Any]]):
    """构建 TF-IDF 索引。每个景点一个文档。"""
    global _pois_db, _tfidf_matrix, _vectorizer
    _pois_db = pois

    # 为每个景点构造文本（分词后）
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
    print(f"已构建 TF-IDF 索引：{len(docs)} 个景点")
    return True


def is_index_ready() -> bool:
    return _tfidf_matrix is not None and len(_pois_db) > 0


def search_pois_by_rag(
    destination: str,
    preferences: List[str] = None,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """TF-IDF 检索：根据目的地和偏好检索最相关的景点。

    用于行程生成场景——替换原来的随机选取。
    """
    if not is_index_ready():
        return []

    # 构造查询（分词后）
    query = f"{destination} 旅游景点"
    if preferences:
        query += " " + " ".join(preferences)

    # TF-IDF 相似度计算
    query_vec = _vectorizer.transform([_tokenize(query)])
    scores = cosine_similarity(query_vec, _tfidf_matrix).flatten()

    # 按城市过滤 + 按分数排序
    results = []
    for i, poi in enumerate(_pois_db):
        if poi.get("city") == destination:
            score = float(scores[i])

            # 偏好匹配加分
            if preferences:
                pref_map = {
                    "自然风光": ["自然风光"],
                    "美食": ["美食"],
                    "历史文化": ["历史文化"],
                    "亲子": ["自然风光", "历史文化"],
                    "购物": ["购物"],
                }
                matched_cats = set()
                for pref in preferences:
                    matched_cats.update(pref_map.get(pref, []))
                if poi.get("category") in matched_cats:
                    score += 0.3

            results.append({**poi, "_score": score})

    results.sort(key=lambda x: x["_score"], reverse=True)
    return results[:top_k]


def chat_with_rag(question: str, destination: str = None) -> str:
    """
    RAG 问答：根据用户问题检索景点知识，生成专业旅游客服回答。

    用于桌宠客服场景——Crafty 信鸽基于景点知识库回答旅行问题。
    流程：TF-IDF 检索景点 → 拼接上下文 → LLM 生成自然语言回答
    """
    if not is_index_ready():
        return "咕咕~ 知识库尚未初始化，请先生成一次行程以构建景点索引。"

    # TF-IDF 相似度计算
    query_vec = _vectorizer.transform([_tokenize(question)])
    scores = cosine_similarity(query_vec, _tfidf_matrix).flatten()

    # 取 top-5 相似景点
    top_indices = np.argsort(scores)[::-1][:5]
    top_pois = [_pois_db[i] for i in top_indices if scores[i] > 0]

    # 按城市过滤（如果有指定）
    if destination:
        city_pois = [p for p in top_pois if p.get("city") == destination]
        if city_pois:
            top_pois = city_pois

    # 构造 RAG 上下文（即使为空也继续走 LLM）
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

    # 尝试用 LLM 生成自然语言回答
    from services.llm_service import has_api_key, chat_with_context
    if has_api_key():
        system_prompt = (
            "你是 TripCraft 的旅行信差 Crafty，一只飞越过大江南北的信鸽。"
            '你性格活泼，说话以"咕咕~"开头，对各地景点、美食、交通了如指掌。'
            "请根据用户的问题和下方景点知识库信息，给出专业、简洁、有用的旅行建议。"
            "回答控制在 200 字以内，语气亲切但信息密度高。"
            "如果知识库信息为空，你可以根据自己的旅行经验回答。"
        )
        try:
            reply = chat_with_context(
                system_prompt=system_prompt,
                user_message=question,
                context=context,
                temperature=0.7,
                max_tokens=400,
            )
            return reply
        except Exception:
            pass  # LLM 失败时降级到模板回答

    # 降级：模板回答（LLM 不可用时）
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