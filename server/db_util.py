import mysql.connector
from mysql.connector import Error
import io
import json
from datetime import date, datetime


def create_db_connection(host_name, user_name, user_password, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name, user=user_name, passwd=user_password, database=db_name
        )
        print("MySQL Database connection successful")
    except Error as err:
        print(f"Error: '{err}'")

    return connection


def execute_query(connection, query, params=()):
    cursor = connection.cursor()
    try:
        cursor.execute(query, params)
        connection.commit()
        print("Query successful")
    except Error as err:
        print(f"Error: '{err}'")


def read_query(connection, query, params=(), as_json=False):
    cursor = connection.cursor()
    result = None
    try:
        cursor.execute(query, params)
        if as_json:
            return getJson(cursor)
        else:
            result = cursor.fetchall()

        return result
    except Error as err:
        print(f"Error: '{err}'")


def getJson(cursor):
    row_headers = [x[0] for x in cursor.description]  # this will extract row headers
    rv = cursor.fetchall()
    json_data = []
    for result in rv:
        json_data.append(dict(zip(row_headers, result)))
    return json_data


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date, bytes)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def getFlightNum(connection):
    query = "SELECT max(flightNum) from image_records;"
    res = read_query(connection, query)
    if len(res) == 0:
        return res[0][0]
    else:
        return 1