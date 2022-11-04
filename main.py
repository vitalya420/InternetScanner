import sys
from threading import Thread

from mcstatus import JavaServer

import database
from scanner.async_scanner import MultiProcessedAsyncPortChecker

_, country, block, ports = sys.argv

ips = database.IP2Location('IPs.sqlite3')
ips_rows = ips.country_code(country)


def check(ip, port):
    try:
        server = JavaServer.lookup(f'{ip}:{port}', timeout=1)
        with open('good.txt', 'a') as file:
            file.write(f'{ip}:{port} {server.status().raw}\n')
    except:
        pass


def on_res(ip, port):
    try:
        Thread(target=check, args=(ip, port)).start()
        with open('out.txt', 'a') as res:
            res.write(f'{ip}:{port}\n')
    except Exception:
        pass


rows_amount = len(ips_rows)
print(f"Rows {len(ips_rows)}")
block = int(block)

threads = 4

# p = []
# for row in ips_rows:
#     amount = row[2] - row[1]
#     print(row, amount)
#     if amount not in p:
#         p.append(amount)
# print(sorted(p))


proc: list[MultiProcessedAsyncPortChecker] = []
for i in range(threads):
    start = i * (rows_amount // threads)
    end = start + (rows_amount // threads)
    print(start, end)
    p = MultiProcessedAsyncPortChecker(ip_rows=ips_rows[start:end], ports=[int(port) for port in ports.split(',')],
                                       block=int(block),
                                       timeout=1.5, callback=on_res)
    p.daemon = True
    proc.append(p)

for p in proc:
    p.start()
#     #p.join()
