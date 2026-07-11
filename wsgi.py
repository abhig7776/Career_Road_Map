"""
Production entrypoint. Run with:
    gunicorn --bind 0.0.0.0:8000 --workers 3 wsgi:app
"""
from app import app

if __name__ == '__main__':
    app.run()
