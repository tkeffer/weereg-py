import datetime
import sys

import click
import pymysql
from flask import current_app, g

from . import db

# The set of data columns in the schema. They can be in any order.
# TODO: read them dynamically from the databaase.
STATION_COLUMNS = [
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
    "config_path",
    "entry_path"
]
# Columns of the SQL table 'stations'
STATION_INFO = frozenset(STATION_COLUMNS)


def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(host=current_app.config['WEEREG_MYSQL_HOST'],
                               port=current_app.config['WEEREG_MYSQL_PORT'],
                               user=current_app.config['WEEREG_MYSQL_USER'],
                               passwd=current_app.config['WEEREG_MYSQL_PASSWORD'],
                               db=current_app.config['WEEREG_MYSQL_DATABASE'],
                               autocommit=True)
    return g.db


def close_db(e=None):
    db_conn = g.pop('db', None)

    if db_conn:
        db_conn.close()


def init_db():
    """Initialize the MySQL database."""
    print("This will drop the 'stations' table, then reinitialize it.")
    print("OLD DATA WILL BE DESTROYED!!")
    while True:
        ans = input("Are you sure you want to do this (y/n)? ")
        if ans.strip() == 'y':
            break
        elif ans.strip() == 'n':
            sys.exit("Nothing done")

    db_conn = get_db()

    # Read in the schema
    with current_app.open_resource('stations_schema.sql') as fd:
        contents = fd.read().decode('utf8')

    # The schema can consist of several SQL statements. Split on the semicolon.
    # Get rid of any resultant empty statements. Add the semicolon back in.
    queries = ["%s;" % q.strip() for q in contents.split(';') if q.strip()]

    # Now execute them one by one
    with db_conn.cursor() as cursor:
        for query in queries:
            cursor.execute(query)


@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


def insert_into_stations(station_info):
    """Insert the station information into the database.
    Args:
        station_info(dict): Keys are columns in the database.
    """

    # This is the set of types in station_info that are also in the schema
    to_insert = STATION_INFO.intersection(station_info)

    # Get a list of sql type names and a list of their values.
    # Make sure the values are in quotation marks, because they might contain spaces.
    pairs = [(k, f'"{station_info[k]}"') for k in to_insert]
    columns, values = zip(*pairs)
    sql_stmt = f'INSERT INTO weereg.stations ({", ".join(columns)}) VALUES ({", ".join(values)});'

    db_conn = db.get_db()
    with db_conn.cursor() as cursor:
        cursor.execute(sql_stmt)

    return True


def get_last_seen(station_url):
    """Return the last time a station reported in.

    Args:
        station_url(str): The unique URL for the station.

    Returns:
        int|None: Time it was last seen in unix epoch time, or None if it has never been seen.
    """
    db_conn = db.get_db()
    with db_conn.cursor() as cursor:
        cursor.execute('SELECT last_seen FROM weereg.stations WHERE station_url=%s '
                       'ORDER BY last_seen DESC LIMIT 1',
                       station_url)
        result = cursor.fetchone()
        last_seen = result[0] if result else None
        return last_seen


# Prepare for the inner join:
t_list = ["t.%s" % col for col in STATION_COLUMNS]
# Form it:
STATIONS_SINCE_SQL = f"""SELECT {", ".join(t_list)}
FROM weereg.stations t
INNER JOIN (
    SELECT station_url, MAX(last_seen) as MaxSeen
    FROM weereg.stations
    WHERE last_seen > %s
    GROUP BY station_url
    LIMIT %s
) tm ON t.station_url = tm.station_url AND t.last_seen = tm.MaxSeen
ORDER BY last_seen ASC
"""


def gen_stations_since(since=0, limit=None):
    """Generate a sequence of dictionaries.
    Each dictionary is the station information as of when a station was last seen.
    Args:
        since (float|int): Generate station information since this time.
        limit (int|None): Max number of stations to return. Default is 2000

    Yields:
        dict: Station information
    """
    limit = limit or 2000

    db_conn = db.get_db()
    with db_conn.cursor() as cursor:
        cursor.execute(STATIONS_SINCE_SQL, (since, limit))
        for result in cursor.fetchall():
            d = dict(zip(STATION_COLUMNS, result))
            yield d


def get_stats(info_type, start_time=None, batch_size=7):
    """Get statistics for a particular type of information
    Args:
        info_type (str): Generall, something like 'python_info', or 'weewx_info'
        start_time (float|None): Earliest time to use. Default is use all time.
        batch_size (int): Chunk size to search for stations. Default is 7.

    Returns:
        dict: Key is the information value (e.g., "3.8.1"). Value is a list
            of two lists. The first list is the timestamps, the second the count of the number
            of stations with the information value at that
            time [ [time1, time2, ...], [count1, count2, ...] ]

    """
    db_conn = db.get_db()
    with db_conn.cursor() as cursor:
        # Get the last date in the dataset
        cursor.execute("SELECT MAX(last_seen) FROM weereg.stations")
        max_timestamp = cursor.fetchone()[0]
        last_date = datetime.date.fromtimestamp(max_timestamp)
        interp_dict = {
            'info_type': info_type,
            'stop_date': last_date,
            'batch_size': batch_size,
            'start_clause': f"WHERE last_seen >= {start_time}" if start_time else "",
        }

        sql = """
        SELECT batch,
               TRUNCATE(UNIX_TIMESTAMP(DATE_ADD('%(stop_date)s', INTERVAL - %(batch_size)s * batch + 1 DAY)), 0),
               %(info_type)s,
               COUNT(*)
        FROM weereg.stations t
        INNER JOIN (
            SELECT station_url,
                   TRUNCATE((DATEDIFF('%(stop_date)s',
                                      FROM_UNIXTIME(last_seen)))/ %(batch_size)s, 0) as batch,
                   MAX(last_seen) as MaxSeen
            FROM weereg.stations
            %(start_clause)s
            GROUP BY batch, station_url
        ) last_stns
        ON t.station_url = last_stns.station_url
        AND t.last_seen = last_stns.MaxSeen
        GROUP BY last_stns.batch, %(info_type)s
        ORDER BY %(info_type)s, last_stns.batch DESC;
        """ % interp_dict

        cursor.execute(sql)
        results = dict()
        for row in cursor.fetchall():
            # Deconstruct the row
            batch, stop, value, count = row
            # Some info_types can be None, which the JSON sorting algorithm doesn't like.
            # Replace with a N/A string
            if value is None:
                value = 'N/A'
            if value not in results:
                results[value] = [[], []]
            results[value][0].append(stop)
            results[value][1].append(count)
        return results
