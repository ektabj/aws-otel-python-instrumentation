# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import atexit
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Tuple

import mysql.connector as mysql
from typing_extensions import override

_SELECT: str = "select"
_CREATE_DATABASE: str = "create_database"
_DROP_TABLE: str = "drop_table"
_FAULT: str = "fault"
_PORT: int = 8080

_DB_HOST = os.getenv("DB_HOST")
_DB_USER = os.getenv("DB_USER")
_DB_PASS = os.getenv("DB_PASS")
_DB_NAME = os.getenv("DB_NAME")


class RequestHandler(BaseHTTPRequestHandler):
    @override
    # pylint: disable=invalid-name
    def do_GET(self):
        status_code: int = 200
        conn = mysql.connect(host=_DB_HOST, user=_DB_USER, password=_DB_PASS, database=_DB_NAME)
        conn.autocommit = True  # CREATE DATABASE cannot run in a transaction block
        if self.in_path(_SELECT):
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM employee")
            result = cur.fetchall()
            cur.close()
            status_code = 200 if len(result) == 1 else 500
        elif self.in_path(_DROP_TABLE):
            cur = conn.cursor()
            cur.execute("DROP TABLE IF EXISTS test_table")
            cur.close()
            status_code = 200
        elif self.in_path(_CREATE_DATABASE):
            cur = conn.cursor()
            cur.execute("CREATE DATABASE test_database")
            cur.close()
            status_code = 200
        elif self.in_path(_FAULT):
            cur = conn.cursor()
            try:
                cur.execute("SELECT DISTINCT id, name FROM invalid_table")
            except mysql.ProgrammingError as exception:
                print("Expected Exception with Invalid SQL occurred:", exception)
                status_code = 500
            except Exception as exception:  # pylint: disable=broad-except
                print("Exception Occurred:", exception)
            else:
                status_code = 200
            finally:
                cur.close()
        else:
            status_code = 404
        conn.close()
        self.send_response_only(status_code)
        self.end_headers()

    def in_path(self, sub_path: str):
        return sub_path in self.path


def prepare_db_server() -> None:
    conn = mysql.connect(host=_DB_HOST, user=_DB_USER, password=_DB_PASS, database=_DB_NAME)
    cur = conn.cursor()
    cur.execute("SHOW TABLES LIKE 'employee'")
    result = cur.fetchone()
    if not result:
        cur.execute("CREATE TABLE employee (id int, name varchar(255))")
        cur.execute("INSERT INTO employee (id, name) values (1, 'A')")
    cur.close()
    conn.close()


def main() -> None:
    prepare_db_server()
    server_address: Tuple[str, int] = ("0.0.0.0", _PORT)
    request_handler_class: type = RequestHandler
    requests_server: ThreadingHTTPServer = ThreadingHTTPServer(server_address, request_handler_class)
    atexit.register(requests_server.shutdown)
    server_thread: Thread = Thread(target=requests_server.serve_forever)
    server_thread.start()
    print("Ready")
    server_thread.join()


if __name__ == "__main__":
    main()
