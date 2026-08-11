"""TripCraft 全局配置 — Pydantic Settings 环境管理"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，从环境变量或 .env 文件加载"""

    # API Keys
    amap_api_key: str = ""
    siliconflow_api_key: str = ""
    llm_model: str = "meituan-longcat/LongCat-2.0"

    # Database
    database_url: str = "mysql+pymysql://root:zjy123@localhost:3306/tripcraft?charset=utf8mb4"

    # LLM
    llm_api_base: str = "https://api.siliconflow.cn/v1/chat/completions"
    llm_timeout: int = 60

    # AMap
    amap_poi_url: str = "https://restapi.amap.com/v3/place/text"
    amap_geo_url: str = "https://restapi.amap.com/v3/geocode/geo"
    amap_timeout: int = 5

    # RAG
    rag_index_path: str = "data/tfidf_index.pkl"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # MongoDB
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "tripcraft"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()