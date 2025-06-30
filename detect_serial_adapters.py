#!/usr/bin/env python3
"""
串口适配器自动识别系统 - 完整集成版本
✅ 自动识别 Zigbee & Z-Wave 波特率
✅ MQTT 流式状态上报（探测开始 / 协议识别 / 占用）
✅ 本地记录最新扫描结果 + 保留最近 3 次
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
ZWAVE_BAUDRATES = [115200, 57600, 38400, 9600, 230400]

def try_baudrate(port, baudrate):
    try:
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.5)
        ser.write(b"\x1A\xC0\x38\xBC\x7E")
        time.sleep(0.2)
        response = ser.read_all().hex().lower()
        ser.close()
        if response.startswith("11"):
            return True, response
    except:
        pass
    return False, ""

def try_zwave_baudrate(port, baudrate):
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        ser.write(b'\x01\x03\x00\x15\xE9')
        time.sleep(0.3)
        resp = ser.read_all()
        ser.close()
        if resp and resp[0] == 0x01 and resp[1] == 0x10:
            return True, resp.hex()
    except:
        pass
    return False, ""

def publish_mqtt_status(port, phase, info=None):
    data = {
        "status": phase,
        "port": port,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if info:
        data.update(info)
    try:
        publish.single(
            topic=MQTT_CONFIG['topic'],
            payload=json.dumps(data),
            hostname=MQTT_CONFIG['broker'],
            port=MQTT_CONFIG['port'],
            auth={"username": MQTT_CONFIG['user'], "password": MQTT_CONFIG['pass']},
            retain=False
        )
        logger.debug(f"📡 状态上报: {data}")
    except Exception as e:
        logger.warning(f"⚠️ MQTT 状态上报失败: {e}")

def detect_zigbee_device(port):
    logger.info(f"🚀 开始 Zigbee 探测: {port}")
    publish_mqtt_status(port, "zigbee_detecting")
    for baud in CANDIDATE_BAUDRATES:
        logger.info(f"🔍 尝试 Zigbee 波特率 {baud}...")
        success, response = try_baudrate(port, baud)
        if success:
            logger.info(f"✅ Zigbee 响应成功 @ {baud}, 响应: {response[:32]}...")
            result = {
                "port": port,
                "type": "zigbee",
                "protocol": "ezsp",
                "baudrate": baud,
                "raw_response": response,
                "confidence": "medium"
            }
            publish_mqtt_status(port, "zigbee_detected", result)
            return result
    logger.info(f"❌ 未发现 Zigbee 响应: {port}")
    return {"port": port, "type": "unknown", "confidence": "low"}

def detect_zwave_device(port):
    logger.info(f"🔄 开始 Z-Wave 探测: {port}")
    publish_mqtt_status(port, "zwave_detecting")
    for baud in ZWAVE_BAUDRATES:
        logger.info(f"🔍 尝试 Z-Wave 波特率 {baud}...")
        ok, response = try_zwave_baudrate(port, baud)
        if ok:
            logger.info(f"✅ Z-Wave 响应成功 @ {baud}, 响应: {response[:32]}...")
            result = {
                "port": port,
                "type": "zwave",
                "protocol": "zwave",
                "baudrate": baud,
                "confidence": "high",
                "raw_response": response
            }
            publish_mqtt_status(port, "zwave_detected", result)
            return result
    logger.info(f"❌ 未检测到 Z-Wave 响应: {port}")
    return None

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
        logger.info("📡 MQTT 最终结果上报成功")
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
    files = sorted(glob.glob(os.path.join(SCAN_DIR, "serial_ports_*.json")), key=os.path.getmtime, reverse=True)
    for f in files[3:]:
        try:
            os.remove(f)
            logger.info(f"🧹 删除旧文件: {f}")
        except Exception as e:
            logger.warning(f"⚠️ 删除失败: {e}")

def main():
    now = datetime.now(timezone.utc).isoformat()
    publish_mqtt({"status": "running", "timestamp": now})
    ports = discover_ports()
    logger.info(f"🔧 发现 {len(ports)} 个串口设备: {ports}")

    old_ports = set(read_previous_ports())
    detected = []

    for port in ports:
        publish_mqtt_status(port, "detecting")
        if is_port_busy(port):
            logger.info(f"⛔ 串口 {port} 被占用，跳过检测")
            result = {"port": port, "type": "occupied", "confidence": "none"}
            publish_mqtt_status(port, "occupied")
        else:
            result = detect_zigbee_device(port)
            if result["type"] == "unknown":
                zwave = detect_zwave_device(port)
                if zwave:
                    result = zwave
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
    logger.info("🟢 串口识别完成")
    for p in detected:
        logger.info(json.dumps(p, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
