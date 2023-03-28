"""Configuration file for weereg-py

    DO NOT EDIT THIS FILE!

Instead, copy it, then edit the copy.
     cp config-sample.py config.py
     nano config.py
"""

# Replace with your MySQL credentials
WEEREG_MYSQL_USER = 'weewx'
WEEREG_MYSQL_PASSWORD = 'weewx'

# How often a station can post.
# It should be slightly less than client's post_interval.
WEEREG_MIN_DELAY = 3600 * 23

# Configuration for method GET /api/v2/stations
WEEREG_STATIONS_MAX_AGE = 3600 * 24 * 30  # = One month
WEEREG_STATIONS_LIMIT = 2000

WEEREG_LOGGING = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }
    },
    'handlers': {
        'rotate': {
            'level': 'DEBUG',
            'formatter': 'default',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/tmp/weereg.log',
            'maxBytes': 1000000,
            'backupCount': 4,
        }
    },
    'root': {
        'level': 'DEBUG',
        'handlers': [
            'rotate'
        ]
    }
}
