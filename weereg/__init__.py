#
#    Copyright (c) 2023 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""Create and run a Flask app to capture station registry data.

See README.md for how to set up and use.
"""
__version__ = "1.2.1"

import os.path
import re
import time
from logging.config import dictConfig

from flask import Flask, request, current_app
import validators.url

from . import db

PARENT_DIR = os.path.join(os.path.dirname(__file__), '..')

dictConfig({
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
})


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_path=PARENT_DIR,
                instance_relative_config=True)
    # Set up useful defaults
    app.config.from_mapping(
        WEEREG_MYSQL_HOST='localhost',
        WEEREG_MYSQL_PORT=3306,
        WEEREG_MYSQL_DATABASE='weereg'
    )

    # Override the defaults
    if test_config:
        # If a test config was passed in, load it
        app.config.from_mapping(test_config)
    else:
        # If not testing, load the instance config
        try:
            app.config.from_pyfile('config.py')
        except FileNotFoundError as e:
            print('Configuration file not found. See README.md')
            raise e

    # Legacy "v1", using GET method:
    @app.get('/api/v1/stations/')
    def add_v1_station():
        """Add a station registration to the database."""
        station_info = request.args.to_dict()
        return _register_station(station_info)

    # V2 version, using POST method
    @app.post('/api/v2/stations/')
    def add_v2_station():
        station_info = request.get_json()
        return _register_station(station_info)

    def _register_station(station_info):
        """Register a station

        Args:
            station_info(dict): Holds the station information. The only required key
                is 'station_url'.
        Returns:
            str|tuple: String 'OK' if successful, otherwise, a
                tuple (error message, response code)
        """

        station_info['last_seen'] = int(time.time() + 0.5)
        station_info['last_addr'] = request.remote_addr

        station_info = sanitize_station(station_info)
        check = check_station(app, station_info)
        if check:
            return check

        app.logger.info(f"Received registration from station {station_info['station_url']}")

        db.insert_into_stations(station_info)

        return "OK"

    @app.get('/api/v2/stations/')
    def get_stations():
        """Get all recent stations. """

        try:
            if 'since' in request.args:
                if 'max_age' in request.args:
                    return "Specify 'max_age' or 'since', but not both", 400
                since = int(request.args['since'])
            else:
                max_age = duration(request.args.get('max_age',
                                                    current_app.config.get(
                                                        "WEEREG_STATIONS_MAX_AGE", "30d")))
                since = time.time() - max_age
            limit = int(request.args.get('limit',
                                         current_app.config.get("WEEREG_STATIONS_LIMIT", 2000)))
        except ValueError:
            return "Badly formed request", 400

        results = [stn for stn in db.gen_stations_since(since, limit)]
        return results

    db.init_app(app)

    return app


def sanitize_station(station_info):
    """Correct any obvious errors in the station information"""

    # Get rid of carriage returns and newlines.
    for key in station_info:
        if isinstance(station_info[key], str):
            station_info[key] = station_info[key].strip().replace("\n", "").replace("\r", "")

    if 'station_model' in station_info:
        # Salvage the driver name out of any "bound method" station models.
        match = re.search(r"bound method (\w+)[. ]", station_info['station_model'])
        if match:
            station_info['station_model'] = match.group(1)

    return station_info


def check_station(app, station_info):
    """Perform some basic data quality checks on a station."""

    # Check station_url. First, we must have one...
    if 'station_url' not in station_info:
        app.logger.info("Missing parameter station_url")
        return "FAIL. Missing parameter station_url", 400
    # ... it must be valid ...
    if not validators.url(station_info['station_url']):
        app.logger.info(f"Invalid station_url {station_info['station_url']}")
        return "FAIL. Invalid station_url", 400
    # ... and not use a silly name.
    for reject in ('weewx.com', 'example.com', 'register.cgi'):
        if reject in station_info['station_url']:
            app.logger.info(f"Silly station_url {station_info['station_url']}")
            return f"FAIL. {station_info['station_url']} is not a valid station_url", 400

    # Cannot post too frequently
    last_post = db.get_last_seen(station_info['station_url'])
    if last_post:
        how_long = station_info['last_seen'] - last_post
        if how_long < current_app.config.get("WEEREG_MIN_DELAY", 3600):
            app.logger.info(f"Station {station_info['station_url']} is "
                            f"logging too frequently ({how_long}s).")
            return "FAIL. Registering too frequently", 429

    # latitude and longitude have to exist, be convertible to floats, and be in a valid range
    try:
        lat = float(station_info['latitude'])
        lon = float(station_info['longitude'])
    except (ValueError, KeyError):
        return "FAIL. Missing or badly formed latitude or longitude", 400
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        return "FAIL. Latitude or longitude out of range", 400


def duration(val):
    if isinstance(val, str):
        if val.endswith('d'):
            return int(val[:-1]) * 3600 * 24
        elif val.endswith('h'):
            return int(val[:-1]) * 3600
        elif val.endswith('M'):
            return int(val[:-1]) * 60
        return int(val)
    return val
