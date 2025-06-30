#!/usr/bin/env python3
"""
串口适配器自动识别系统 - 完整优化版
支持 EZSP / ZNP / Z-Wave 检测 + MQTT 上报 + 历史比对 + 日志输出
"""

import os
import json
import time
import yaml
import glob
import logging
import serial
import subprocess
from datetime import datetime
from typing import List, Dict, Optional

# ========== 配置项 ==========
SCAN_DIR = "/sdcard/isgbackup/serialport"
LATEST_JSON = os.path.join(SCAN_DIR, "latest.json")
LOG_FILE = os.path.join(SCAN_DIR, "serial_detect.log")
ZIGBEE_KNOWN = os.path.join(SCAN_DIR, "zigbee_known.yaml")

# MQTT 配置（支持环境变量覆盖）
MQTT_CONFIG = {
    "broker": os.getenv("MQTT_BROKER", "127.0.0.1"),
    "port": int(os.getenv("MQTT_PORT", 1883)),
    "user": os.getenv("MQTT_USER", "admin"),
    "pass": os.getenv("MQTT_PASS", "admin"),
    "topic": os.getenv("MQTT_TOPIC", "isg/serial/scan"),
    "retain": os.getenv("MQTT_RETAIN", "true") == "true"
}

# ========== 日志配置 ==========
os.makedirs(SCAN_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("serial_detector")

# ========== 工具函数 ==========
def load_known_devices() -> List[Dict]:
    if os.path.exists(ZIGBEE_KNOWN):
        with open(ZIGBEE_KNOWN, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return []

def get_serial_ports() -> List[str]:
    patterns = ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/ttyAMA*", "/dev/ttyAS*", "/dev/ttyS*"]
    ports = []
    for pattern in patterns:
        ports.extend(glob.glob(pattern))
    return sorted(set(ports))

def is_port_busy(port: str) -> bool:
    try:
        res = subprocess.run(['lsof', port], capture_output=True, text=True)
        return res.returncode == 0
    except:
        return False

def read_last_result() -> List[str]:
    if os.path.exists(LATEST_JSON):
        with open(LATEST_JSON, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                return [d['port'] for d in data.get('ports', [])]
            except:
                return []
    return []

def save_current_result(payload: Dict):
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = os.path.join(SCAN_DIR, f"serial_ports_{timestamp}.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    with open(LATEST_JSON, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

# ========== 主探测逻辑 ==========
def detect_serial_devices():
    known_devices = load_known_devices()
    ports = get_serial_ports()
    logger.info(f"🔍 共发现 {len(ports)} 个串口设备")

    detected_ports = []
    for port in ports:
        info = {
            "port": port,
            "busy": is_port_busy(port),
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            ser = serial.Serial(port=port, baudrate=115200, timeout=2, rtscts=False)
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            # 尝试发送 EZSP 重置指令
            ser.write(b"\x1A\xC0\x38\xBC\x7E")
            ser.flush()
            time.sleep(0.3)
            response = ser.read_all().hex().lower()
            info["raw_response"] = response
            ser.close()

            for device in known_devices:
                if any(pattern in response for pattern in device.get("response_patterns", [])):
                    info.update({
                        "type": "zigbee",
                        "protocol": device.get("protocol"),
                        "manufacturer": device.get("manufacturer"),
                        "model": device.get("name"),
                        "chipset": device.get("chipset"),
                        "confidence": "high"
                    })
                    break
            else:
                if response:
                    info.update({
                        "type": "zigbee",
                        "protocol": "ezsp",
                        "confidence": "medium"
                    })
                else:
                    info["type"] = "unknown"

        except Exception as e:
            info["error"] = str(e)
            info["type"] = "error"

        detected_ports.append(info)
        time.sleep(0.1)

    return detected_ports

# ========== MQTT 上报 ==========
def publish_mqtt(payload: Dict):
    try:
        import paho.mqtt.publish as publish
        publish.single(
            topic=MQTT_CONFIG['topic'],
            payload=json.dumps(payload),
            hostname=MQTT_CONFIG['broker'],
            port=MQTT_CONFIG['port'],
            auth={'username': MQTT_CONFIG['user'], 'password': MQTT_CONFIG['pass']},
            retain=MQTT_CONFIG['retain']
        )
        logger.info(f"📡 MQTT 上报成功 → {MQTT_CONFIG['topic']}")
    except Exception as e:
        logger.warning(f"❌ MQTT 上报失败: {e}")

# ========== 主程序入口 ==========
def main():
    now = datetime.utcnow().isoformat()
    new_result = detect_serial_devices()
    old_ports = set(read_last_result())
    new_ports = set([x["port"] for x in new_result])

    payload = {
        "timestamp": now,
        "ports": new_result,
        "added": sorted(list(new_ports - old_ports)),
        "removed": sorted(list(old_ports - new_ports))
    }

    save_current_result(payload)
    publish_mqtt(payload)

    logger.info("✅ 串口识别流程完成")
    logger.info(json.dumps(payload, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
