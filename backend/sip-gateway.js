#!/usr/bin/env node
/**
 * SIP Gateway v4: WebSocket → Python UDP bridge → Localphone
 * Uses a Python child process for UDP to avoid Node.js dgram issues.
 * Protocol: 4-byte big-endian length prefix + message data.
 */
const http = require('http');
const { WebSocketServer } = require('ws');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const WS_PORT = 51764;
const SIP_HOST = 'localphone.com';
const SIP_PORT = 5060;

// Track connected WS clients
const connectedClients = new Set();

// Spawn Python UDP bridge
const bridgeScript = path.join(__dirname, 'udp-bridge.py');
console.log(`[Gateway] Starting Python UDP bridge: ${bridgeScript}`);

const udpBridge = spawn('python3', [bridgeScript], {
  stdio: ['pipe', 'pipe', 'pipe'],
});

let udpReady = false;
let udpPort = null;

let stdoutBuf = Buffer.alloc(0);

udpBridge.stdout.on('data', (data) => {
  // Append to buffer
  stdoutBuf = Buffer.concat([stdoutBuf, data]);
  
  // Process complete messages
  while (stdoutBuf.length >= 4) {
    const msgLen = stdoutBuf.readUInt32BE(0);
    if (stdoutBuf.length < 4 + msgLen) {
      break; // Wait for more data
    }
    
    const sipResponse = stdoutBuf.slice(4, 4 + msgLen).toString('utf8');
    stdoutBuf = stdoutBuf.slice(4 + msgLen);
    
    console.log(`[UDP IN] ${sipResponse.split('\r\n')[0]}`);
    
    // Forward to all connected WS clients
    for (const ws of connectedClients) {
      if (ws.readyState === 1) {
        ws.send(Buffer.from(sipResponse, 'utf8'));
        console.log(`[WS OUT] Forwarded ${sipResponse.length} bytes`);
      }
    }
  }
});

udpBridge.stderr.on('data', (data) => {
  const lines = data.toString().split('\n').filter(l => l.trim());
  for (const line of lines) {
    if (line.startsWith('READY ')) {
      udpPort = parseInt(line.split(' ')[1]);
      udpReady = true;
      console.log(`[UDP Bridge] Ready on port ${udpPort}`);
    } else {
      console.log(`[UDP Bridge] ${line}`);
    }
  }
});

udpBridge.on('close', (code) => {
  console.log(`[UDP Bridge] Exited with code ${code}`);
});

udpBridge.on('error', (err) => {
  console.error(`[UDP Bridge] Spawn error: ${err.message}`);
});

// HTTP + WebSocket server
const server = http.createServer();
const wss = new WebSocketServer({
  server,
  handleProtocols: (protocols) => {
    if (protocols && protocols.includes('sip')) return 'sip';
    return false;
  },
});

wss.on('connection', (ws, req) => {
  console.log(`[WS] Connected from ${req.socket.remoteAddress}`);
  connectedClients.add(ws);

  ws.on('message', (data) => {
    const buf = Buffer.isBuffer(data) ? data : Buffer.from(data);
    const sipMsg = buf.toString('utf8');
    console.log(`[WS IN] ${sipMsg.split('\r\n')[0]} (${buf.length} bytes)`);

    if (udpReady && udpBridge.stdin.writable) {
      // Send length-prefixed message to Python bridge
      const lenBuf = Buffer.alloc(4);
      lenBuf.writeUInt32BE(buf.length);
      udpBridge.stdin.write(lenBuf);
      udpBridge.stdin.write(buf);
    } else {
      console.log('[UDP Bridge] Not ready, dropping message');
    }
  });

  ws.on('close', (code) => {
    console.log(`[WS] Disconnected: code=${code}`);
    connectedClients.delete(ws);
  });

  ws.on('error', (err) => console.error('[WS Error]', err.message));
});

server.listen(WS_PORT, '127.0.0.1', () => {
  console.log(`SIP Gateway v4: ws://127.0.0.1:${WS_PORT}/ws → Python UDP → ${SIP_HOST}:${SIP_PORT}`);
});
