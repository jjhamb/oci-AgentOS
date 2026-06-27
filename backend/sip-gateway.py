#!/usr/bin/env python3
"""
SIP Gateway: WebSocket server + UDP bridge for Localphone.
Runs as a standalone process — no Node.js needed.
Listens on port 51764 for WebSocket connections from SIP.js.
Bridges SIP messages between WebSocket (browser) and UDP (Localphone).
"""
import asyncio
import websockets
import socket
import json
import sys
import os
import time

SIP_HOST = 'localphone.com'
SIP_PORT = 5060
WS_PORT = 51764

# Create UDP socket
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.bind(('0.0.0.0', 0))
udp_port = udp_sock.getsockname()[1]
udp_sock.setblocking(False)

print(f'[Gateway] UDP socket bound to port {udp_port}', flush=True)
print(f'[Gateway] Bridging WS port {WS_PORT} -> UDP {SIP_HOST}:{SIP_PORT}', flush=True)

# Track connected WebSocket clients
clients = set()

async def udp_receiver():
    """Receive UDP responses from Localphone and forward to WS clients."""
    loop = asyncio.get_event_loop()
    print('[Gateway] UDP receiver started', flush=True)
    while True:
        try:
            data, addr = await loop.sock_recvfrom(udp_sock, 65535)
            sip_response = data.decode('utf-8', errors='replace')
            first_line = sip_response.split('\r\n')[0]
            print(f'[Gateway] UDP IN from {addr[0]}:{addr[1]}: {first_line}', flush=True)

            # Forward to all connected WS clients
            if clients:
                disconnected = set()
                for ws in list(clients):
                    try:
                        await ws.send(sip_response)
                        print(f'[Gateway] WS OUT: Forwarded {len(data)} bytes', flush=True)
                    except Exception as e:
                        print(f'[Gateway] WS OUT error: {e}', flush=True)
                        disconnected.add(ws)
                clients -= disconnected
            else:
                print('[Gateway] UDP IN: No clients connected, dropped', flush=True)
        except Exception as e:
            print(f'[Gateway] UDP error: {e}', flush=True)
            await asyncio.sleep(0.1)

async def ws_handler(websocket):
    """Handle a WebSocket connection from SIP.js."""
    client_addr = websocket.remote_address
    print(f'[Gateway] WS connected from {client_addr}', flush=True)
    clients.add(websocket)

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                data = message
            else:
                data = message.encode('utf-8')

            sip_msg = data.decode('utf-8', errors='replace')
            first_line = sip_msg.split('\r\n')[0]
            print(f'[Gateway] WS IN: {first_line} ({len(data)} bytes)', flush=True)

            # Send via UDP to Localphone (use sync sendto to avoid event loop conflict)
            udp_sock.sendto(data, (SIP_HOST, SIP_PORT))
            print(f'[Gateway] UDP OUT: {len(data)} bytes to {SIP_HOST}:{SIP_PORT}', flush=True)
    except websockets.exceptions.ConnectionClosed as e:
        print(f'[Gateway] WS disconnected: code={e.code}', flush=True)
    finally:
        clients.discard(websocket)

async def main():
    # Start UDP receiver task
    udp_task = asyncio.create_task(udp_receiver())

    # Start WebSocket server (using await, not async with)
    print(f'[Gateway] Starting WS server on port {WS_PORT}...', flush=True)
    server = await websockets.serve(
        ws_handler, '127.0.0.1', WS_PORT,
        subprotocols=['sip'],
        ping_interval=30,
        ping_timeout=10
    )
    print(f'[Gateway] Ready! ws://127.0.0.1:{WS_PORT} -> UDP {SIP_HOST}:{SIP_PORT}', flush=True)

    # Run forever
    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        pass
    finally:
        server.close()
        await server.wait_closed()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n[Gateway] Shutting down', flush=True)
