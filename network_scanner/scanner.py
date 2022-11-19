import asyncio
import sys
import time
from multiprocessing import Process, Queue

from network_scanner import utils
from network_scanner.ip_range import IPRange
from network_scanner.port_checker import PortCheckerAsync


class Worker(Process):
    def __init__(self, ips: list[IPRange], ports, timeout, ip_chunk_size, port_chunk_size, print_q=None, id_=0,
                 **kwargs):
        super().__init__()
        self.id_ = id_
        self.ips = ips
        self.ports = ports
        self.timeout = timeout
        self.ip_chunks_size = ip_chunk_size
        self.port_chunk_size = port_chunk_size
        self.print_q = print_q
        self.loop = asyncio.new_event_loop()
        self._port_checker = PortCheckerAsync(event_loop=self.loop, **kwargs)
        self._total_ip_addr = utils.total_ip_addr(self.ips)
        self.completed = 0

    def print(self, message=None):
        self.print_q.put((self.name, f'[{self.name}][{self.progress:.02f}%]'))

    async def work(self):
        async for res in self._port_checker.check_many(self.ips, self.ports,
                                                       self.timeout, self.ip_chunks_size, self.port_chunk_size):
            self.completed += len(res)
            self.print()

    @property
    def progress(self):
        p = (self.completed / (self._total_ip_addr * len(self.ports))) * 100
        return 100 if p > 100 else p

    def run(self):
        self.loop.run_until_complete(self.work())

    def __repr__(self):
        return f"<Worker(id={self.id_}, ips={self.ips})>"


def update_print(q):
    messages = {}
    while True:
        name, message = q.get()
        messages[name] = message
        print(message)
        time.sleep(1)


class WorkManager:
    def __init__(self, workers=None):
        if workers is None:
            workers = []
        self.workers = workers
        self.__i = 0
        self.q = Queue()

    def create_worker(self, ips, ports, timeout=3, ip_chunk_size=None, port_chunk_size=None, **kwargs):
        worker = Worker(ips, ports, timeout, ip_chunk_size, port_chunk_size, print_q=self.q, **kwargs)
        self.__i += 1
        self.workers.append(worker)
        return worker

    def start(self):
        Process(target=update_print, args=(self.q,)).start()
        for worker in self.workers:
            worker.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return
