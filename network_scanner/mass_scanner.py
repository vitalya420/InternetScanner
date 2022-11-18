import asyncio
import typing
from multiprocessing import Pool

from network_scanner import utils
from network_scanner.ip_range import IPRange
from network_scanner.range_scanner import AsyncRangeScanner


class MassScanner:
    def __init__(self, ips: list[IPRange],
                 ports: typing.Iterable,
                 workers: int = 4,
                 block_size: int = 5,
                 port_chunk_size: int = 10,
                 timeout: int = 3,
                 callback: typing.Callable = None):
        self.ips = ips
        self.ports = ports
        self.workers = workers
        self.block_size = block_size
        self.port_chunk_size = port_chunk_size
        self.timeout = timeout
        self.callback = callback

    def split(self):
        for i, ips_chunks in enumerate(utils.chunks(self.ips, len(self.ips) // self.workers)):
            yield i, ips_chunks

    async def check_many(self, ip_block, loop):
        tasks = []
        for ip_range in ip_block:
            scanner = AsyncRangeScanner(ip_range[0], ports=self.ports,
                                        event_loop=loop, timeout=self.timeout,
                                        callback=self.callback)
            tasks.append(loop.create_task(scanner.check_ports()))
        res = await asyncio.gather(*tasks)
        return res

    @staticmethod
    def ips_amount(ip_block):
        return sum([len(ip_range[0]) for ip_range in ip_block])

    def work(self, ips):
        worker_id, ip_chunk = ips
        all_ip_blocks = list(utils.chunks(ip_chunk, self.block_size))

        for i, ip_block in enumerate(list(utils.chunks(ip_chunk, self.block_size))):
            print(f"Worker {worker_id} starts checking {len(ip_block)} ip ranges: {self.ips_amount(ip_block)}")
            loop = asyncio.new_event_loop()
            task = loop.create_task(self.check_many(ip_block, loop))
            res = loop.run_until_complete(task)
            print(f"Worker id: {worker_id}. Done {i} / {len(all_ip_blocks)}")

    def start(self):
        with Pool(self.workers) as pool:
            pool.map(self.work, self.split())
