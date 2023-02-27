import sys

import click
import pymysql
from flask import current_app, g

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


def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(host=current_app.config['HOST'],
                               port=current_app.config['PORT'],
                               user=current_app.config['USER'],
                               passwd=current_app.config['PASSWORD'],
                               db=current_app.config['DATABASE'])
    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


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

    db = get_db()

    with current_app.open_resource('stations_schema.sql') as fd:
        # Read in the schema
        contents = fd.read().decode('utf8')
        # It can consist of several SQL statements. Split on the semicolon. Get rid of any resultant empty
        # statements. Add the semicolon back in.
        queries = ["%s;" % q.strip() for q in contents.split(';') if q.strip()]
        # Now execute them one by one
        with db.cursor() as cursor:
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
    """Insert the station information into the database."""

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
    db_conn = db.get_db()
    with db_conn.cursor() as cursor:
        cursor.execute('SELECT last_seen FROM weereg.stations WHERE station_url=%s ORDER BY last_seen DESC LIMIT 1', station_url)
        result = cursor.fetchone()
        last_seen = result[0] if result else None
        return last_seen
