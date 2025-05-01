import os
from dotenv import load_dotenv
import secrets
from datetime import timedelta

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(16))
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/evoting')
    
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flask_session')
    SESSION_KEY_PREFIX = 'flask_session:'

    REMEMBER_COOKIE_DURATION = timedelta(minutes=60)
    REMEMBER_COOKIE_SECURE = False  
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'



