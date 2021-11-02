"""
To start server on production.
"""
import os
import sys
import waitress
from core.wsgi import APPLICATION


BASE_DIR = os.path.join(os.path.dirname(__file__), 'src')
sys.path.append(BASE_DIR)

waitress.serve(
    APPLICATION,
    host='0.0.0.0',
    port=os.getenv('PORT', '8000'),
    threads=8
)
