import argparse
import typing
from multiprocessing import Queue, Process

import database
from scanner import Scanner, PortScanner
from scanner.port_scanner import scan_ports

PORTS = []

def parse_ports(ports):
    for may_port_range in ports.split(','):
        if '...' in may_port_range:
            ports = may_port_range.split('...')
            for port in range(int(ports[0]), int(ports[1]) + 1):
                yield port
        else:
            yield int(may_port_range)


class Stdout:
    def __init__(self, message_queue: Queue = Queue()):
        self.message_queue: Queue = message_queue

    def out(self, thread: Process, message):
        self.message_queue.put((thread, message))
        self._print()

    def _print(self):
        thread, message = self.message_queue.get()
        print(f'[{thread.pid}]: {message}')


def temp_callback(ip, port):
    print(f'{ip}:{port}')
    with open('out.txt', 'a') as res:
        res.write(f'{ip}:{port}\n')


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def main(country: str, ip: str, threads_amount: int, block_size: int,
         ports: typing.Iterable, timeout: float, show_output: bool,
         output_file: str):
    if country and not ip:
        ips = database.IP2Location('IPs.sqlite3')
        ips_rows = ips.country_code(country)
        rows_amount = len(ips_rows)
        threads = []
        for i in range(threads_amount):
            start = i * (rows_amount // threads_amount)
            end = start + (rows_amount // threads_amount)
            print(f"Process {i} scans range from {start} to {end}")
            thread = Scanner(ip_rows=ips_rows[start:end],
                             ports=ports,
                             block_size=block_size,
                             timeout=timeout,
                             callback=temp_callback,
                             stdout_callback=lambda t, m: print(f'[{t.pid}]: {m}'))
            thread.start()
            threads.append(thread)
    elif not country and ip:
        res = scan_ports(
            ip, ports, threads_amount, 50, 3
        )
        for process_result in res:
            for chunk_result in process_result:
                for result in chunk_result:
                    ip, port, status = result
                    if status:
                        print(ip, port)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="IP port scanner")
    parser.add_argument('-c', '--country', type=str, help="Country code. Example: US")
    parser.add_argument('-i', '--ip', type=str, help='Scan ip for ports')
    parser.add_argument('-t', '--threads', type=int, help="Threads amount", default=4)
    parser.add_argument('-b', '--block_size', type=int, help="IP blocks", default=5)
    parser.add_argument('-p', '--ports', type=str, help='Parse ports', required=True)
    parser.add_argument('-T', '--timeout', type=float, help='Timeout', default=1.5)
    parser.add_argument('-s', '--show', action='store_true', help="Print in console")
    parser.add_argument('output_file', type=str, help='Output file')
    args = parser.parse_args()
    main(country=args.country,
         ip=args.ip,
         threads_amount=args.threads,
         block_size=args.block_size,
         ports=list(parse_ports(args.ports)),
         timeout=args.timeout,
         show_output=args.show,
         output_file=args.output_file
         )
