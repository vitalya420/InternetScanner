import asyncio
import socket
import struct
import time
from multiprocessing import Queue
from dataclasses import dataclass
from multiprocessing import Process
from time import perf_counter, time


@dataclass
class IPStatus:
    ip: str
    port: int
    opened: bool


class Scanner(Process):
    def __init__(self, ip_rows=None):
        super().__init__()
        self.ip_rows = ip_rows
        self.event_loop = asyncio.new_event_loop()
        self.q = Queue()
        self.res_q = Queue()
        self.is_busy = False

    def scan_nowait(self, ip_range, port, callback):
        self.q.put((ip_range, port, callback))

    def scan(self, ip_range, port):
        self.q.put((ip_range, port, None))
        return self.res_q.get()

    async def await_for_scan(self):
        while True:
            item = self.q.get()
            self.is_busy = True
            ip_range, port, callback = item
            tasks = []
            for ip in range(ip_range[1], ip_range[2]):
                ip_str = socket.inet_ntoa(struct.pack('!L', ip))
                if isinstance(port, int):
                    tasks.append(asyncio.create_task(self.check_port(ip_str, port)))
                if isinstance(port, list):
                    for p in port:
                        tasks.append(asyncio.create_task(self.check_port(ip_str, p)))
            all_results = await asyncio.gather(*tasks)
            self.res_q.put(all_results)
            if callback and callable(callback):
                callback(self, all_results)
            self.is_busy = False

    def run(self) -> None:
        if self.ip_rows:
            self.event_loop.run_until_complete(self.main())
        else:
            self.event_loop.create_task(self.await_for_scan())
            self.event_loop.run_forever()

    async def check_port(self, ip=None, port=None):
        try:
            future = asyncio.open_connection(ip, port)
            try:
                await asyncio.wait_for(future, timeout=1)
            except asyncio.TimeoutError:
                return IPStatus(ip, port, False)
            return IPStatus(ip, port, True)
        except ConnectionRefusedError:
            return IPStatus(ip, port, False)
        except OSError:
            return IPStatus(ip, port, False)

    async def main(self):
        for ip_range in self.ip_rows:
            start = perf_counter()
            tasks = []
            ips_amount = ip_range[1] - ip_range[2]
            c = (ip_range[2] - ip_range[1]) // 10
            x = 10 * c, ip_range[2]

            for i in range(10):
                for ip in range(i*c, i*c+c):
                    ip_str = socket.inet_ntoa(struct.pack('!L', ip))
                    tasks.append(asyncio.create_task(self.check_port(ip_str, 25565)))
            if x[0] != x[1]:
                for ip in range(x[0], x[1]):
                    ip_str = socket.inet_ntoa(struct.pack('!L', ip))
                    tasks.append(asyncio.create_task(self.check_port(ip_str, 25565)))

            all_results = await asyncio.gather(*tasks)
            end = perf_counter()
            for res in all_results:
                if res.opened:
                    print(f'{res.ip}:{res.port}')
                    with open("out.txt", "a") as file:
                        file.write(f'{res.ip}:{res.port}\n')
            print(f"Process {self.name} just finished range in {end - start} s.)")
