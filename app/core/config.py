"""全局配置：从项目根目录的 .env 读取，避免工作目录不同导致的相对路径坑。"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# app/core/config.py -> 项目根目录是上三级
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    dashscope_api_key: str

    embedding_model: str = "text-embedding-v3"
    chat_model: str = "qwen-plus"
    embedding_dim: int = 1024
    chunk_size: int = 500
    chunk_overlap: int = 50

    data_dir: str = "data/raw"
    redis_url: str = "redis://localhost:6380/0"
    amap_key: str = ""        # 高德开放平台 Web 服务 Key（第4周天气工具）

    @property
    def raw_path(self) -> Path:
        """无论从哪个工作目录启动，资料目录都锚定到项目根目录下（绝对路径）。"""
        p = Path(self.data_dir)
        return p if p.is_absolute() else BASE_DIR / p


settings = Settings()
