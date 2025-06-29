#!/usr/bin/env python3
"""detect_serial_adapters.py — 全面串口探测、MQTT 上报与配置联动

功能一览
--------
* 扫描所有可用串口并收集硬件信息（VID, PID, Serial, Product, Manufacturer）。
* 判断适配器类型：
  - **Z‑Wave**：通过发送 GetVersion 帧 (0x01 0x03 0x00 0x07 0xFB)。
  - **Zigbee**：根据 VID/PID & 描述串匹配已知列表（ZHA & Zigbee2MQTT 支持芯片）。
* 将结果保存为 JSON：`/sdcard/isgbackup/serialport/serial_ports_<timestamp>.json`，并更新 `latest.json` 软链。
* 比较与上次扫描差异 → 新增 / 移除设备列表。
* 通过 MQTT 发布扫描结果（主题可配置，缺省 `isg/serial/scan`）。
* 自动调用（或提示）现有脚本，更新：
    * Z‑Wave: `generate_settings_json.py` (传入 `Z_SERIAL`)
    * Zigbee2MQTT: `generate_config_yaml.py` (传入 `Z2M_SERIAL` & `Z2M_BAUDRATE`)

依赖安装
--------
```bash
pip install pyserial paho-mqtt
```

CLI 用法示例
------------
```bash
python /sdcard/isgbackup/zwave/detect_serial_adapters.py \
    --mqtt-broker 127.0.0.1 --retain --run-generators
```
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import paho.mqtt.client as mqtt
import serial
import serial.tools.list_ports as list_ports

# -----------------------------------------------------------
# 常量 & 已知适配器表
# -----------------------------------------------------------

# Zigbee 适配器 (VID, PID) 列表（可自行补充）
ZIGBEE_KNOWN: List[Tuple[int, int, str]] = [
    (0x10C4, 0xEA60, "SiliconLabs CP210x"),  # 多数 EZSP / Sonoff ZBDongle‐E
    (0x10C4, 0x8A2A, "Sonoff ZBDongle‐E"),
    (0x0403, 0x6015, "FTDI CC2531/CC2652"),
    (0x1A86, 0x55D4, "CH34x Zigbee"),
]

SERIAL_DIR = Path("/sdcard/isgbackup/serialport")
SERIAL_DIR.mkdir(parents=True, exist_ok=True)
LAST_JSON = SERIAL_DIR / "latest.json"

# -----------------------------------------------------------
# Helper: Probe Z‑Wave dongle (blocking ≤1s)
# -----------------------------------------------------------

_ZW_GET_VERSION = bytes([0x01, 0x03, 0x00, 0x07, 0xFB])

def is_zwave(port: str, baud: int = 115200) -> bool:
    """Return True if *port* responds to Z‑Wave GetVersion."""
    try:
        with serial.Serial(port, baudrate=baud, timeout=0.7) as s:
            s.reset_input_buffer()
            s.write(_ZW_GET_VERSION)
            s.flush()
            time.sleep(0.1)
            resp = s.read(128)
            return bool(resp and resp.startswith(b"\x01") and b"Z-Wave" in resp)
    except Exception:
        return False

# -----------------------------------------------------------
# Helper: Zigbee identification
# -----------------------------------------------------------

def is_zigbee(vid: Optional[int], pid: Optional[int], desc: str) -> bool:
    if vid is None or pid is None:
        return False
    for v, p, _name in ZIGBEE_KNOWN:
        if vid == v and pid == p:
            return True
    # Fallback heuristic
    desc_l = desc.lower()
    if any(k in desc_l for k in ("zigbee", "cc253", "cc265", "ezsp")):
        return True
    return False

# -----------------------------------------------------------
# Main scan routine
# -----------------------------------------------------------

def scan_serial_ports() -> List[Dict]:
    result: List[Dict] = []
    for port in list_ports.comports():
        info = {
            "device": port.device,
            "hwid": port.hwid,
            "vid": port.vid,
            "pid": port.pid,
            "serial_number": port.serial_number,
            "manufacturer": port.manufacturer,
            "product": port.product,
            "description": port.description,
            "is_zigbee": False,
            "is_zwave": False,
        }
        info["is_zigbee"] = is_zigbee(port.vid, port.pid, port.description or "")
        if not info["is_zigbee"]:
            # 避免对 Zigbee 端口发 Z‑Wave 帧
            info["is_zwave"] = is_zwave(port.device)
        else:
            info["is_zwave"] = False
        result.append(info)
    return result

# -----------------------------------------------------------
# JSON 读写 & Diff
# -----------------------------------------------------------

def load_last() -> List[Dict]:
    if LAST_JSON.exists():
        try:
            return json.loads(LAST_JSON.read_text())
        except Exception:
            return []
    return []

def save_current(data: List[Dict]) -> Path:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    outfile = SERIAL_DIR / f"serial_ports_{ts}.json"
    outfile.write_text(json.dumps(data, indent=2))
    # Update latest symlink / copy
    try:
        if LAST_JSON.exists() or LAST_JSON.is_symlink():
            LAST_JSON.unlink()
        LAST_JSON.symlink_to(outfile.name)
    except Exception:
        # On Android FAT sdcard (no symlink support) → write copy
        LAST_JSON.write_text(json.dumps(data, indent=2))
    return outfile


def diff_ports(old: List[Dict], new: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    old_set = {d["device"] for d in old}
    new_set = {d["device"] for d in new}
    added = [d for d in new if d["device"] not in old_set]
    removed = [d for d in old if d["device"] not in new_set]
    return added, removed

# -----------------------------------------------------------
# MQTT publish helper
# -----------------------------------------------------------

def publish_mqtt(cfg: argparse.Namespace, payload: dict):
    cli = mqtt.Client()
    if cfg.mqtt_user:
        cli.username_pw_set(cfg.mqtt_user, cfg.mqtt_pass or "")
    try:
        cli.connect(cfg.mqtt_broker, cfg.mqtt_port, 60)
        cli.publish(cfg.topic, json.dumps(payload), qos=1, retain=cfg.retain)
        cli.disconnect()
    except Exception as exc:
        print("[MQTT] publish failed:", exc)

# -----------------------------------------------------------
# Generator call wrappers
# -----------------------------------------------------------

def call_generators(cfg: argparse.Namespace, ports: List[Dict]):
    """Invoke existing generator scripts with env vars."""
    zw_port = next((d for d in ports if d["is_zwave"]), None)
    zb_port = next((d for d in ports if d["is_zigbee"]), None)
    env = os.environ.copy()
    if zw_port:
        env["Z_SERIAL"] = zw_port["device"]
        print("[GEN] Z‑Wave serial =", zw_port["device"])
    if zb_port:
        env["Z2M_SERIAL"] = zb_port["device"]
        env.setdefault("Z2M_BAUDRATE", "115200")
        print("[GEN] Zigbee serial =", zb_port["device"])

    if cfg.run_generators and zw_port:
        os.system("proot-distro login ubuntu -- python3 /sdcard/isgbackup/zwave/generate_settings_json.py")
    if cfg.run_generators and zb_port:
        os.system("proot-distro login ubuntu -- python3 /sdcard/isgbackup/z2m/generate_config_yaml.py")

# -----------------------------------------------------------
# CLI Entry
# -----------------------------------------------------------

def main():
    p = argparse.ArgumentParser("Detect serial adapters (Zigbee / Z‑Wave) and publish via MQTT")
    p.add_argument("--mqtt-broker", required=True)
    p.add_argument("--mqtt-port", type=int, default=1883)
    p.add_argument("--mqtt-user")
    p.add_argument("--mqtt-pass")
    p.add_argument("--topic", default="isg/serial/scan")
    p.add_argument("--retain", action="store_true")
    p.add_argument("--interval", type=int, help="repeat every N seconds")
    p.add_argument("--run-generators", action="store_true", help="after detection call zwave & z2m generators")
    args = p.parse_args()

    last_data = load_last()

    def once():
        nonlocal last_data
        cur_data = scan_serial_ports()
        added, removed = diff_ports(last_data, cur_data)
        save_current(cur_data)

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ports": cur_data,
            "added": added,
            "removed": removed,
        }
        publish_mqtt(args, payload)
        call_generators(args, cur_data)
        last_data = cur_data

    once()
    if args.interval:
        try:
            while True:
                time.sleep(args.interval)
                once()
        except KeyboardInterrupt:
            print("Interrupted.")

if __name__ == "__main__":
    main()
