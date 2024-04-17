#
#    Copyright (c) 2023-2024 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""Create and run a Flask app to capture station registry data.

See README.md for how to set up and use.
"""
__version__ = "1.7.2"

import logging.config
import os.path
import re
import subprocess
import threading
import time
from dataclasses import dataclass

import validators.url
from flask import Flask, request, current_app

from . import db


@dataclass
class RejectStation(Exception):
    reason: str
    code: int


PARENT_DIR = os.path.join(os.path.dirname(__file__), '..')


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

    logging.config.dictConfig(app.config.get('WEEREG_LOGGING'))

    # Legacy "v1", using GET method:
    @app.get('/api/v1/stations', strict_slashes=False)
    def add_v1_station():
        """Add a station registration to the database."""
        station_info = request.args.to_dict()
        return _register_station(station_info)

    # V2 version, using POST method
    @app.post('/api/v2/stations', strict_slashes=False)
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
        try:
            last_seen = check_station(app, station_info)
        except RejectStation as eject:
            return eject.reason, eject.code

        db.insert_into_stations(station_info)

        app.logger.info(f"Received registration from station {station_info['station_url']}; "
                        f"version {station_info.get('weewx_info', 'N/A')}; "
                        f"({station_info['last_addr']})")

        # If the staton has never been seen before, do a screen capture.
        if not last_seen:
            _capture_station(station_info['station_url'],
                             app.config.get('SCREEN_CAPTURE_TIMEOUT'))

        return "OK"

    def _capture_station(station_url, timeout=None):
        """Kick off the screenshot capture process in a separate thread.

        Args:
            station_url (str): The unique identifier to be used by a station.
            timeout (float|None): The number of seconds to wait for the capture subprocess before
                killing it. Default is 180 seconds
        """

        # Timeout defaults to 180 seconds
        timeout = timeout or 180

        def _do_capture():
            """Do the actual capture. Intended to be run in a thread."""

            # Get a logger that we can use in this thread:
            log = logging.getLogger(__name__)
            # Be prepared to catch an exception in case the capture-one shell doesn't exist, or
            # the process times out.
            try:
                # Run the capture shell command. If it times out, a TimeoutError will be raised.
                subprocess.run(["/var/www/html/register/capture-one.sh", station_url],
                               timeout=timeout)
                # We're inside a thread, so we cannot use the Flask app logger.
                # Use the standard logging module.
                log.info(f"Kicked off screen capture for station {station_url}")
            except FileNotFoundError:
                log.error("Could not find screen capture app")
            except TimeoutError:
                log.error(f"Screen capture for station {station_url} "
                          f"timed out after {timeout} seconds")

        thread = threading.Thread(target=_do_capture)
        # Start the thread, but don't wait around to 'join' it. We don't care if it succeeds
        # or fails.
        thread.start()

    @app.get('/api/v2/stations', strict_slashes=False)
    def get_stations():
        """Get all recent stations. """

        try:
            if 'since' in request.args:
                if 'max_age' in request.args:
                    return "Specify 'max_age' or 'since', but not both", 400
                since = int(request.args['since'])
            else:
                since = duration(request.args.get('max_age',
                                                  current_app.config.get(
                                                      "WEEREG_STATIONS_MAX_AGE", "30d")))
            limit = int(request.args.get('limit',
                                         current_app.config.get("WEEREG_STATIONS_LIMIT", 2000)))
        except ValueError:
            return "Badly formed request", 400

        results = [stn for stn in db.gen_stations_since(since, limit)]
        return results

    @app.get('/api/v2/stats/<info_type>')
    def get_stats(info_type: str):
        """Get usage statistics"""
        if info_type not in {"station_type", "station_model", "weewx_info", "python_info",
                             "platform_info", "config_path", "entry_path"}:
            return "Invalid info type", 400
        try:
            if 'since' in request.args and 'max_age' in request.args:
                return "Specify 'max_age' or 'since', but not both", 400
            elif 'since' in request.args:
                since = int(request.args['since'])
            elif 'max_age' in request.args:
                since = duration(request.args.get('max_age'))
            else:
                since = None
        except ValueError:
            return "Badly formed request", 400

        results = db.get_stats(info_type, start_time=since)

        # If requested, consolidate the results.
        if 'consolidate' in request.args:
            results = consolidate(info_type, results)

        return results

    db.init_app(app)

    return app


def sanitize_station(station_info):
    """Correct any obvious errors in the station information"""

    # Get rid of carriage returns, newlines, and double-quotes. Single quotes are OK,
    # because they might be part of a name (e.g., Land's End).
    for key in station_info:
        if isinstance(station_info[key], str):
            station_info[key] = station_info[key] \
                .strip() \
                .replace("\n", "") \
                .replace("\r", "") \
                .replace('"', "")

    if 'station_model' in station_info:
        # Salvage the driver name out of any "bound method" station models.
        match = re.search(r"bound method (\w+)[. ]", station_info['station_model'])
        if match:
            station_info['station_model'] = match.group(1)

    if 'config_path' in station_info:
        station_info['config_path'] = os.path.normpath(station_info['config_path'])
    if 'entry_path' in station_info:
        station_info['entry_path'] = os.path.normpath(station_info['entry_path'])

    return station_info


def check_station(app, station_info):
    """Perform some basic quality checks on a station.

    Args:
        app (Flask): A flask application object
        station_info (dict): Station information from the client

    Returns:
        float|None: The last time the station was seen, or None if it has never been seen.

    Raises:
        RejectStation: If the station fails any validations.
    """

    # Check station_url. First, we must have one...
    if 'station_url' not in station_info:
        app.logger.info("Missing parameter station_url")
        raise RejectStation("FAIL. Missing parameter station_url", 200)
    # ... it must be valid ...
    if not validators.url(station_info['station_url']):
        app.logger.info(f"Invalid station_url {station_info['station_url']}")
        raise RejectStation("FAIL. Invalid station_url", 200)
    # ... and not use a silly name.
    for reject in ('weewx.com', 'example.com', 'register.cgi'):
        if reject in station_info['station_url']:
            app.logger.info(f"Silly station_url {station_info['station_url']}")
            raise RejectStation(f"FAIL. {station_info['station_url']} is not a "
                                f"serious station_url", 200)

    # latitude and longitude have to exist, be convertible to floats, and be in a valid range
    try:
        lat = float(station_info['latitude'])
        lon = float(station_info['longitude'])
    except (ValueError, KeyError):
        raise RejectStation("FAIL. Missing or badly formed latitude or longitude", 200)
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise RejectStation("FAIL. Latitude or longitude out of range", 200)

    # Cannot post too frequently
    last_post = db.get_last_seen(station_info['station_url'])
    if last_post:
        how_long = station_info['last_seen'] - last_post
        if how_long < current_app.config.get("WEEREG_MIN_DELAY", 23 * 3600):
            if 'weewx_info' in station_info:
                version = f"v{station_info['weewx_info']}"
            else:
                version = "N/A"
            app.logger.info(f"Station {station_info['station_url']} ({version}) is "
                            f"registering too frequently ({how_long}s)")
            raise RejectStation("FAIL. Registering too frequently", 429)

    return last_post


config_path_re = re.compile(r"""
                    /(home|Users)/  # Accept either /home or /Users
                    [-\w]+?/        # Match a user directory name. May contain a dash
                    weewx-data/.*   # Match anything following "weewx-data"
                    """, re.X)
entry_path_re = re.compile(r"""
                   /(home|Users)/       # Accept either /home or /Users
                   [-\w]+?/             # Match a user directory name. May contain a dash
                   [-\w]*?venv[-\w]*/   # Match anything containing "venv"
                   """, re.X, )


def consolidate(info_type, result_set):
    if info_type == 'config_path':
        return consolidate_info(config_path_re, result_set, '/home/*/weewx-data/weewx.conf')
    elif info_type == 'entry_path':
        return consolidate_info(entry_path_re, result_set, '/home/*/weewx-venv/bin/weewxd')
    return result_set


def consolidate_info(matcher, result_set, new_key):
    """Merge the count of all the keys that match 'matcher' under one key in the result set."""
    to_be_merged_dict = dict()
    count_dict = dict()
    for key in list(result_set.keys()):
        if matcher.match(key):
            # Initalize the count for all timestamps in this key
            for timestamp in result_set[key][0]:
                count_dict[timestamp] = 0
            # Save the matching keys. They will be merged together in the next step
            to_be_merged_dict[key] = result_set.pop(key)
    # If any matches were found...
    if to_be_merged_dict:
        # To through the matched keys, adding their count to the new count.
        for key in to_be_merged_dict:
            for timestamp, count in zip(to_be_merged_dict[key][0], to_be_merged_dict[key][1]):
                count_dict[timestamp] += count
        # Consolidate the results under the new key
        result_set[new_key] = [[t for t in count_dict], [count_dict[t] for t in count_dict]]
    return result_set


def duration(val, ref_time=None):
    ref_time = int(ref_time or time.time() + 0.5)
    if isinstance(val, str):
        if val.endswith('y'):
            delta = int(val[:-1]) * 3600 * 24 * 365
        elif val.endswith('d'):
            delta = int(val[:-1]) * 3600 * 24
        elif val.endswith('h'):
            delta = int(val[:-1]) * 3600
        elif val.endswith('M'):
            delta = int(val[:-1]) * 60
        else:
            delta = int(val)
    else:
        delta = val
    return ref_time - delta
