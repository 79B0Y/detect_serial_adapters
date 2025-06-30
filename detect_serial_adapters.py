#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
串口适配器自动识别系统
适用于 Android Termux + Proot Ubuntu 环境
自动识别 Zigbee / Z-Wave 串口适配器并通过 MQTT 上报
"""

import os
import sys
import json
import yaml
import time
import glob
import argparse
import subprocess
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

import serial
import serial.tools.list_ports
import paho.mqtt.client as mqtt
from colorama import init, Fore, Back, Style

# 初始化颜色输出
init(autoreset=True)

class SerialDetector:
    def __init__(self, config_path: str = "zigbee_known.yaml", 
                 storage_path: str = "/sdcard/isgbackup/serialport/",
                 mqtt_config: Optional[Dict] = None,
                 verbose: bool = False):
        self.config_path = config_path
        self.storage_path = Path(storage_path)
        self.verbose = verbose
        
        # MQTT 默认配置
        self.mqtt_config = mqtt_config or {
            'broker': '127.0.0.1',
            'port': 1883,
            'user': 'admin',
            'pass': 'admin',
            'topic': 'isg/serial/scan',
            'retain': True
        }
        
        # 创建存储目录
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 设置日志
        self.setup_logging()
        
        # 加载已知 Zigbee 设备库
        self.zigbee_known = self.load_zigbee_known()
        
        self.logger.info("🚀 串口适配器检测系统初始化完成")

    def setup_logging(self):
        """设置日志系统"""
        log_file = self.storage_path / "serial_detect.log"
        
        # 创建logger
        self.logger = logging.getLogger('SerialDetector')
        self.logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def load_zigbee_known(self) -> List[Dict]:
        """加载已知 Zigbee 设备库"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    self.logger.info(f"✅ 加载了 {len(data)} 个已知 Zigbee 设备")
                    return data
            else:
                self.logger.warning(f"⚠️ 配置文件不存在: {self.config_path}")
                return []
        except Exception as e:
            self.logger.error(f"❌ 加载 Zigbee 配置失败: {e}")
            return []

    def get_serial_ports(self) -> List[Dict]:
        """获取所有串口设备信息"""
        ports = []
        
        try:
            # 方法1: 使用 pyserial 枚举
            for port in serial.tools.list_ports.comports():
                port_info = {
                    'device': port.device,
                    'name': port.name or '',
                    'description': port.description or '',
                    'hwid': port.hwid or '',
                    'vid': getattr(port, 'vid', None),
                    'pid': getattr(port, 'pid', None),
                    'serial_number': getattr(port, 'serial_number', None),
                    'manufacturer': getattr(port, 'manufacturer', None),
                    'product': getattr(port, 'product', None),
                }
                ports.append(port_info)
                
        except Exception as e:
            self.logger.warning(f"⚠️ pyserial 枚举失败: {e}")
        
        # 方法2: Fallback - 直接扫描 /dev/tty*
        if not ports:
            try:
                # 扩展扫描范围，包含更多串口类型
                tty_patterns = [
                    '/dev/ttyUSB*',   # USB 转串口
                    '/dev/ttyACM*',   # USB CDC ACM 设备
                    '/dev/ttyS*',     # 标准串口
                    '/dev/ttyAS*',    # ARM 串口（如您的 ttyAS3）
                    '/dev/ttyAMA*',   # ARM AMBA 串口
                    '/dev/ttyO*',     # OMAP 串口
                    '/dev/ttymxc*',   # i.MX 串口
                    '/dev/ttyAP*',    # ARM Primecell 串口
                    '/dev/ttySAC*',   # Samsung 串口
                ]
                
                tty_devices = []
                for pattern in tty_patterns:
                    tty_devices.extend(glob.glob(pattern))
                
                for device in tty_devices:
                    if device != '/dev/tty':  # 排除 /dev/tty
                        ports.append({
                            'device': device,
                            'name': os.path.basename(device),
                            'description': 'Unknown serial device',
                            'hwid': '',
                            'vid': None,
                            'pid': None,
                            'serial_number': None,
                            'manufacturer': None,
                            'product': None
                        })
            except Exception as e:
                self.logger.error(f"❌ 扫描 /dev/tty* 失败: {e}")
        
        # 方法3: 强制添加已知设备（如果未被检测到）
        known_devices = ['/dev/ttyAS3']  # 添加您的已知设备
        current_devices = {port['device'] for port in ports}
        
        for device in known_devices:
            if os.path.exists(device) and device not in current_devices:
                self.logger.info(f"🔍 手动添加已知设备: {device}")
                ports.append({
                    'device': device,
                    'name': os.path.basename(device),
                    'description': f'Known serial device ({device})',
                    'hwid': 'manually_added',
                    'vid': None,
                    'pid': None,
                    'serial_number': None,
                    'manufacturer': 'Unknown',
                    'product': 'Board integrated serial port'
                })
        
        self.logger.info(f"🔍 发现 {len(ports)} 个串口设备")
        return ports

    def check_port_busy(self, device: str) -> bool:
        """检查串口是否被占用"""
        try:
            with serial.Serial(device, timeout=1) as ser:
                return False  # 能打开说明未被占用
        except serial.SerialException:
            return True  # 被占用或其他错误
        except Exception:
            return True

    def check_zigbee_by_vid_pid(self, vid: Optional[int], pid: Optional[int]) -> Optional[str]:
        """通过 VID/PID 匹配已知 Zigbee 设备"""
        if vid is None or pid is None:
            return None
            
        for device in self.zigbee_known:
            if device.get('vid') == vid and device.get('pid') == pid:
                return device.get('name', 'Unknown Zigbee')
        return None

    def check_zigbee_with_herdsman(self, device: str) -> Optional[Dict]:
        """使用 zigbee-herdsman 检测 Zigbee 适配器"""
        try:
            # 调用 NodeJS 子模块
            result = subprocess.run([
                'node', 'detect_zigbee_with_z2m.js', device
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data = json.loads(result.stdout.strip())
                if data.get('isZigbee'):
                    return {
                        'type': data.get('adapterType', 'Unknown'),
                        'method': 'herdsman'
                    }
        except subprocess.TimeoutExpired:
            self.logger.warning(f"⚠️ Zigbee 检测超时: {device}")
        except json.JSONDecodeError:
            self.logger.warning(f"⚠️ Zigbee 检测返回格式错误: {device}")
        except FileNotFoundError:
            self.logger.warning("⚠️ NodeJS 子模块不存在: detect_zigbee_with_z2m.js")
        except Exception as e:
            self.logger.warning(f"⚠️ Zigbee 检测失败 {device}: {e}")
        
        return None

    def check_zwave(self, device: str) -> bool:
        """检测 Z-Wave 适配器"""
        try:
            with serial.Serial(device, baudrate=115200, timeout=2) as ser:
                # 发送版本查询指令
                version_cmd = bytes([0x01, 0x03, 0x00, 0x07, 0xFB])
                ser.write(version_cmd)
                time.sleep(0.5)
                
                # 读取回应
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting)
                    # Z-Wave 回应通常以 0x01 开头
                    if len(response) > 0 and response[0] == 0x01:
                        return True
        except Exception as e:
            self.logger.debug(f"Z-Wave 检测失败 {device}: {e}")
        
        return False

    def detect_adapters(self) -> List[Dict]:
        """检测所有适配器"""
        ports = self.get_serial_ports()
        results = []
        
        for port in ports:
            device = port['device']
            self.logger.info(f"🔍 检测设备: {Fore.CYAN}{device}{Style.RESET_ALL}")
            
            result = port.copy()
            result.update({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'busy': self.check_port_busy(device),
                'zigbee': None,
                'zwave': False
            })
            
            # 如果设备被占用，跳过协议检测
            if result['busy']:
                self.logger.warning(f"⚠️ 设备被占用: {device}")
                results.append(result)
                continue
            
            # Zigbee 检测
            # 1. 首先尝试 VID/PID 匹配
            zigbee_name = self.check_zigbee_by_vid_pid(port['vid'], port['pid'])
            if zigbee_name:
                result['zigbee'] = {
                    'name': zigbee_name,
                    'method': 'vid_pid'
                }
                self.logger.info(f"✅ Zigbee (VID/PID): {Fore.GREEN}{zigbee_name}{Style.RESET_ALL}")
            else:
                # 2. 使用 herdsman 自动检测
                zigbee_info = self.check_zigbee_with_herdsman(device)
                if zigbee_info:
                    result['zigbee'] = zigbee_info
                    self.logger.info(f"✅ Zigbee (Herdsman): {Fore.GREEN}{zigbee_info['type']}{Style.RESET_ALL}")
            
            # Z-Wave 检测
            if self.check_zwave(device):
                result['zwave'] = True
                self.logger.info(f"✅ Z-Wave: {Fore.BLUE}{device}{Style.RESET_ALL}")
            
            results.append(result)
        
        return results

    def load_previous_results(self) -> List[Dict]:
        """加载上次扫描结果"""
        latest_file = self.storage_path / "latest.json"
        try:
            if latest_file.exists():
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 确保返回正确的数据结构
                    if isinstance(data, dict) and 'ports' in data:
                        return data.get('ports', [])
                    elif isinstance(data, list):
                        # 如果直接是端口列表，直接返回
                        return data
                    else:
                        self.logger.warning("⚠️ 历史文件格式异常，返回空列表")
                        return []
        except Exception as e:
            self.logger.warning(f"⚠️ 加载上次结果失败: {e}")
        return []

    def compare_results(self, current: List[Dict], previous: List[Dict]) -> Dict:
        """比较当前和上次结果，找出新增/移除的设备"""
        current_devices = {port['device'] for port in current}
        previous_devices = {port['device'] for port in previous}
        
        added_devices = current_devices - previous_devices
        removed_devices = previous_devices - current_devices
        
        added = [port for port in current if port['device'] in added_devices]
        removed = [port for port in previous if port['device'] in removed_devices]
        
        return {'added': added, 'removed': removed}

    def save_results(self, results: List[Dict], changes: Dict) -> str:
        """保存扫描结果"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"serial_ports_{timestamp}.json"
        filepath = self.storage_path / filename
        
        data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'ports': results,
            'added': changes['added'],
            'removed': changes['removed']
        }
        
        # 保存时间戳文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 更新 latest.json
        latest_file = self.storage_path / "latest.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"💾 结果已保存: {filename}")
        return str(filepath)

    def publish_mqtt(self, data: Dict) -> bool:
        """发布 MQTT 消息"""
        try:
            # 使用新的 MQTT 客户端 API
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            
            # 设置认证
            if self.mqtt_config.get('user') and self.mqtt_config.get('pass'):
                client.username_pw_set(self.mqtt_config['user'], self.mqtt_config['pass'])
            
            # 连接并发布
            client.connect(self.mqtt_config['broker'], self.mqtt_config['port'], 60)
            
            message = json.dumps(data, ensure_ascii=False)
            result = client.publish(
                self.mqtt_config['topic'], 
                message, 
                retain=self.mqtt_config.get('retain', True)
            )
            
            client.disconnect()
            
            if result.rc == 0:
                self.logger.info(f"📡 MQTT 发布成功: {self.mqtt_config['topic']}")
                return True
            else:
                self.logger.error(f"❌ MQTT 发布失败: {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ MQTT 连接失败: {e}")
            return False

    def run(self):
        """运行主检测流程"""
        self.logger.info(f"{Back.BLUE}{Fore.WHITE} 开始串口适配器扫描 {Style.RESET_ALL}")
        
        # 加载上次结果
        previous_results = self.load_previous_results()
        
        # 检测当前适配器
        current_results = self.detect_adapters()
        
        # 比较变化
        changes = self.compare_results(current_results, previous_results)
        
        # 报告变化
        if changes['added']:
            self.logger.info(f"🆕 新增设备: {Fore.GREEN}{len(changes['added'])}{Style.RESET_ALL} 个")
            for device in changes['added']:
                self.logger.info(f"  + {device['device']}")
        
        if changes['removed']:
            self.logger.info(f"🗑️ 移除设备: {Fore.RED}{len(changes['removed'])}{Style.RESET_ALL} 个")
            for device in changes['removed']:
                self.logger.info(f"  - {device['device']}")
        
        # 保存结果
        self.save_results(current_results, changes)
        
        # MQTT 上报
        mqtt_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'ports': current_results,
            'added': changes['added'],
            'removed': changes['removed']
        }
        
        if self.publish_mqtt(mqtt_data):
            self.logger.info("✅ 扫描完成并已上报")
        else:
            self.logger.warning("⚠️ 扫描完成但 MQTT 上报失败")
        
        # 统计输出
        zigbee_count = sum(1 for p in current_results if p.get('zigbee'))
        zwave_count = sum(1 for p in current_results if p.get('zwave'))
        busy_count = sum(1 for p in current_results if p.get('busy'))
        
        self.logger.info(f"""
{Back.GREEN}{Fore.BLACK} 扫描统计 {Style.RESET_ALL}
📊 总设备数: {len(current_results)}
🏠 Zigbee: {zigbee_count}
🌊 Z-Wave: {zwave_count}
🔒 被占用: {busy_count}
        """.strip())


def main():
    parser = argparse.ArgumentParser(description='串口适配器自动识别系统')
    parser.add_argument('--config', default='zigbee_known.yaml', help='Zigbee 已知设备配置文件')
    parser.add_argument('--storage', default='/sdcard/isgbackup/serialport/', help='存储目录')
    parser.add_argument('--mqtt-broker', default='127.0.0.1', help='MQTT Broker 地址')
    parser.add_argument('--mqtt-port', type=int, default=1883, help='MQTT 端口')
    parser.add_argument('--mqtt-user', default='admin', help='MQTT 用户名')
    parser.add_argument('--mqtt-pass', default='admin', help='MQTT 密码')
    parser.add_argument('--mqtt-topic', default='isg/serial/scan', help='MQTT 主题')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 构建 MQTT 配置
    mqtt_config = {
        'broker': args.mqtt_broker,
        'port': args.mqtt_port,
        'user': args.mqtt_user,
        'pass': args.mqtt_pass,
        'topic': args.mqtt_topic,
        'retain': True
    }
    
    # 创建检测器并运行
    detector = SerialDetector(
        config_path=args.config,
        storage_path=args.storage,
        mqtt_config=mqtt_config,
        verbose=args.verbose
    )
    
    try:
        detector.run()
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 运行错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
