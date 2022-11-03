import csv
import sqlite3

CREATE_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS "IPs" (
	"id"	INTEGER,
	"range_from"	INTEGER,
	"range_to"	INTEGER,
	"country_code"	TEXT,
	"country"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
"""
INSERT_QUERY = """INSERT INTO IPs (range_from, range_to, country_code, country) VALUES {}"""
value_pattern = '({}, {}, "{}", "{}")'


def convert(csv_filename, sqlite_filename):
    conn = sqlite3.connect(sqlite_filename)
    cursor = conn.cursor()
    conn.execute(CREATE_TABLE_QUERY)

    values = []
    with open(csv_filename, 'r') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for i, row in enumerate(csv_reader):
            range_from, range_to, cc, country = row
            values.append(
                value_pattern.format(range_from, range_to, cc, country)
            )
    cursor.execute(INSERT_QUERY.format(", ".join(values)))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    convert("../IPs.csv", "../IPs.sqlite3")
