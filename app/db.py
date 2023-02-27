import sys

import click
import pymysql
from flask import current_app, g


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
