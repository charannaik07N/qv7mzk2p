import os
from pathlib import Path

DATA_DIR = Path(os.getenv('DATA_DIR', str(Path(__file__).resolve().parents[2] / 'data')))
API_BASE = 'https://data.elexon.co.uk/bmrs/api/v1'
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:8080').split(',')
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '')
DEFAULT_CUTOFF = os.getenv('DEFAULT_CUTOFF', '09:20')
HISTORY_WARNING = ('WINDFOR dataset publication queries are intended to retain superseded forecasts. '
                   'Historical completeness is not guaranteed; metrics use only retained publications. '
                   'Official OpenAPI publication queries were reviewed; January observation coverage has not been independently verified.')

ENABLE_LOCAL_REFRESH = os.getenv('ENABLE_LOCAL_REFRESH', '0') == '1'
AUTO_REFRESH_ON_STARTUP = os.getenv('AUTO_REFRESH_ON_STARTUP', '0') == '1'
