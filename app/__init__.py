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
        print('origin=', request.origin)
        print('remote_addr=', request.remote_addr)
        station_info = request.args.to_dict()
        station_info['last_seen'] = str(int(time.time() + 0.5))
        station_info['last_addr'] = request.remote_addr
        to_update = STATION_INFO.intersection(station_info)
        pairs = [(k, f'"{station_info[k]}"') for k in to_update]
        obs, values = zip(*pairs)
        sql_stmt = f'INSERT INTO stations ({", ".join(obs)}) VALUES ({", ".join(values)});'
        print(sql_stmt)
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
