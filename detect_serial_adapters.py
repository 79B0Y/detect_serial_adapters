#!/usr/bin/env python3
"""
串口适配器自动识别系统 - 增强版
✅ 自动识别 Zigbee 波特率
✅ 每个串口中文日志输出
✅ MQTT 先上报 running 状态
✅ MQTT 上报中包含最终波特率
"""

import os
import json
import time
import glob
import serial
import logging
import subprocess
from datetime import datetime, timezone
import paho.mqtt.publish as publish

SCAN_DIR = "/sdcard/isgbackup/serialport"
LATEST_JSON = os.path.join(SCAN_DIR, "latest.json")
LOG_FILE = os.path.join(SCAN_DIR, "serial_detect.log")

# MQTT 设置（可用环境变量覆盖）
MQTT_CONFIG = {
    "broker": os.getenv("MQTT_BROKER", "127.0.0.1"),
    "port": int(os.getenv("MQTT_PORT", 1883)),
    "user": os.getenv("MQTT_USER", "admin"),
    "pass": os.getenv("MQTT_PASS", "admin"),
    "topic": os.getenv("MQTT_TOPIC", "isg/serial/scan"),
    "retain": os.getenv("MQTT_RETAIN", "true") == "true"
}

os.makedirs(SCAN_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("serial_detect")

CANDIDATE_BAUDRATES = [115200, 57600, 38400, 9600, 230400, 250000]


def try_baudrate(port, baudrate):
    try:
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.5)
        ser.write(b"\x1A\xC0\x38\xBC\x7E")
        time.sleep(0.2)
        response = ser.read_all().hex().lower()
        ser.close()
        if response.startswith("11"):
            return True, response
    except Exception:
        pass
    return False, ""

def detect_zigbee_device(port):
    logger.info(f"🚀 开始探测串口: {port}")
    for baud in CANDIDATE_BAUDRATES:
        logger.info(f"🔍 尝试波特率 {baud}...")
        success, response = try_baudrate(port, baud)
        if success:
            logger.info(f"✅ Zigbee 设备响应成功，波特率为 {baud}, 响应为 {response[:32]}...")
            return {
                "port": port,
                "type": "zigbee",
                "protocol": "ezsp",
                "baudrate": baud,
                "raw_response": response,
                "confidence": "medium"
            }
    logger.info(f"❌ 未发现 Zigbee 响应: {port}")
    return {
        "port": port,
        "type": "unknown",
        "confidence": "low"
    }

def discover_ports():
    patterns = ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/ttyAS*", "/dev/ttyAMA*", "/dev/ttyS*"]
    ports = []
    for p in patterns:
        ports.extend(glob.glob(p))
    return sorted(set(ports))

def is_port_busy(port):
    try:
        result = subprocess.run(['lsof', port], capture_output=True)
        return result.returncode == 0
    except:
        return False

def publish_mqtt(data):
    try:
        publish.single(
            topic=MQTT_CONFIG['topic'],
            payload=json.dumps(data),
            hostname=MQTT_CONFIG['broker'],
            port=MQTT_CONFIG['port'],
            auth={"username": MQTT_CONFIG['user'], "password": MQTT_CONFIG['pass']},
            retain=MQTT_CONFIG['retain']
        )
        logger.info("📡 MQTT 上报成功")
    except Exception as e:
        logger.warning(f"⚠️ MQTT 上报失败: {e}")

def read_previous_ports():
    try:
        with open(LATEST_JSON, "r") as f:
            return [p['port'] for p in json.load(f).get("ports", [])]
    except:
        return []

def save_result(payload):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    path = os.path.join(SCAN_DIR, f"serial_ports_{timestamp}.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    with open(LATEST_JSON, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def main():
    now = datetime.now(timezone.utc).isoformat()

    # 上报 running 状态
    publish_mqtt({"status": "running", "timestamp": now})

    ports = discover_ports()
    logger.info(f"🔧 发现 {len(ports)} 个串口设备: {ports}")

    old_ports = set(read_previous_ports())
    detected = []

    for port in ports:
        if is_port_busy(port):
            logger.info(f"⛔ 串口 {port} 被占用，跳过检测")
            detected.append({"port": port, "type": "occupied", "confidence": "none"})
        else:
            result = detect_zigbee_device(port)
            result["timestamp"] = datetime.now(timezone.utc).isoformat()
            detected.append(result)

    new_ports = set([d["port"] for d in detected])

    payload = {
        "timestamp": now,
        "ports": detected,
        "added": sorted(list(new_ports - old_ports)),
        "removed": sorted(list(old_ports - new_ports))
    }

    save_result(payload)
    publish_mqtt(payload)

    logger.info("🟢 串口识别完成：")
    for p in detected:
        logger.info(json.dumps(p, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
