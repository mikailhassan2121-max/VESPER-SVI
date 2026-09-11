from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_prefix="VESPER_")
    massive_api_key: SecretStr = Field(default=SecretStr(""), validation_alias="MASSIVE_API_KEY")
    telegram_bot_token: SecretStr = Field(default=SecretStr(""), validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", validation_alias="TELEGRAM_CHAT_ID")
    data_dir: Path = Path("data")
    model_dir: Path = Path("models")
    min_price: float = Field(default=2, gt=0)
    min_dollar_volume: float = Field(default=10_000_000, gt=0)
    max_spread_bps: float = Field(default=75, gt=0)
    max_quote_age: float = Field(default=3, gt=0)
    max_bar_age: float = Field(default=90, gt=0)
    min_coverage: float = Field(default=.98, gt=0, le=1)
    min_score: float = Field(default=75, ge=65, le=100)
    min_net_return: float = Field(default=.005, gt=0)
    max_downside: float = Field(default=.08, gt=0)
    signal_grace_seconds: int = Field(default=30, ge=1, le=120)
    slippage_bps_each_side: float = Field(default=10, ge=0)
    queue_size: int = Field(default=20000, ge=100)
    raw_retention_days: int = Field(default=90, ge=7)
    forward_pause_drawdown: float = Field(default=.15, gt=0, lt=1)

    def prepare(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)
