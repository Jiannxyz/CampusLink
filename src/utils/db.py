from contextlib import contextmanager

import mysql.connector
from flask import current_app
from mysql.connector import Error


def get_db_connection(app_config):
    """
    Create and return a MySQL database connection using app config dict.
    """
    try:
        connection = mysql.connector.connect(
            host=app_config["MYSQL_HOST"],
            port=app_config["MYSQL_PORT"],
            user=app_config["MYSQL_USER"],
            password=app_config["MYSQL_PASSWORD"],
            database=app_config["MYSQL_DATABASE"],
        )
        return connection
    except Error as err:
        print(f"Database connection error: {err}")
        return None


def get_connection():
    """Open a connection using the active Flask app config (requires app context)."""
    return get_db_connection(current_app.config)


@contextmanager
def db_cursor(dictionary=True):
    """
    Yields (connection, cursor). Caller commits or rolls back explicitly.
    """
    conn = get_connection()
    if conn is None:
        yield None
        return
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield conn, cursor
    finally:
        cursor.close()
        conn.close()
