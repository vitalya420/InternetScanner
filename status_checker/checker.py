import asyncio
import socket

from mcstatus import JavaServer

ips = """193.30.244.182:25565
193.34.95.127:25565
193.37.192.221:25565
193.104.203.36:25565
193.106.58.33:25565
"""


async def check(address=None, ip=None, port=None):
    try:
        server = await JavaServer.async_lookup(address or f'{ip}:{port}', timeout=1)
        print(f'{address} {server.status().raw}')
        with open('good.txt', 'a') as file:
            file.write(f'{address} {server.status().raw}\n')
    except socket.timeout:
        print("timeout")
    except OSError:
        print('Pizda OSError')


loop = asyncio.get_event_loop()
tasks = []
for ip in ips.split('\n'):
    tasks.append(loop.create_task(check(ip)))
asyncio.gather(*tasks)
loop.run_forever()
