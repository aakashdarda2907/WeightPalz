"""
Django settings for WeightPalz.
"""
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
# Keep the key Django generated for you in the original file.
SECRET_KEY = '&r1swbewf5ynh#6y@6zxsnd=h++hb5@1j-vwsk5hz5mv8i0lj='
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'local-dev-only-not-a-real-secret')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'

# Set to False when you deploy on PythonAnywhere (stage three).
DEBUG = True

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'weightpalz.pythonanywhere.com',
]

CSRF_TRUSTED_ORIGINS = ['https://weightpalz.pythonanywhere.com']
# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Our single app
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'weightpalz.urls'

# ---------------------------------------------------------------------------
# Templates (project-level templates folder)
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'weightpalz.wsgi.application'

# ---------------------------------------------------------------------------
# Database (SQLite is fine for this project, including PythonAnywhere)
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 6}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Authentication redirects
# ---------------------------------------------------------------------------
LOGIN_URL = 'login'            # where @login_required sends logged-out users
LOGIN_REDIRECT_URL = 'home'    # after login
LOGOUT_REDIRECT_URL = 'landing'

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']   # our styles.css lives here
STATIC_ROOT = BASE_DIR / 'staticfiles'     # used by collectstatic on PythonAnywhere

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'