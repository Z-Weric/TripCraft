"""TripCraft 全局配置 — Pydantic Settings 环境管理"""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，从环境变量或 .env 文件加载"""

    # API Keys
    amap_api_key: str = ""
    siliconflow_api_key: str = ""
    llm_model: str = "meituan-longcat/LongCat-2.0"

    # Security
    jwt_secret: str = "change-me-in-production"
    share_token_expire_hours: int = Field(default=168, gt=0, le=8760)

    # Database
    database_url: str = "mysql+pymysql://root:zjy123@localhost:3306/tripcraft?charset=utf8mb4"

    # LLM
    llm_api_base: str = "https://api.siliconflow.cn/v1/chat/completions"
    llm_timeout: int = 60
    llm_default_provider: str = "ollama"
    llm_fallback_provider: str = "openai_compatible"
    llm_enabled_scopes: str = "itinerary,chat"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3.5:9b"
    ollama_timeout: int = Field(default=90, gt=0, le=600)
    ollama_retries: int = Field(default=1, ge=0, le=3)
    ollama_max_concurrency: int = Field(default=2, gt=0, le=16)
    ollama_queue_timeout: int = Field(default=5, gt=0, le=60)
    ollama_circuit_failure_threshold: int = Field(default=3, gt=0, le=20)
    ollama_circuit_cooldown: int = Field(default=30, gt=0, le=600)

    # AMap
    amap_poi_url: str = "https://restapi.amap.com/v3/place/text"
    amap_geo_url: str = "https://restapi.amap.com/v3/geocode/geo"
    amap_timeout: int = 5

    # RAG
    rag_index_path: str = "data/tfidf_index.pkl"
    candidate_pool_multiplier: int = Field(default=8, ge=3, le=20)

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
