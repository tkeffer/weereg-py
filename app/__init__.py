import collections
import os
import time

from flask import Flask, request

from . import db

# Columns of the SQL table 'stations'
STATION_INFO = frozenset([
    "station_url",
    "description",
    "latitude",
    "longitude",
    "station_type",
    "station_model",
    "weewx_info",
    "python_info",
    "platform_info",
    "last_addr",
    "last_seen",
])


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        HOST='localhost',
        PORT=3306,
        USER='weewx',
        PASSWORD='weewx',
        DATABASE='weereg',
        STATION_TABLE='stations',
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Legacy "v1" GET statement:
    @app.get('/v1')
    def add_station():
        station_info = request.args.to_dict()
        station_info['last_seen'] = str(int(time.time() + 0.5))
        station_info['last_addr'] = request.remote_addr

        # The set of values to be inserted.
        # This is the set of types in station_info that are also in the schema
        to_insert = STATION_INFO.intersection(station_info)

        # Get a list of sql type names and a list of their values.
        # Make sure the values are in quotation marks, because they might contain spaces.
        pairs = [(k, f'"{station_info[k]}"') for k in to_insert]
        columns, values = zip(*pairs)
        sql_stmt = f'INSERT INTO stations ({", ".join(columns)}) VALUES ({", ".join(values)});'

        db_conn = db.get_db()
        with db_conn.cursor() as cursor:
            cursor.execute(sql_stmt)

        return "OK"

    db.init_app(app)

    return app


def to_float(value):
    try:
        value = float(value)
    except (ValueError, TypeError):
        value = None
    return value
