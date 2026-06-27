#!/usr/bin/env python3
"""
UDP bridge: reads SIP messages from stdin, sends via UDP to localphone.com:5060,
writes UDP responses to stdout.
Protocol: 4-byte big-endian length prefix + message data (both directions).
Uses select() + non-blocking I/O to handle stdin and UDP socket concurrently.
"""
import socket
import sys
import struct
import select
import os
import fcntl

SIP_HOST = 'localphone.com'
SIP_PORT = 5060

# Set stdin to non-blocking
stdin_fd = sys.stdin.buffer.fileno()
fl = fcntl.fcntl(stdin_fd, fcntl.F_GETFL)
fcntl.fcntl(stdin_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 0))
port = sock.getsockname()[1]
print(f'READY {port}', file=sys.stderr, flush=True)

stdin_buf = b''

def try_read_stdin():
    """Try to read from stdin (non-blocking). Returns a complete message or None."""
    global stdin_buf
    try:
        chunk = os.read(stdin_fd, 65535)
        if chunk:
            stdin_buf += chunk
    except BlockingIOError:
        pass
    
    if len(stdin_buf) < 4:
        return None
    
    msg_len = struct.unpack('>I', stdin_buf[:4])[0]
    if len(stdin_buf) < 4 + msg_len:
        return None
    
    msg = stdin_buf[4:4+msg_len]
    stdin_buf = stdin_buf[4+msg_len:]
    return msg

def send_response(sip_msg):
    """Send a SIP response to stdout with length prefix."""
    data = sip_msg.encode('utf-8') if isinstance(sip_msg, str) else sip_msg
    sys.stdout.buffer.write(struct.pack('>I', len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()

while True:
    # Wait for UDP response or stdin readability
    readable, _, _ = select.select([sock], [], [], 0.1)
    
    if sock in readable:
        data, addr = sock.recvfrom(65535)
        response_str = data.decode('utf-8', errors='replace')
        print(f'RESPONSE from {addr[0]}:{addr[1]}: {response_str.split(chr(13)+chr(10))[0]}', file=sys.stderr, flush=True)
        send_response(response_str)
    
    # Try to read from stdin (non-blocking)
    msg = try_read_stdin()
    if msg:
        sock.sendto(msg, (SIP_HOST, SIP_PORT))
        sip_str = msg.decode('utf-8', errors='replace')
        print(f'SENT {len(msg)} bytes: {sip_str.split(chr(13)+chr(10))[0]}', file=sys.stderr, flush=True)
