import asyncio
import socket
import struct
import time
import typing
from multiprocessing import Process
from threading import Thread
from time import perf_counter, time


class Scanner(Process):
    def __init__(self,
                 ip_rows: list,
                 ports: typing.Iterable,
                 callback: typing.Union[typing.Callable, None] = None,
                 event_loop: asyncio.AbstractEventLoop = asyncio.new_event_loop(),
                 block_size: int = 5,
                 timeout: typing.Union[int, float] = 1.5,
                 stdout_callback: typing.Union[typing.Callable, None] = None
                 ):
        super().__init__()
        self.ip_rows = ip_rows
        self.ports = ports
        self._callback = callback
        self.event_loop = event_loop
        self.block_size = block_size
        self.timeout = timeout
        self.stdout_callback = stdout_callback

    def callback(self, *args, **kwargs):
        if self._callback and callable(self._callback):
            self._callback(*args, **kwargs)
            return True
        return False

    def stdout(self, message):
        if self.stdout_callback and callable(self.stdout_callback):
            self.stdout_callback(self, message)

    async def check_port(self, ip, port, proto="TCP"):
        if proto == 'TCP':
            fut = self.event_loop.create_connection(asyncio.Protocol, ip, port)
            try:
                await asyncio.wait_for(fut, timeout=self.timeout)
            except asyncio.exceptions.TimeoutError:
                return False
            except OSError:
                return False
            return ip, port, True
        return False

    async def check_range(self, ip_a, ip_b, ports):
        tasks = []
        for ip in range(ip_a, ip_b):
            ip_str = socket.inet_ntoa(struct.pack('!L', ip))
            if isinstance(ports, list):
                for port in ports:
                    tasks.append(self.event_loop.create_task(self.check_port(ip_str, port)))
            else:
                tasks.append(self.event_loop.create_task(self.check_port(ip_str, ports)))
        results = await asyncio.gather(*tasks)
        for result in results:
            if isinstance(result, tuple):
                self.stdout(result)
        return results

    async def check_many(self, ip_rows, port):
        tasks = []
        for ip_row in ip_rows:
            tasks.append(self.event_loop.create_task(self.check_range(ip_row[1], ip_row[2], port)))
        results = await asyncio.gather(*tasks)
        return results

    @staticmethod
    def calc_ips(ip_range):
        total = 0
        for ip_row in ip_range:
            total += ip_row[2] - ip_row[1]
        return total

    @staticmethod
    def split_row(row):
        iters_amount = (row[2] - row[1]) // 25_000
        additional = (row[2] - row[1]) % 25_000
        for i in range(iters_amount):
            pad = i * 25_000
            yield row[1] + pad, row[1] + pad + 3
        else:
            if additional:
                yield row[1] + pad + 3, row[2]

    async def proceed_ip_block(self, block):
        ips_amount = self.calc_ips(block)
        if ips_amount <= 25_000:
            await self.check_many(block, self.ports)
        else:
            self.stdout(f"Block has to many IPs. Splitting")
            for row in block:
                ips_in_row = row[2] - row[1]
                if ips_in_row > 25_000:
                    for i, mini_block in enumerate(self.split_row(row)):
                        self.stdout(f"Row splitted to mini blocks. Checking block index: {i}. {mini_block}")
                        start = perf_counter()
                        await self.check_range(*mini_block, self.ports)
                        self.stdout(f"Mini block check end (index: {i}). "
                                    f"Total time: {perf_counter() - start}")
                else:
                    self.stdout(f"Row has {ips_in_row} IPs. Checking all.")
                    await self.check_range(row[1], row[2], self.ports)
        return True

    async def _run(self):
        for i in range(0, len(self.ip_rows), self.block_size):
            ips_block = self.ip_rows[i:i + self.block_size]
            self.stdout(f'[{((i + self.block_size) / len(self.ip_rows)) * 100:.2f}]'
                        f'[Starting block check] Amount: {self.calc_ips(ips_block)}')
            start = perf_counter()
            await self.proceed_ip_block(ips_block)
            total_time = perf_counter() - start
            self.stdout(f'[Block check end] Total time: {total_time}')
        self.stdout('Finished!')

    def run(self) -> None:
        self.event_loop.run_until_complete(self._run())
