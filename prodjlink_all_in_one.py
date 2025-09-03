#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProDJLink Web监控器 - 单文件版本
包含WebSocket服务器和HTML界面的完整监控系统
"""

import asyncio
import websockets
import socket
import json
import struct
import threading
from datetime import datetime
import logging
import sys
import io
import webbrowser
import time
import os
import tempfile
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# HTML内容
HTML_CONTENT = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ProDJLink Monitor - All-in-One</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
            background: #f5f5f5;
            color: #3b3b3b;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* 标题栏 */
        .titlebar {
            background: #2c3e50;
            color: white;
            padding: 1rem 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .titlebar h1 {
            font-size: 1.5rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .titlebar .controls {
            display: flex;
            gap: 1rem;
        }

        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-primary {
            background: #4CAF50;
            color: white;
        }

        .btn-primary:hover {
            background: #45a049;
        }

        .btn-danger {
            background: #f44336;
            color: white;
        }

        .btn-danger:hover {
            background: #da190b;
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        /* 连接状态 */
        .connection-status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
        }

        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #ccc;
        }

        .status-indicator.online {
            background: #4CAF50;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        /* 主内容区 */
        .main-content {
            flex: 1;
            background: white;
            display: flex;
            flex-direction: column;
        }

        /* 提示信息 */
        .info-banner {
            background: #2196F3;
            color: white;
            padding: 0.75rem;
            text-align: center;
            font-size: 0.9rem;
        }

        /* 设备卡片 */
        .devices-container {
            padding: 1rem;
        }

        .device-card {
            display: grid;
            grid-template-columns: 100px 1fr;
            gap: 1rem;
            padding: 1rem;
            border-bottom: 1px solid #eee;
            animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* 设备指示器 */
        .device-indicator {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
            padding-right: 1rem;
            border-right: 1px solid #eee;
        }

        .player-id {
            font-size: 0.875rem;
            font-weight: 700;
            background: #3b434b;
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 3px;
            min-width: 40px;
            text-align: center;
        }

        .player-id.onair {
            background: #ff5757;
        }

        .device-icon {
            width: 48px;
            height: 48px;
            background: #f0f0f0;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }

        /* 设备状态 */
        .device-status {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .status-row {
            display: flex;
            gap: 0.5rem;
            align-items: center;
            flex-wrap: wrap;
        }

        .play-state {
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.25rem 0.75rem;
            text-transform: uppercase;
            border-radius: 3px;
            min-width: 80px;
            text-align: center;
        }

        /* 播放状态颜色 */
        .play-state.empty { background: #f1f1f1; color: #999; }
        .play-state.loading { background: #E9E9E9; color: #666; }
        .play-state.playing { background: #81F14C; color: #2d5016; }
        .play-state.looping { background: #FFD466; color: #7a5f00; }
        .play-state.paused { background: #78DFFF; color: #00506b; }
        .play-state.cued { background: #FFC266; color: #7a4f00; }
        .play-state.cuing { background: #FF9466; color: #7a2f00; }
        .play-state.searching { background: #B378FF; color: #4a0080; }
        .play-state.ended { background: #FF6666; color: #7a0000; }

        /* BPM指示器 */
        .bpm-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.25rem 0.75rem;
            background: #f8f8f8;
            border-radius: 3px;
            font-size: 0.875rem;
        }

        .bpm-value {
            font-weight: 600;
            color: #2c3e50;
        }

        .pitch-value {
            font-size: 0.75rem;
            color: #666;
        }

        /* 节拍计数器 */
        .beat-counter {
            display: flex;
            gap: 0.25rem;
        }

        .beat-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #ddd;
            transition: all 0.1s;
        }

        .beat-dot.active {
            background: #4CAF50;
            transform: scale(1.2);
        }

        /* 元数据显示 */
        .metadata-container {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 0.75rem;
            padding: 0.5rem;
            background: #fafafa;
            border-radius: 4px;
            margin-top: 0.5rem;
        }

        .metadata-container.no-track {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
            color: #999;
            font-size: 0.875rem;
            text-transform: uppercase;
        }

        .artwork {
            width: 48px;
            height: 48px;
            border-radius: 3px;
            background: #e0e0e0;
            object-fit: cover;
        }

        .track-info {
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 0.125rem;
        }

        .track-title {
            font-weight: 600;
            font-size: 0.9rem;
            color: #2c3e50;
        }

        .track-artist {
            font-size: 0.8rem;
            color: #666;
        }

        .track-details {
            display: flex;
            gap: 1rem;
            margin-top: 0.25rem;
            font-size: 0.7rem;
            color: #999;
        }

        /* 其他设备 */
        .other-devices {
            display: flex;
            gap: 2rem;
            padding: 1rem;
            border-bottom: 1px solid #eee;
            flex-wrap: wrap;
        }

        .small-device {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem;
            background: #f8f8f8;
            border-radius: 4px;
        }

        .small-device-icon {
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
        }

        .device-info {
            font-size: 0.75rem;
        }

        .device-name {
            font-weight: 600;
        }

        .device-ip {
            color: #666;
        }

        /* 无设备提示 */
        .no-devices {
            padding: 3rem;
            text-align: center;
            color: #999;
        }

        .no-devices h2 {
            margin-bottom: 1rem;
            color: #666;
        }

        /* 页脚 */
        .footer {
            background: #f8f8f8;
            padding: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid #e0e0e0;
        }

        .stats {
            display: flex;
            gap: 2rem;
            font-size: 0.875rem;
        }

        .stat-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .stat-label {
            color: #666;
        }

        .stat-value {
            font-weight: 600;
            color: #2c3e50;
        }

        /* 响应式设计 */
        @media (max-width: 768px) {
            .device-card {
                grid-template-columns: 1fr;
            }

            .device-indicator {
                flex-direction: row;
                justify-content: center;
                border-right: none;
                border-bottom: 1px solid #eee;
                padding-bottom: 0.5rem;
            }

            .metadata-container {
                grid-template-columns: 1fr;
                text-align: center;
            }

            .artwork {
                margin: 0 auto;
            }
        }
    </style>
</head>
<body>
    <!-- 标题栏 -->
    <div class="titlebar">
        <h1>
            <span>🎧</span>
            <span>ProDJLink Monitor (All-in-One)</span>
        </h1>
        <div class="connection-status">
            <span class="status-indicator online"></span>
            <span id="statusText">已连接</span>
        </div>
        <div class="controls">
            <button class="btn btn-danger" id="refreshBtn">刷新页面</button>
        </div>
    </div>

    <!-- 信息横幅 -->
    <div class="info-banner">
        WebSocket服务器运行在 ws://localhost:8080 | 监听UDP端口 50000-50002
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
        <!-- 设备列表 -->
        <div class="devices-container" id="devicesContainer">
            <div class="no-devices" id="noDevices">
                <h2>等待设备连接...</h2>
                <p>请确保：</p>
                <ul style="list-style: none; margin-top: 1rem; line-height: 1.8;">
                    <li>✓ DJ设备已开启并连接到同一网络</li>
                    <li>✓ ProDJLink功能已启用</li>
                    <li>✓ 防火墙允许UDP端口 50000-50002</li>
                    <li>✓ 开始播放音乐以查看状态</li>
                </ul>
            </div>
        </div>

        <!-- 其他设备 -->
        <div class="other-devices" id="otherDevices">
            <!-- Mixer和Rekordbox设备将在这里显示 -->
        </div>
    </div>

    <!-- 页脚 -->
    <div class="footer">
        <div class="stats">
            <div class="stat-item">
                <span class="stat-label">设备:</span>
                <span class="stat-value" id="deviceCount">0</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">数据包:</span>
                <span class="stat-value" id="packetCount">0</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">状态更新:</span>
                <span class="stat-value" id="updateCount">0</span>
            </div>
        </div>
        <div style="font-size: 0.75rem; color: #999;">
            <span id="currentTime"></span>
        </div>
    </div>

    <script>
        // ProDJLink Web监控器
        class ProDJLinkMonitor {
            constructor() {
                this.ws = null;
                this.devices = new Map();
                this.stats = {
                    packets: 0,
                    updates: 0,
                    devices: 0
                };
                this.beatTimers = new Map();
                this.initializeUI();
                this.connect();
            }

            initializeUI() {
                // 刷新按钮
                document.getElementById('refreshBtn').addEventListener('click', () => {
                    location.reload();
                });

                // 更新时间
                this.updateTime();
                setInterval(() => this.updateTime(), 1000);
            }

            connect() {
                // 自动连接到本地WebSocket服务器
                this.ws = new WebSocket('ws://localhost:8080');

                this.ws.onopen = () => {
                    console.log('WebSocket连接成功');
                    document.getElementById('statusText').textContent = '已连接';
                };

                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket错误:', error);
                    document.getElementById('statusText').textContent = '连接错误';
                };

                this.ws.onclose = () => {
                    document.getElementById('statusText').textContent = '已断开';
                    // 3秒后自动重连
                    setTimeout(() => this.connect(), 3000);
                };
            }

            handleMessage(data) {
                // 隐藏无设备提示
                const noDevices = document.getElementById('noDevices');
                if (noDevices) {
                    noDevices.style.display = 'none';
                }

                switch(data.type) {
                    case 'device':
                        this.updateDevice(data.device);
                        break;
                    case 'status':
                        this.updateStatus(data.status);
                        break;
                    case 'beat':
                        this.updateBeat(data.beat);
                        break;
                }
                this.updateStats();
            }

            updateDevice(device) {
                this.devices.set(device.id, device);
                this.renderDevices();
            }

            updateStatus(status) {
                const device = this.devices.get(status.deviceId);
                if (device) {
                    device.status = status;
                    this.renderDeviceCard(status.deviceId);
                }
                this.stats.updates++;
            }

            updateBeat(beat) {
                const deviceCard = document.querySelector(`[data-device-id="${beat.deviceId}"]`);
                if (deviceCard) {
                    this.animateBeat(beat.deviceId, beat.position);
                }
            }

            renderDevices() {
                const cdjs = Array.from(this.devices.values())
                    .filter(d => d.type === 'CDJ')
                    .sort((a, b) => a.id - b.id);

                const others = Array.from(this.devices.values())
                    .filter(d => d.type !== 'CDJ');

                // 渲染CDJ设备
                cdjs.forEach(device => this.renderDeviceCard(device.id));

                // 渲染其他设备
                this.renderOtherDevices(others);
            }

            renderDeviceCard(deviceId) {
                const device = this.devices.get(deviceId);
                if (!device || device.type !== 'CDJ') return;

                let card = document.querySelector(`[data-device-id="${deviceId}"]`);
                if (!card) {
                    card = document.createElement('div');
                    card.className = 'device-card';
                    card.dataset.deviceId = deviceId;
                    document.getElementById('devicesContainer').appendChild(card);
                }

                const status = device.status || {};
                const onAir = status.isOnAir ? 'onair' : '';

                card.innerHTML = `
                    <div class="device-indicator">
                        <div class="player-id ${onAir}">${deviceId.toString().padStart(2, '0')}</div>
                        <div class="device-icon">💿</div>
                    </div>
                    <div class="device-status">
                        <div class="status-row">
                            <div class="play-state ${this.getPlayStateClass(status.playState)}">
                                ${this.getPlayStateText(status.playState)}
                            </div>
                            <div class="beat-counter" id="beat-${deviceId}">
                                <span class="beat-dot"></span>
                                <span class="beat-dot"></span>
                                <span class="beat-dot"></span>
                                <span class="beat-dot"></span>
                            </div>
                            <div class="bpm-indicator">
                                <span class="bpm-value">${status.bpm ? status.bpm.toFixed(2) : '--'} BPM</span>
                                <span class="pitch-value">${status.pitch ? (status.pitch > 0 ? '+' : '') + status.pitch.toFixed(2) + '%' : ''}</span>
                            </div>
                            ${status.time ? `<div style="font-size: 0.875rem; color: #666;">⏱️ ${status.time}</div>` : ''}
                        </div>
                        ${this.renderMetadata(status)}
                    </div>
                `;
            }

            renderMetadata(status) {
                if (!status.track) {
                    return '<div class="metadata-container no-track">No Track Loaded</div>';
                }

                // 处理真实数据
                const track = status.track;
                const title = track.title || `Track ID: ${track.id ? track.id.toString(16).toUpperCase().padStart(8, '0') : 'Unknown'}`;
                const artist = track.artist || '';
                const hasDetails = track.format || track.duration || track.key || track.genre;

                return `
                    <div class="metadata-container">
                        ${status.artwork ? `<img class="artwork" src="${status.artwork}" alt="Album Art">` : '<div class="artwork"></div>'}
                        <div class="track-info">
                            <div class="track-title">${title}</div>
                            ${artist ? `<div class="track-artist">${artist}</div>` : ''}
                            ${hasDetails ? `
                                <div class="track-details">
                                    ${track.format ? `<span class="file-type">${track.format}</span>` : ''}
                                    ${track.duration ? `<span>${this.formatDuration(track.duration)}</span>` : ''}
                                    ${track.key ? `<span>${track.key}</span>` : ''}
                                    ${track.genre ? `<span>${track.genre}</span>` : ''}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            }

            renderOtherDevices(devices) {
                const container = document.getElementById('otherDevices');
                if (devices.length === 0) {
                    container.innerHTML = '';
                    return;
                }
                
                container.innerHTML = devices.map(device => `
                    <div class="small-device">
                        <div class="small-device-icon">
                            ${device.type === 'Mixer' ? '🎛️' : '💻'}
                        </div>
                        <div class="device-info">
                            <div class="device-name">${device.name || device.type}</div>
                            <div class="device-ip">${device.ip}</div>
                        </div>
                    </div>
                `).join('');
            }

            animateBeat(deviceId, position) {
                const beatCounter = document.getElementById(`beat-${deviceId}`);
                if (!beatCounter) return;

                const dots = beatCounter.querySelectorAll('.beat-dot');
                dots.forEach((dot, index) => {
                    dot.classList.toggle('active', index === (position - 1));
                });

                // 自动清除活动状态
                clearTimeout(this.beatTimers.get(deviceId));
                const timer = setTimeout(() => {
                    dots.forEach(dot => dot.classList.remove('active'));
                }, 200);
                this.beatTimers.set(deviceId, timer);
            }

            getPlayStateClass(state) {
                const stateMap = {
                    0: 'empty',
                    2: 'loading',
                    3: 'playing',
                    4: 'looping',
                    5: 'paused',
                    6: 'cued',
                    7: 'cuing',
                    9: 'searching',
                    17: 'ended'
                };
                return stateMap[state] || 'empty';
            }

            getPlayStateText(state) {
                const textMap = {
                    0: 'Empty',
                    2: 'Loading',
                    3: 'Playing',
                    4: 'Looping',
                    5: 'Paused',
                    6: 'Cued',
                    7: 'Cuing',
                    9: 'Searching',
                    17: 'Ended'
                };
                return textMap[state] || 'Unknown';
            }

            formatDuration(seconds) {
                const mins = Math.floor(seconds / 60);
                const secs = seconds % 60;
                return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            }

            updateStats() {
                document.getElementById('deviceCount').textContent = this.devices.size;
                document.getElementById('packetCount').textContent = ++this.stats.packets;
                document.getElementById('updateCount').textContent = this.stats.updates;
            }

            updateTime() {
                const now = new Date();
                document.getElementById('currentTime').textContent = now.toLocaleString('zh-CN');
            }
        }

        // 初始化监控器
        const monitor = new ProDJLinkMonitor();
    </script>
</body>
</html>'''

class ProDJLinkWebSocketServer:
    def __init__(self, websocket_port=8080):
        # ProDJLink协议魔术头
        self.PROLINK_HEADER = bytes([0x51, 0x73, 0x70, 0x74, 0x31, 0x57, 0x6D, 0x4A, 0x4F, 0x4C])
        
        # 端口配置
        self.ports = {
            50000: "ANNOUNCE",
            50001: "BEAT", 
            50002: "STATUS"
        }
        
        # WebSocket配置
        self.websocket_port = websocket_port
        self.connected_clients = set()
        
        # 数据存储
        self.devices = {}
        self.current_status = {}
        
        # UDP套接字
        self.sockets = []
        self.running = False
        
        # 消息队列
        self.message_queue = asyncio.Queue()
        
        # 调试模式 - 显示原始数据
        self.debug_mode = True
        self.packet_count = {50000: 0, 50001: 0, 50002: 0}
        
    def create_udp_socket(self, port):
        """创建UDP套接字"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', port))
            sock.settimeout(1.0)
            self.sockets.append(sock)
            logger.info(f"UDP socket bound to port {port}")
            return sock
        except Exception as e:
            logger.error(f"Failed to create socket on port {port}: {e}")
            return None
    
    def parse_announce_packet(self, data, addr):
        """解析设备公告包"""
        try:
            if len(data) < 50 or data[:10] != self.PROLINK_HEADER:
                return None
                
            device_info = {
                'type': 'device',
                'device': {
                    'ip': addr[0],
                    'type': 'Unknown',
                    'id': 0,
                    'name': 'Unknown Device'
                }
            }
            
            # 解析设备ID
            if len(data) > 36:
                device_id = data[36]
                if device_id > 0:
                    device_info['device']['id'] = device_id
                    
            # 解析设备类型
            if len(data) > 34:
                device_type = data[34]
                type_names = {
                    1: "CDJ",
                    2: "Mixer",
                    3: "Rekordbox"
                }
                device_info['device']['type'] = type_names.get(device_type, f'Type{device_type}')
                
                # 设置设备名称
                if device_type == 1:
                    device_info['device']['name'] = f"CDJ-2000NXS2"
                elif device_type == 2:
                    device_info['device']['name'] = "DJM-900NXS2"
                elif device_type == 3:
                    device_info['device']['name'] = "Rekordbox"
                    
            return device_info
            
        except Exception as e:
            logger.error(f"Failed to parse ANNOUNCE packet: {e}")
            return None
    
    def parse_beat_packet(self, data):
        """解析节拍包"""
        try:
            if len(data) < 100 or data[:10] != self.PROLINK_HEADER:
                return None
                
            beat_info = {
                'type': 'beat',
                'beat': {}
            }
            
            # 解析设备ID
            if len(data) > 33:
                beat_info['beat']['deviceId'] = data[33]
                
            # 解析节拍位置 (1-4)
            if len(data) > 88:
                beat_count = struct.unpack('>I', data[84:88])[0]
                beat_info['beat']['position'] = (beat_count % 4) + 1
                
            # 解析BPM
            if len(data) >= 94:
                bpm_raw = struct.unpack('>H', data[92:94])[0]
                if bpm_raw > 0:
                    beat_info['beat']['bpm'] = bpm_raw / 100.0
                    
            return beat_info
            
        except Exception as e:
            logger.error(f"Failed to parse BEAT packet: {e}")
            return None
    
    def parse_status_packet(self, data):
        """解析状态包"""
        try:
            if len(data) < 170 or data[:10] != self.PROLINK_HEADER:
                return None
                
            status_info = {
                'type': 'status',
                'status': {}
            }
            
            # 设备ID
            if len(data) > 33:
                device_id = data[33]
                status_info['status']['deviceId'] = device_id
                
            # 音轨ID
            if len(data) >= 50:
                track_id = struct.unpack('>I', data[46:50])[0]
                status_info['status']['trackId'] = track_id
                
            # 播放状态
            if len(data) > 123:
                play_state = data[123]
                status_info['status']['playState'] = self.decode_play_state(play_state)
                status_info['status']['isPlaying'] = bool(play_state & 0x40)
                status_info['status']['isMaster'] = bool(play_state & 0x20)
                status_info['status']['isSync'] = bool(play_state & 0x10)
                status_info['status']['isOnAir'] = bool(play_state & 0x08)
                
            # BPM
            if len(data) >= 94:
                bpm_raw = struct.unpack('>H', data[92:94])[0]
                if bpm_raw > 0:
                    status_info['status']['bpm'] = bpm_raw / 100.0
                    
            # Pitch
            if len(data) >= 136:
                pitch_raw = struct.unpack('>i', data[132:136])[0]
                status_info['status']['pitch'] = pitch_raw / 1048576.0 * 100
                
            # 播放位置
            if len(data) >= 168:
                position_ms = struct.unpack('>I', data[164:168])[0]
                if position_ms > 0:
                    minutes = position_ms // 60000
                    seconds = (position_ms % 60000) / 1000
                    status_info['status']['time'] = f"{minutes:02.0f}:{seconds:05.2f}"
                    
            # 添加音轨信息
            if track_id > 0:
                status_info['status']['track'] = {
                    'id': track_id,
                    'title': f'Track {track_id:08X}'
                }
                
            return status_info
            
        except Exception as e:
            logger.error(f"Failed to parse STATUS packet: {e}")
            return None
    
    def decode_play_state(self, state_byte):
        """解码播放状态字节"""
        if state_byte & 0x40:
            return 3  # Playing
        elif state_byte & 0x02:
            return 2  # Loading
        elif state_byte == 0:
            return 0  # Empty
        else:
            return 5  # Paused
    
    def print_raw_data(self, port, data, addr):
        """打印原始数据用于调试"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.packet_count[port] += 1
        
        # 格式化十六进制数据
        hex_data = ' '.join(f'{b:02X}' for b in data[:50])  # 显示前50字节
        if len(data) > 50:
            hex_data += f' ... (total: {len(data)} bytes)'
        
        # 检查是否是ProDJLink包
        is_prolink = data[:10] == self.PROLINK_HEADER if len(data) >= 10 else False
        
        print(f"\n[{timestamp}] Port {port} ({self.ports[port]}) - Packet #{self.packet_count[port]}")
        print(f"  From: {addr[0]}:{addr[1]}")
        print(f"  Size: {len(data)} bytes")
        print(f"  ProDJLink: {'YES' if is_prolink else 'NO'}")
        print(f"  Raw (hex): {hex_data}")
        
        # 如果是ProDJLink包，显示关键字段
        if is_prolink and len(data) > 36:
            print(f"  Device ID (offset 36): {data[36] if len(data) > 36 else 'N/A'}")
            print(f"  Device Type (offset 34): {data[34] if len(data) > 34 else 'N/A'}")
            
            if port == 50002 and len(data) >= 50:  # STATUS包
                track_id = struct.unpack('>I', data[46:50])[0] if len(data) >= 50 else 0
                print(f"  Track ID (offset 46-50): 0x{track_id:08X}")
                
                if len(data) > 123:
                    play_state = data[123]
                    print(f"  Play State (offset 123): 0x{play_state:02X}")
                    print(f"    - Playing: {'YES' if play_state & 0x40 else 'NO'}")
                    print(f"    - OnAir: {'YES' if play_state & 0x08 else 'NO'}")
        
        print("-" * 60)
    
    def listen_udp_port(self, port):
        """监听UDP端口的线程函数"""
        sock = self.create_udp_socket(port)
        if not sock:
            return
            
        port_name = self.ports[port]
        logger.info(f"Started listening on UDP port {port} ({port_name})")
        
        while self.running:
            try:
                data, addr = sock.recvfrom(4096)
                
                # 调试模式：打印原始数据
                if self.debug_mode:
                    self.print_raw_data(port, data, addr)
                
                # 解析数据包
                message = None
                if port == 50000:  # ANNOUNCE
                    message = self.parse_announce_packet(data, addr)
                    if message:
                        device_id = message['device']['id']
                        self.devices[device_id] = message['device']
                        
                elif port == 50001:  # BEAT
                    message = self.parse_beat_packet(data)
                    
                elif port == 50002:  # STATUS
                    message = self.parse_status_packet(data)
                    if message and 'deviceId' in message['status']:
                        device_id = message['status']['deviceId']
                        self.current_status[device_id] = message['status']
                
                # 将消息放入队列
                if message:
                    asyncio.run_coroutine_threadsafe(
                        self.message_queue.put(message),
                        self.loop
                    )
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"UDP port {port} listen error: {e}")
                break
                
        sock.close()
        logger.info(f"Stopped listening on UDP port {port}")
    
    async def websocket_handler(self, websocket, path):
        """处理WebSocket连接"""
        self.connected_clients.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"WebSocket client connected: {client_addr}")
        
        try:
            # 发送当前设备列表
            for device in self.devices.values():
                await websocket.send(json.dumps({
                    'type': 'device',
                    'device': device
                }))
                
            # 发送当前状态
            for status in self.current_status.values():
                await websocket.send(json.dumps({
                    'type': 'status',
                    'status': status
                }))
                
            # 保持连接
            await websocket.wait_closed()
            
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connected_clients.remove(websocket)
            logger.info(f"WebSocket client disconnected: {client_addr}")
    
    async def broadcast_messages(self):
        """广播消息到所有WebSocket客户端"""
        while self.running:
            try:
                # 获取消息
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                
                # 广播到所有客户端
                if self.connected_clients:
                    message_json = json.dumps(message)
                    disconnected = set()
                    
                    for client in self.connected_clients:
                        try:
                            await client.send(message_json)
                        except websockets.exceptions.ConnectionClosed:
                            disconnected.add(client)
                            
                    # 移除断开的客户端
                    self.connected_clients -= disconnected
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Broadcast message error: {e}")
    
    async def start_websocket_server(self):
        """启动WebSocket服务器"""
        logger.info(f"Starting WebSocket server on port: {self.websocket_port}")
        
        # 保存事件循环引用
        self.loop = asyncio.get_event_loop()
        
        # 启动UDP监听线程
        self.running = True
        for port in self.ports:
            thread = threading.Thread(target=self.listen_udp_port, args=(port,))
            thread.daemon = True
            thread.start()
        
        # 启动消息广播协程
        broadcast_task = asyncio.create_task(self.broadcast_messages())
        
        # 启动WebSocket服务器
        async with websockets.serve(self.websocket_handler, 'localhost', self.websocket_port):
            logger.info(f"WebSocket server running: ws://localhost:{self.websocket_port}")
            
            try:
                await asyncio.Future()  # 永久运行
            except KeyboardInterrupt:
                logger.info("Received stop signal")
            finally:
                self.running = False
                broadcast_task.cancel()
    
    def run(self):
        """运行服务器"""
        try:
            asyncio.run(self.start_websocket_server())
        except KeyboardInterrupt:
            logger.info("Server stopped")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.running = False
            for sock in self.sockets:
                try:
                    sock.close()
                except:
                    pass

def create_html_file():
    """创建HTML文件并返回路径"""
    # 创建临时HTML文件
    html_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
    html_file.write(HTML_CONTENT)
    html_file.close()
    return html_file.name

def main():
    """主函数"""
    print("=" * 60)
    print("[DJ] ProDJLink Web Monitor - All-in-One")
    print("=" * 60)
    print()
    print("[INFO] Single file version - Everything included!")
    print("[DEBUG] Raw packet data will be displayed below")
    print("=" * 60)
    print()
    
    # 检查依赖
    try:
        import websockets
    except ImportError:
        print("[ERROR] websockets library not found")
        print("[INFO] Installing websockets...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
        print("[OK] websockets installed")
        import websockets
    
    # 创建HTML文件
    print("[CREATE] Creating HTML interface...")
    html_path = create_html_file()
    print(f"[OK] HTML file created: {html_path}")
    
    # 打开浏览器
    print("[BROWSER] Opening web interface...")
    time.sleep(1)  # 等待服务器启动
    webbrowser.open(f"file:///{html_path}")
    
    print()
    print("[START] Starting WebSocket server...")
    print("[INFO] Listening on:")
    print("  - WebSocket: ws://localhost:8080")
    print("  - UDP: 50000 (ANNOUNCE)")
    print("  - UDP: 50001 (BEAT)")  
    print("  - UDP: 50002 (STATUS)")
    print()
    print("[READY] Monitor is running!")
    print("[INFO] The web page will auto-connect to the server")
    print()
    print("Press Ctrl+C to stop...")
    print()
    
    # 启动服务器
    server = ProDJLinkWebSocketServer()
    
    try:
        server.run()
    finally:
        # 清理临时文件
        try:
            os.unlink(html_path)
        except:
            pass
        print("[STOP] Monitor stopped")

if __name__ == "__main__":
    main()