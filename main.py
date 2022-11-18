import argparse
from pprint import pprint

from sqlalchemy import create_engine

import network_scanner
from network_scanner.ip_addr import IPAddr
from network_scanner.ip_range import IPRange, import_from_csv
from network_scanner.mass_scanner import MassScanner
from network_scanner.port_checker import PortCheckerAsyncToSync, PortCheckResult
from network_scanner.range_scanner import AsyncToSyncRangeScanner

network_scanner.db_manager.setup_database(
    create_engine("postgresql://postgres:postgres@localhost/IPDB")
)


def parse_ports(ports):
    for may_port_range in ports.split(','):
        if '...' in may_port_range:
            ports = may_port_range.split('...')
            for port in range(int(ports[0]), int(ports[1]) + 1):
                yield port
        else:
            yield int(may_port_range)


def ip_lookup(ip_addr):
    return IPAddr.lookup(ip_addr)


def range_lookup(ip_addr):
    return IPRange.lookup_ip_addr(ip_addr)


def on_port_opened(res: PortCheckResult):
    print(res)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Network IP utility")
    parser.add_argument('-i', '--ip', type=str, help="Input IP")
    parser.add_argument('-l', '--lookup', action='store_true', help="IP info")
    parser.add_argument('-L', '--lookup-range', action='store_true', help="Lookup IP range")
    parser.add_argument('-p', '--ports', type=str, help="Ports")
    parser.add_argument('--ports-chunk', type=int, help="Port chunk", default=15)

    parser.add_argument('-m', '--mode', type=str, help="Work mode. [lookup, scanner, checker]", default='lookup', required=True)
    parser.add_argument('-w', '--workers', type=int, help="Pool Workers")
    parser.add_argument('-c', '--country', type=str, help="Country")
    parser.add_argument('--block-size', type=int, help="Block size", default=30)
    parser.add_argument('-T', '--timeout', type=float, help='Timeout', default=1.5)
    parser.add_argument('-f', '--file', type=str, help='Filename')

    args = parser.parse_args()
    if args.mode == 'scanner':
        country_ips = IPRange.fetch_all_by_country_code(args.country)
        scanner = MassScanner(country_ips, list(parse_ports(args.ports)), workers=args.workers,
                              block_size=args.block_size, port_chunk_size=args.ports_chunk,
                              timeout=args.timeout, callback=on_port_opened)
        scanner.start()
    elif args.mode == 'lookup':
        print(ip_lookup(args.ip).serialize())
    elif args.mode == 'db-init':
        network_scanner.db_manager.create_all()
        import_from_csv(args.file)
