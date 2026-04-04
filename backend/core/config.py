import os

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./harness.db")

# Encryption key for API keys stored in settings
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "dev-encryption-key-32bytes!!!!!")
