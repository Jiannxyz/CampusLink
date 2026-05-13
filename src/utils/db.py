import mysql.connector
from mysql.connector import Error


def get_db_connection(app_config):
    """
    Create and return a MySQL database connection using app config.
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
