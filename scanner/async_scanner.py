import asyncio
import socket
import struct
import time
from multiprocessing import Process
from multiprocessing.process import AuthenticationString
from threading import Thread
from typing import Union, Callable


class EchoClientProtocol:
    def __init__(self, message, on_con_lost):
        self.message = message
        self.on_con_lost = on_con_lost
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        print('Send:', self.message)
        self.transport.sendto(self.message.encode())

    def datagram_received(self, data, addr):
        print("Received:", data.decode())

        print("Close the socket")
        self.transport.close()

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        print("Connection closed")
        self.on_con_lost.set_result(True)


class AsyncPortChecker:
    def __init__(self, event_loop: asyncio.AbstractEventLoop = asyncio.get_event_loop(),
                 timeout: Union[int, float] = 10, callback: Callable = None):
        self.loop = event_loop
        self.timeout = timeout
        self.callback = callback

    async def check_async(self, ip, port, proto='TCP'):
        try:
            if proto == 'TCP':
                fut = self.loop.create_connection(asyncio.Protocol, ip, port)
                await asyncio.wait_for(fut, timeout=self.timeout)
                if self.callback and callable(self.callback):
                    self.callback(ip, port)
                return True
            return False
            # elif proto == 'UDP':
            #     on_con_lost = self.loop.create_future()
            #     fut = self.loop.create_datagram_endpoint(
            #         lambda: EchoClientProtocol('asd', on_con_lost),
            #         remote_addr=(ip, port))
            #     res = await asyncio.wait_for(fut, timeout=self.timeout)
            #     return True
        except asyncio.exceptions.TimeoutError:
            return False
        except OSError:
            return False

    def check_one(self, ip, port, proto='TCP'):
        task = self.loop.create_task(self.check_async(ip, port, proto))
        return self.loop.run_until_complete(task)

    def check_range(self, ip_a, ip_b, port):
        tasks = []
        for ip in range(ip_a, ip_b):
            ip_str = socket.inet_ntoa(struct.pack('!L', ip))
            tasks.append(self.loop.create_task(self.check_async(ip_str, port)))
        results = self.loop.run_until_complete(asyncio.gather(*tasks))
        return results

    async def check_range_async(self, ip_a, ip_b, ports):
        tasks = []
        for ip in range(ip_a, ip_b):
            ip_str = socket.inet_ntoa(struct.pack('!L', ip))
            if isinstance(ports, list):
                for port in ports:
                    tasks.append(self.loop.create_task(self.check_async(ip_str, port)))
            else:
                tasks.append(self.loop.create_task(self.check_async(ip_str, ports)))
        results = await asyncio.gather(*tasks)
        return results

    def check_many(self, ip_rows, ports):
        tasks = []
        for ip_row in ip_rows:
            tasks.append(self.loop.create_task(self.check_range_async(ip_row[1], ip_row[2], ports)))
        results = self.loop.run_until_complete(asyncio.gather(*tasks))
        return results

    async def check_many_async(self, ip_rows, port):
        tasks = []
        for ip_row in ip_rows:
            tasks.append(self.loop.create_task(self.check_range_async(ip_row[1], ip_row[2], port)))
        results = await asyncio.gather(*tasks)
        return results

    def check_all(self, ips, port, block=10):
        tasks = []
        for i in range(len(ips) // block):
            tasks.append(self.check_many_async(ips[i * block:i * block + block], port))
        result = self.loop.run_until_complete(asyncio.gather(*tasks))
        return result


class MultiProcessedAsyncPortChecker(Thread):
    def __init__(self, ip_rows, ports, block, timeout, callback, out, *args, **kwargs):
        super().__init__()
        self.ip_rows = ip_rows
        self.block = block
        self.ports = ports
        self.callback = callback
        self.out = out
        self.checker = AsyncPortChecker(
            event_loop=asyncio.new_event_loop(),
            timeout=timeout, callback=self.callback
        )
        out(self, 'Inited')

    @staticmethod
    def calc_ips(ip_range):
        total = 0
        for ip_row in ip_range:
            total += ip_row[2] - ip_row[1]
        return total

    def split_row(self, row):
        iters_amount = (row[2] - row[1]) // 25_000
        additional = (row[2] - row[1]) % 25_000
        for i in range(iters_amount):
            pad = i * 25_000
            yield row[1] + pad, row[1] + pad + 3
        else:
            if additional:
                yield row[1] + pad + 3, row[2]

    def proceed_ip_block(self, block):
        ips_amount = self.calc_ips(block)
        if ips_amount <= 25_000:
            self.checker.check_many(block, self.ports)
        else:
            print(f"[PID: {self.pid}] Block has to many IPs. Splitting")
            for row in block:
                ips_in_row = row[2] - row[1]
                if ips_in_row > 25_000:
                    for i, mini_block in enumerate(self.split_row(row)):
                        print(f"[PID: {self.pid}] Row splitted to mini blocks. Checking block index: {i}. {mini_block}")
                        start = time.perf_counter()
                        self.checker.check_range(*mini_block, self.ports)
                        print(f"[PID: {self.pid}] Mini block check end (index: {i}). "
                              f"Total time: {time.perf_counter() - start}")
                else:
                    print(f"[PID: {self.pid}] Row has {ips_in_row} IPs. Checking all.")
                    self.checker.check_range(row[1], row[2], self.ports)
        return True

    def run(self):
        for i in range(0, len(self.ip_rows), self.block):
            ips_block = self.ip_rows[i:i + self.block]
            print(f'[PID: {self.pid}][{((i + self.block) / len(self.ip_rows)) * 100:.2f}][Starting block check] Amount: {self.calc_ips(ips_block)}')
            start = time.perf_counter()
            self.proceed_ip_block(ips_block)
            total_time = time.perf_counter() - start
            print(f'[PID: {self.pid}][Block check end] Total time: {total_time}')
        print(f'[PID: {self.pid}] Finished')

    # def __getstate__(self):
    #     state = self.__dict__.copy()
    #     conf = state['_config']
    #     if 'authkey' in conf:
    #         conf['authkey'] = bytes(conf['authkey'])
    #     return state
    #
    # def __setstate__(self, state):
    #     state['_config']['authkey'] = AuthenticationString(state['_config']['authkey'])
    #     self.__dict__.update(state)
