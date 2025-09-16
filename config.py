import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    # Flask
    SECRET_KEY = os.environ.get("SESSION_SECRET", "default-development-key")
    SESSION_COOKIE_NAME = 'academic_writing_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True  # Set to False in development
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    BRAIN_TREE_ENVIRONMENT = os.environ.get("BRAIN_TREE_ENVIRONMENT", "sandbox")
    BRAIN_TREE_MERCHANT_ID= os.environ.get("BRAIN_TREE_MERCHANT_ID")
    BRAIN_TREE_PUBLIC_KEY=os.environ.get("BRAIN_TREE_PUBLIC_KEY")
    BRAIN_TREE_PRIVATE_KEY=os.environ.get("BRAIN_TREE_PRIVATE_KEY")
    # SQLAlchemy
    #SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///academic_writing.db")
    SQLALCHEMY_DATABASE_URI = f"postgresql://{os.environ.get('DB_USER')}:{os.environ.get('DB_PASSWORD')}@{os.environ.get('DB_HOST')}:{os.environ.get('DB_PORT')}/{os.environ.get('DB_NAME')}"
#    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        'pool_size': 10,
        'max_overflow': 20
    }
    
    # Flask-Mail
    MAIL_SERVER =os.environ.get("EMAIL_HOST")
    MAIL_PORT = os.environ.get("EMAIL_PORT")
    MAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "False").lower() in ['true', '1', 'yes']
    MAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False").lower() in ['true', '1', 'yes']
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")
    
    # File uploads
    UPLOAD_FOLDER = 'uploads'
    DELIVERY_UPLOAD_FOLDER = 'uploads/delivery/'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    
    # Stripe
    STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
    ALLOWED_PIC_EXT ={'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Rate Limiter
    LIMITER_STORAGE_URI = os.environ.get("LIMITER_STORAGE_URI", "redis://localhost:6379/0")

    # CACHE
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "simple")
    CACHE_DEFAULT_TIMEOUT = 300 

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
