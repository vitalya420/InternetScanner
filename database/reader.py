import sqlite3
from dataclasses import dataclass

IP_IN_RANGE = """SELECT * FROM IPs WHERE range_from <= ? AND range_to >= ?"""
COUNTRY_CODE = """SELECT * FROM IPs WHERE country_code = ?"""


class IP2Location:
    def __init__(self, filename):
        self.filename = filename

    def ip(self, ip_dec):
        with sqlite3.connect(self.filename) as conn:
            return conn.cursor().execute(IP_IN_RANGE, (ip_dec, ip_dec)).fetchall()

    def country_code(self, code):
        with sqlite3.connect(self.filename) as conn:
            return conn.cursor().execute(COUNTRY_CODE, (code.upper(),)).fetchall()
