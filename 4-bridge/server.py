#!/usr/bin/env python3
"""
MCP Server — 小猫爪 Venus BLE 广播控制

通过子进程运行 BLE 广播（ble_worker.py），MCP server 与子进程通过 stdin/stdout 通信。

启动：
  uv run server.py
然后开 Cloudflare Tunnel：
  cloudflared tunnel --url http://localhost:8888 --protocol http2
将 Tunnel URL 填入 claude.ai → Settings → Connectors → Add Custom Connector
"""

import subprocess
import threading
import time
import logging
import os
import sys
import json
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

# ── BLE Worker 进程管理 ────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

class VenusBLEWorker:
    """管理 ble_worker.py 子进程，通过 stdin/stdout 发送振动命令。"""

    def __init__(self):
        self._proc = None
        self._lock = threading.Lock()
        self._ready = False
        self._start()

    def _start(self):
        worker_path = os.path.join(SCRIPT_DIR, 'ble_worker.py')
        self._proc = subprocess.Popen(
            ['uv', 'run', 'python3', worker_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=SCRIPT_DIR,
        )
        # 等待 worker 初始化完成
        line = self._proc.stdout.readline().strip()
        if line == "READY":
            self._ready = True
            print("[BLE Worker] 就绪", flush=True)
        else:
            err = self._proc.stderr.read()
            print(f"[BLE Worker] 启动失败: {line} {err}", flush=True)

    def send(self, intensity: int) -> str:
        if not self._ready or self._proc.poll() is not None:
            raise RuntimeError("BLE worker 未就绪")
        with self._lock:
            self._proc.stdin.write(f"{intensity}\n")
            self._proc.stdin.flush()
            response = self._proc.stdout.readline().strip()
            if response == "OK":
                return "OK"
            raise RuntimeError(f"Worker 返回: {response}")

    @property
    def is_ready(self):
        return self._ready and self._proc and self._proc.poll() is None


_worker: VenusBLEWorker | None = None

def get_worker() -> VenusBLEWorker:
    global _worker
    if _worker is None or not _worker.is_ready:
        _worker = VenusBLEWorker()
    return _worker


# ── 状态 ───────────────────────────────────────────────────────────────────────

_current_intensity = 0

# ── MCP Server ─────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
mcp = FastMCP("venus", host="0.0.0.0", port=8888)


@mcp.tool()
def vibrate(intensity: int) -> str:
    """
    控制小猫爪振动。

    Args:
        intensity: 振动强度，0-100。0 表示停止。
    """
    global _current_intensity

    if intensity < 0 or intensity > 100:
        return "❌ 强度范围 0-100"

    try:
        get_worker().send(intensity)
        _current_intensity = intensity
        if intensity == 0:
            return "✅ 已停止"
        return f"✅ 振动强度 {intensity}%"
    except Exception as e:
        return f"❌ 失败: {e}"


@mcp.tool()
def stop() -> str:
    """立即停止振动。"""
    return vibrate(0)


@mcp.tool()
def status() -> str:
    """查询当前状态。"""
    w = _worker
    ready = w is not None and w.is_ready
    return (
        f"设备: 小猫爪 Venus\n"
        f"BLE Worker: {'✅ 就绪' if ready else '❌ 未就绪'}\n"
        f"振动: {_current_intensity}%"
    )


@mcp.tool()
def pattern(name: str) -> str:
    """
    播放预设振动模式。

    Args:
        name: 模式名称。可选: pulse（脉冲）、wave（波浪）、tease（挑逗）
    """
    try:
        w = get_worker()

        if name == "pulse":
            for _ in range(5):
                for i in [80, 0, 80, 0]:
                    w.send(i)
        elif name == "wave":
            for _ in range(2):
                for i in range(20, 101, 10):
                    w.send(i)
                for i in range(100, 19, -10):
                    w.send(i)
        elif name == "tease":
            for lvl, reps in [(30, 2), (0, 1), (70, 2), (0, 1), (100, 3), (0, 1)]:
                for _ in range(reps):
                    w.send(lvl)
        else:
            return f"❌ 未知模式: {name}。可选: pulse、wave、tease"

        w.send(0)
        global _current_intensity
        _current_intensity = 0
        return f"✅ 模式 '{name}' 播放完毕"
    except Exception as e:
        return f"❌ 失败: {e}"


# ── REST API (for OpenClaw / curl access) ──────────────────────────────────────

@mcp.custom_route("/vibrate", methods=["POST"])
async def rest_vibrate(request: Request) -> JSONResponse:
    try:
        body = await request.json()
        intensity = int(body.get("intensity", 0))
    except Exception:
        return JSONResponse({"error": "invalid body, expected {\"intensity\": 0-100}"}, status_code=400)
    result = vibrate(intensity)
    return JSONResponse({"result": result})


@mcp.custom_route("/stop", methods=["POST"])
async def rest_stop(request: Request) -> JSONResponse:
    result = stop()
    return JSONResponse({"result": result})


@mcp.custom_route("/status", methods=["GET"])
async def rest_status(request: Request) -> JSONResponse:
    result = status()
    return JSONResponse({"result": result})


if __name__ == "__main__":
    print("初始化 BLE worker（约5秒）...")
    get_worker()
    if not _worker.is_ready:
        print("❌ BLE worker 启动失败，请检查蓝牙权限")
        sys.exit(1)
    print("就绪，启动 MCP server (port 8888)...")
    mcp.run(transport="streamable-http")
