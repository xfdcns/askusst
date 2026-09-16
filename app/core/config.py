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
    files_dir: str = "data/files"   # get_file 工具可下发给学生的资料文件目录
    redis_url: str = "redis://localhost:6380/0"
    amap_key: str = ""        # 历史天气工具 Key（get_weather 已下线，保留字段不影响旧 .env）

    @property
    def files_path(self) -> Path:
        """可下发资料目录的绝对路径，锚定项目根目录。"""
        p = Path(self.files_dir)
        return p if p.is_absolute() else BASE_DIR / p

    @property
    def raw_path(self) -> Path:
        """无论从哪个工作目录启动，资料目录都锚定到项目根目录下（绝对路径）。"""
        p = Path(self.data_dir)
        return p if p.is_absolute() else BASE_DIR / p


settings = Settings()
