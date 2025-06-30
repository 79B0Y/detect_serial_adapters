#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import serial
import serial.tools.list_ports
import logging
import yaml
import glob
import datetime
from pathlib import Path
from paho.mqtt import client as mqtt_client

# ========== 配置区域 ==========
zigbee_db_path = "/sdcard/isgbackup/serialport/zigbee_known.yaml"
output_dir = Path("/sdcard/isgbackup/serialport")
log_file = output_dir / "serial_detect.log"
mqtt_config = {
    "broker": os.getenv("MQTT_BROKER", "127.0.0.1"),
    "port": int(os.getenv("MQTT_PORT", 1883)),
    "user": os.getenv("MQTT_USER", "admin"),
    "pass": os.getenv("MQTT_PASS", "admin"),
    "topic": os.getenv("MQTT_TOPIC", "isg/serial/scan"),
    "retain": True
}

common_baudrates = [115200, 57600, 38400, 9600, 230400]
zwave_version_cmd = bytes.fromhex("01030015E9")

# ========== 日志设置 ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ========== MQTT 客户端 ==========
def publish_mqtt(payload):
    try:
        client = mqtt_client.Client()
        client.username_pw_set(mqtt_config['user'], mqtt_config['pass'])
        client.connect(mqtt_config['broker'], mqtt_config['port'], 60)
        client.loop_start()
        client.publish(mqtt_config['topic'], json.dumps(payload), retain=mqtt_config['retain'])
        client.loop_stop()
        logging.info(f"📡 MQTT 上报成功 → {mqtt_config['topic']}")
    except Exception as e:
        logging.error(f"MQTT 发送失败: {e}")

# ========== Zigbee 识别逻辑 ==========
def load_zigbee_db():
    if Path(zigbee_db_path).exists():
        with open(zigbee_db_path, "r") as f:
            return yaml.safe_load(f)
    return []

def check_known_zigbee(vid, pid):
    db = load_zigbee_db()
    for entry in db:
        if vid == entry.get("vid") and pid == entry.get("pid"):
            return entry
    return None

# ========== 设备探測逻辑 ==========
def list_serial_ports():
    patterns = ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/ttyAS*", "/dev/ttyS*", "/dev/ttyAMA*"]
    all_ports = []
    for pattern in patterns:
        all_ports.extend(glob.glob(pattern))
    return sorted(set(all_ports))

def detect_device(port):
    result = {
        "port": port,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "busy": False
    }

    publish_mqtt({"status": "detecting", "port": port, "timestamp": result["timestamp"]})
    logging.info(f"🔎 正在探測 {port}")

    try:
        info = next((p for p in serial.tools.list_ports.comports() if p.device == port), None)
        vid = int(info.vid) if info and info.vid else None
        pid = int(info.pid) if info and info.pid else None

        # Step 1: Z-Wave 探測
        for baudrate in common_baudrates:
            try:
                with serial.Serial(port=port, baudrate=baudrate, timeout=1) as ser:
                    ser.reset_input_buffer()
                    ser.write(zwave_version_cmd)
                    time.sleep(0.5)
                    raw = ser.read(64).hex()
                    if raw.startswith("01"):
                        result.update({
                            "type": "zwave",
                            "protocol": "zwave",
                            "raw_response": raw,
                            "baudrate": baudrate,
                            "confidence": "medium"
                        })
                        publish_mqtt({"status": "zwave_detected", **result})
                        return result
            except Exception:
                continue

        # Step 2: 基于 VID/PID 识别 Zigbee
        if vid and pid:
            zigbee = check_known_zigbee(vid, pid)
            if zigbee:
                result.update({
                    "type": "zigbee",
                    "protocol": zigbee.get("type", "unknown"),
                    "baudrate": zigbee.get("baudrate", 115200),
                    "confidence": "high",
                })
                publish_mqtt({"status": "zigbee_known", **result})
                return result

        # Step 3: 探測 EZSP 协议
        for baudrate in common_baudrates:
            try:
                with serial.Serial(port=port, baudrate=baudrate, timeout=1) as ser:
                    ser.reset_input_buffer()
                    ser.write(b"\x1A\xC0\x38\xBC\x7E")  # EZSP reset
                    time.sleep(0.5)
                    raw = ser.read(64).hex()
                    if raw.startswith("11"):
                        result.update({
                            "type": "zigbee",
                            "protocol": "ezsp",
                            "raw_response": raw,
                            "baudrate": baudrate,
                            "confidence": "medium"
                        })
                        publish_mqtt({"status": "zigbee_ezsp", **result})
                        return result
            except Exception:
                continue

        result.update({"type": "unknown"})
        return result

    except serial.SerialException as e:
        result.update({"busy": True, "type": "error", "error": str(e)})
        publish_mqtt({"status": "occupied", **result})
        return result

# ========== 主程序 ==========
def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    publish_mqtt({"status": "running", "timestamp": now})
    ports = list_serial_ports()
    logging.info(f"🔍 共发现 {len(ports)} 个串口设备")
    results = [detect_device(p) for p in ports]

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    output_file = output_dir / f"serial_ports_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump({"timestamp": now, "ports": results}, f, indent=2)

    latest_path = output_dir / "latest.json"
    with open(latest_path, "w") as f:
        json.dump({"timestamp": now, "ports": results}, f, indent=2)

    files = sorted(output_dir.glob("serial_ports_*.json"), key=os.path.getmtime, reverse=True)
    for f in files[3:]:
        f.unlink()

    publish_mqtt({"timestamp": now, "ports": results, "added": [], "removed": []})
    logging.info("✅ 串口识别流程完成")

if __name__ == "__main__":
    main()
