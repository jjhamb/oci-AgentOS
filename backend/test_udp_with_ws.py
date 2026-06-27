#!/usr/bin/env python3
"""Test: Does having a WebSocket server listening prevent UDP reception?"""
import asyncio
import socket
import time

async def test():
    # Create UDP socket
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setblocking(False)
    udp_sock.bind(('0.0.0.0', 0))
    udp_port = udp_sock.getsockname()[1]
    print(f"[TEST] UDP socket bound to port {udp_port}")

    # Start a minimal TCP listener (like a WS server would)
    server = await asyncio.start_server(lambda r, w: None, '0.0.0.0', 0)
    tcp_port = server.sockets[0].getsockname()[1]
    print(f"[TEST] TCP server listening on port {tcp_port}")

    # Send UDP to localphone
    sip_register = (
        f"REGISTER sip:localphone.com SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP 127.0.0.1:{udp_port};branch=z9hG4bK{int(time.time())}\r\n"
        f"From: <sip:5532156@localphone.com>;tag={int(time.time())}\r\n"
        f"To: <sip:5532156@localphone.com>\r\n"
        f"Call-ID: {int(time.time())}@test\r\n"
        f"CSeq: 1 REGISTER\r\n"
        f"Contact: <sip:5532156@127.0.0.1:{udp_port}>\r\n"
        f"Max-Forwards: 70\r\n"
        f"Content-Length: 0\r\n\r\n"
    ).encode()

    print(f"[TEST] Sending UDP REGISTER to localphone.com:5060...")
    udp_sock.sendto(sip_register, ('localphone.com', 5060))

    # Try to receive with timeout
    loop = asyncio.get_event_loop()
    try:
        data = await asyncio.wait_for(loop.sock_recv(udp_sock, 4096), timeout=5.0)
        print(f"[TEST] ✓ RECEIVED {len(data)} bytes: {data[:200]}")
    except asyncio.TimeoutError:
        print(f"[TEST] ✗ TIMEOUT - no UDP response received (with TCP server listening)")

    # Now close TCP server and try again
    server.close()
    await server.wait_closed()
    print("[TEST] TCP server closed")

    udp_sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock2.setblocking(False)
    udp_sock2.bind(('0.0.0.0', 0))
    udp_port2 = udp_sock2.getsockname()[1]
    print(f"[TEST] New UDP socket bound to port {udp_port2}")

    sip_register2 = (
        f"REGISTER sip:localphone.com SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP 127.0.0.1:{udp_port2};branch=z9hG4bK{int(time.time())}\r\n"
        f"From: <sip:5532156@localphone.com>;tag={int(time.time())}\r\n"
        f"To: <sip:5532156@localphone.com>\r\n"
        f"Call-ID: {int(time.time())}@test\r\n"
        f"CSeq: 1 REGISTER\r\n"
        f"Contact: <sip:5532156@127.0.0.1:{udp_port2}>\r\n"
        f"Max-Forwards: 70\r\n"
        f"Content-Length: 0\r\n\r\n"
    ).encode()

    print(f"[TEST] Sending UDP REGISTER (no TCP server)...")
    udp_sock2.sendto(sip_register2, ('localphone.com', 5060))

    try:
        data = await asyncio.wait_for(loop.sock_recv(udp_sock2, 4096), timeout=5.0)
        print(f"[TEST] ✓ RECEIVED {len(data)} bytes: {data[:200]}")
    except asyncio.TimeoutError:
        print(f"[TEST] ✗ TIMEOUT - no UDP response (no TCP server)")

    udp_sock.close()
    udp_sock2.close()

asyncio.run(test())
