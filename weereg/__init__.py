#
#    Copyright (c) 2023 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""Create and run a Flask app to capture station registry data

To use:

1. Create a directory in your home directory called 'weereg':
       mkdir ~/weereg

2. Put a file called "config.py" in it. This is a file in Python
   that will contain configuration information.
   Sample contents:
       USER = 'username'
       PASSWORD = 'your_password'
       MIN_DELAY = 3600  # Users cannot post more often than this.
"""

import os
import os.path
import time

from flask import Flask, request, current_app

from . import db


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__,
                instance_path=os.path.expanduser("~/weereg"),
                instance_relative_config=True)
    app.config.from_mapping(
        HOST='localhost',
        PORT=3306,
        DATABASE='weereg',
        STATION_TABLE='stations',
    )

    if test_config:
        # load the test config if passed in
        app.config.from_mapping(test_config)
    else:
        # If not testing, load the instance config
        try:
            app.config.from_pyfile('config.py')
        except FileNotFoundError as e:
            print(e)
            print(f"See the top of file {__file__} for directions.")
            raise

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
        if last_post and station_info['last_seen'] - last_post < current_app.config.get("MIN_DELAY", 3600):
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
                max_age = duration(request.args.get('max_age', current_app.config.get("STATIONS_MAX_AGE", "30d")))
                since = time.time() - max_age
            limit = int(request.args.get('limit', current_app.config.get("STATIONS_LIMIT", 2000)))
        except ValueError:
            return "Badly formed request", 400

        results = [stn for stn in db.gen_stations_since(since, limit)]
        return results

    db.init_app(app)

    return app


def duration(val):
    if val.endswith('d'):
        return int(val[:-1]) * 3600 * 24
    elif val.endswith('h'):
        return int(val[:-1]) * 3600
    elif val.endswith('M'):
        return int(val[:-1]) * 60
    return int(val)