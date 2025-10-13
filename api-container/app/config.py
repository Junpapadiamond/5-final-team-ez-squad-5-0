import os


class Config:
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/together")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    AGENT_LLM_ENABLED = os.environ.get("AGENT_LLM_ENABLED", "1")
    AGENT_MODEL_TONE = os.environ.get("AGENT_MODEL_TONE", os.environ.get("OPENAI_AGENT_MODEL", "gpt-4o-mini"))
    AGENT_MODEL_COACHING = os.environ.get("AGENT_MODEL_COACHING", "gpt-4o-mini")
    AGENT_MODEL_STYLE = os.environ.get("AGENT_MODEL_STYLE", "gpt-4o-mini")
    AGENT_TONE_CACHE_HOURS = os.environ.get("AGENT_TONE_CACHE_HOURS", "3")
    AGENT_COACHING_CACHE_HOURS = os.environ.get("AGENT_COACHING_CACHE_HOURS", "6")
    INTERNAL_SERVICE_TOKEN = os.environ.get("INTERNAL_SERVICE_TOKEN", "dev-internal-token")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
