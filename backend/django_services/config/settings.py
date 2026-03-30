import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
from cryptography.fernet import Fernet

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')  
DEBUG = os.getenv('DEBUG') == 'True'
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if host.strip()]

INSTALLED_APPS = [
    'django.contrib.admin', 
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages', 

    # DRF and authentication
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'dj_rest_auth',
    'oauth2_provider',  
    'social_django', 

    # Security and CORS
    'corsheaders',

    # Custom users app
    'users',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS/Hosts seguros por defecto (abiertos solo en desarrollo)
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False

    cors_origins_raw = os.getenv('CORS_ALLOWED_ORIGINS', '')
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins_raw.split(',') if origin.strip()]

# Permitir credenciales (cookies, encabezados de autorización, etc.)
CORS_ALLOW_CREDENTIALS = True

# Explícitamente permitir métodos HTTP 
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT',]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']

CORS_PREFLIGHT_MAX_AGE = 86400

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://172.17.0.1:3000",
]

if not DEBUG:
    csrf_extra_raw = os.getenv('CSRF_TRUSTED_ORIGINS', '')
    extra_origins = [origin.strip() for origin in csrf_extra_raw.split(',') if origin.strip()]
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS + extra_origins))

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('POSTGRES_HOST'),
        'PORT': os.getenv('POSTGRES_PORT'),
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/min',
        'user': '100/min',
        'login': '5/min',
        'password_reset': '5/min',
    },
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'SIGNING_KEY': os.getenv('JWT_SECRET_KEY', SECRET_KEY),
    'ALGORITHM': os.getenv('JWT_ALGORITHM'),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',  # Flask busca este claim en el token
}

OAUTH2_PROVIDER = {
    "ACCESS_TOKEN_EXPIRE_SECONDS": 3600,
    "REFRESH_TOKEN_EXPIRE_SECONDS": 86400,
    "SCOPES": {
        "read": "Leer datos",
        "write": "Modificar datos",
    },
}

# Configuración específica para Google OAuth
AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('GOOGLE_CLIENT_ID')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['email', 'profile']
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {
    'access_type': 'offline',
    'prompt': 'select_account'
}

REST_USE_JWT = True
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = "optional"

AUTH_USER_MODEL = 'users.User'
SESSION_COOKIE_AGE = 3600  # 1 hora de sesión
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False
USE_TZ = True

STATIC_URL = '/static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CACHE_REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
CACHE_REDIS_USE_TLS = os.getenv('REDIS_USE_TLS', 'False').strip().lower() in {'1', 'true', 'yes', 'on'}
CACHE_REDIS_SCHEME = 'rediss' if CACHE_REDIS_USE_TLS else 'redis'
CACHE_REDIS_AUTH = f":{CACHE_REDIS_PASSWORD}@" if CACHE_REDIS_PASSWORD else ""
CACHE_REDIS_DB = os.getenv('REDIS_DB_CACHE', os.getenv('REDIS_DB_SESSIONS', os.getenv('REDIS_DB', '0')))

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f"{CACHE_REDIS_SCHEME}://{CACHE_REDIS_AUTH}{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/{CACHE_REDIS_DB}",
        'OPTIONS': {
            'ssl_cert_reqs': os.getenv('REDIS_SSL_CERT_REQS', 'required'),
        } if CACHE_REDIS_USE_TLS else {},
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = os.getenv('EMAIL_PORT')
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')  # tu dirección de correo electrónico
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')  # tu contraseña de correo electrónico

FLASK_API_KEY = os.getenv('FLASK_API_KEY', os.getenv('DJANGO_SECRET_KEY', ''))
AI_SERVICE_URL = os.getenv('AI_SERVICE_URL', '').rstrip('/')
FIELD_ENCRYPTION_KEY = os.getenv('FIELD_ENCRYPTION_KEY', '')
AUDIT_SIGNING_KEY = os.getenv('AUDIT_SIGNING_KEY', '')

if not FLASK_API_KEY:
    raise ImproperlyConfigured("FLASK_API_KEY must be configured.")
if not CACHE_REDIS_PASSWORD:
    raise ImproperlyConfigured("REDIS_PASSWORD must be configured.")
if not FIELD_ENCRYPTION_KEY:
    raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY must be configured.")
if not AUDIT_SIGNING_KEY:
    raise ImproperlyConfigured("AUDIT_SIGNING_KEY must be configured.")
try:
    Fernet(FIELD_ENCRYPTION_KEY.encode("utf-8"))
except Exception as exc:
    raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY must be a valid Fernet key.") from exc

if not DEBUG:
    ALLOWED_HOSTS = [host for host in ALLOWED_HOSTS if host != '*']

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True") == "True"
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
