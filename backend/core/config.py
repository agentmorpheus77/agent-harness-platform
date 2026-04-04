import os

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
# Use absolute path to avoid CWD ambiguity
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_raw_db_url = os.getenv("DATABASE_URL", f"sqlite:///{_BASE_DIR}/harness.db")

# Railway provides postgres:// but SQLAlchemy requires postgresql://
if _raw_db_url.startswith("postgres://"):
    _raw_db_url = _raw_db_url.replace("postgres://", "postgresql://", 1)

DATABASE_URL = _raw_db_url

# Encryption key for API keys stored in settings
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "dev-encryption-key-32bytes!!!!!")
