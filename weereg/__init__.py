#
#    Copyright (c) 2023 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""Create and run a Flask app to capture station registry data.

See README.md for how to set up and use.
"""

import os.path
import time

from flask import Flask, request, current_app

from . import db

parent_dir = os.path.join(os.path.dirname(__file__), '..')


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_path=parent_dir,
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

    # Legacy "v1" GET statement:
    @app.get('/api/v1/stations')
    def add_station():
        """Add a station registration to the database."""
        station_info = request.args.to_dict()
        station_info['last_seen'] = int(time.time() + 0.5)
        station_info['last_addr'] = request.remote_addr

        # We must have a station_url
        if 'station_url' not in station_info:
            return "Missing parameter station_url", 400

        # Cannot post too frequently
        last_post = db.get_last_seen(station_info['station_url'])
        if last_post and station_info['last_seen'] - last_post < current_app.config.get("WEEREG_MIN_DELAY", 3600):
            return "Registering too frequently", 429

        db.insert_into_stations(station_info)

        return "OK"

    @app.get('/api/v2/stations')
    def get_stations():
        """Get all recent stations. """

        try:
            if 'since' in request.args:
                if 'max_age' in request.args:
                    return "Specify 'max_age' or 'since', but not both", 400
                since = int(request.args['since'])
            else:
                max_age = duration(request.args.get('max_age',
                                                    current_app.config.get("WEEREG_STATIONS_MAX_AGE", "30d")))
                since = time.time() - max_age
            limit = int(request.args.get('limit', current_app.config.get("WEEREG_STATIONS_LIMIT", 2000)))
        except ValueError:
            return "Badly formed request", 400

        results = [stn for stn in db.gen_stations_since(since, limit)]
        return results

    db.init_app(app)

    return app


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
