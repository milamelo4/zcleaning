import os
from dotenv import load_dotenv
from datetime import timedelta

# Load .env from the parent directory
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'defaultsecretkey')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Add session timeout
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # CSRF protection
    WTF_CSRF_SECRET_KEY = os.getenv('WTF_CSRF_SECRET_KEY', 'defaultcsrfkey')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

