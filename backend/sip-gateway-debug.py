#!/usr/bin/env python3
"""Debug gateway - minimal version."""
import asyncio
import websockets
import socket
import time

SIP_HOST = 'localphone.com'
SIP_PORT = 5060
WS_PORT = 51764

print(f'[DEBUG] Starting...', flush=True)
print(f'[DEBUG] websockets version: {websockets.__version__}', flush=True)

udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.bind(('0.0.0.0', 0))
udp_port = udp_sock.getsockname()[1]
udp_sock.setblocking(False)
print(f'[DEBUG] UDP socket bound to port {udp_port}', flush=True)

async def udp_receiver():
    loop = asyncio.get_event_loop()
    print('[DEBUG] UDP receiver started', flush=True)
    while True:
        try:
            data, addr = await loop.sock_recvfrom(udp_sock, 65535)
            print(f'[UDP IN from {addr}] {data[:200]}', flush=True)
            # Forward to clients
            for ws in list(clients):
                try:
                    await ws.send(data.decode('utf-8', errors='replace'))
                except:
                    clients.discard(ws)
        except Exception as e:
            print(f'[UDP Error] {e}', flush=True)
            await asyncio.sleep(0.1)

clients = set()

async def ws_handler(websocket):
    print(f'[WS] Connected from {websocket.remote_address}', flush=True)
    clients.add(websocket)
    try:
        async for message in websocket:
            print(f'[WS IN] {len(message)} bytes', flush=True)
            if isinstance(message, str):
                message = message.encode('utf-8')
            udp_sock.sendto(message, (SIP_HOST, SIP_PORT))
            print(f'[UDP SENT] {len(message)} bytes', flush=True)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.discard(websocket)

async def main():
    print(f'[DEBUG] Creating UDP task...', flush=True)
    udp_task = asyncio.create_task(udp_receiver())

    print(f'[DEBUG] Starting WS server on {WS_PORT}...', flush=True)
    try:
        server = await websockets.serve(ws_handler, '127.0.0.1', WS_PORT, subprotocols=['sip'])
        print(f'[DEBUG] WS server started! Ready on port {WS_PORT}', flush=True)
        await asyncio.Future()
    except Exception as e:
        print(f'[DEBUG] ERROR: {e}', flush=True)
        raise

if __name__ == '__main__':
    print(f'[DEBUG] Running main...', flush=True)
    asyncio.run(main())
