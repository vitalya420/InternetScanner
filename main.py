import sys

import database
from scanner.async_scanner import MultiProcessedAsyncPortChecker

_, country, block, ports = sys.argv

ips = database.IP2Location('IPs.sqlite3')
ips_rows = ips.country_code(country)


def on_res(ip, port):
    print(ip, port)
    with open('out.txt', 'a') as res:
        res.write(f'{ip}:{port}\n')


rows_amount = len(ips_rows)
print(f"Rows {len(ips_rows)}")
block = int(block)

threads = 4

proc: list[MultiProcessedAsyncPortChecker] = []
for i in range(threads):
    start = i*(rows_amount // threads)
    end = start + (rows_amount // threads)
    print(start, end)
    p = MultiProcessedAsyncPortChecker(ip_rows=ips_rows[start:end], ports=[int(port) for port in ports.split(',')],
                                       block=int(block),
                                       timeout=3, callback=on_res)
    proc.append(p)

for p in proc:
    p.start()
    #p.join()
