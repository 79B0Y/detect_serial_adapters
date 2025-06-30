#!/usr/bin/env python3
# 快速修复脚本 - 立即识别 ttyAS3 设备

import os
import glob
import json
import serial
import serial.tools.list_ports
from datetime import datetime, timezone

def get_all_serial_ports():
    """获取所有串口设备，包括 ttyAS* 设备"""
    ports = []
    
    # 扩展的串口扫描模式
    patterns = [
        '/dev/ttyUSB*',
        '/dev/ttyACM*', 
        '/dev/ttyS*',
        '/dev/ttyAS*',     # ARM 串口
        '/dev/ttyAMA*',    # ARM AMBA
        '/dev/ttyO*',      # OMAP
        '/dev/ttymxc*',    # i.MX
    ]
    
    devices = []
    for pattern in patterns:
        devices.extend(glob.glob(pattern))
    
    # 去重并排序
    devices = sorted(list(set(devices)))
    
    for device in devices:
        if device == '/dev/tty':  # 跳过虚拟终端
            continue
            
        try:
            # 检查设备是否可访问
            port_info = {
                'device': device,
                'name': os.path.basename(device),
                'exists': os.path.exists(device),
                'readable': os.access(device, os.R_OK),
                'writable': os.access(device, os.W_OK),
            }
            
            # 尝试获取更多信息
            try:
                # 检查是否被占用
                with serial.Serial(device, timeout=0.1) as ser:
                    port_info['busy'] = False
            except serial.SerialException:
                port_info['busy'] = True
            except Exception:
                port_info['busy'] = None
                
            ports.append(port_info)
            
        except Exception as e:
            print(f"检查设备 {device} 时出错: {e}")
    
    return ports

def check_zigbee_by_device_name(device):
    """基于设备名称和路径判断可能的 Zigbee 类型"""
    device_lower = device.lower()
    
    # 板载串口通常是 Zigbee 模组
    if 'ttyas' in device_lower:
        return {
            'likely_zigbee': True,
            'type': 'EZSP',  # 您提到是 EZSP 芯片
            'confidence': 'high',
            'reason': 'Board integrated Zigbee module'
        }
    
    return None

def test_zigbee_communication(device):
    """测试是否为 Zigbee 设备"""
    try:
        with serial.Serial(device, baudrate=115200, timeout=2) as ser:
            # EZSP 通信测试 - 发送版本查询
            # EZSP frame: [len, frame_control, sequence, frame_id, parameters]
            ezsp_version_cmd = bytes([0x00, 0x00, 0x00, 0x00])  # 简化的测试命令
            
            ser.write(ezsp_version_cmd)
            ser.flush()
            
            response = ser.read(10)
            if len(response) > 0:
                return {
                    'responds': True,
                    'response_length': len(response),
                    'response_hex': response.hex(),
                    'likely_zigbee': True
                }
    except Exception as e:
        return {
            'responds': False,
            'error': str(e),
            'likely_zigbee': False
        }
    
    return {'responds': False, 'likely_zigbee': False}

def main():
    print("🔍 快速串口设备扫描 - 特别检测 ttyAS3")
    print("=" * 50)
    
    # 获取所有串口设备
    ports = get_all_serial_ports()
    
    print(f"发现 {len(ports)} 个串口设备:")
    
    for port in ports:
        device = port['device']
        name = port['name']
        
        print(f"\n📍 设备: {device}")
        print(f"   名称: {name}")
        print(f"   存在: {'✅' if port['exists'] else '❌'}")
        print(f"   可读: {'✅' if port['readable'] else '❌'}")
        print(f"   可写: {'✅' if port['writable'] else '❌'}")
        print(f"   占用: {'🔒' if port['busy'] else '🔓' if port['busy'] is False else '❓'}")
        
        # 特别检测 Zigbee
        zigbee_info = check_zigbee_by_device_name(device)
        if zigbee_info:
            print(f"   🏠 Zigbee: {zigbee_info}")
            
            # 如果设备未被占用，尝试通信测试
            if not port['busy'] and port['readable'] and port['writable']:
                print(f"   🧪 通信测试中...")
                comm_result = test_zigbee_communication(device)
                print(f"   📡 通信结果: {comm_result}")
    
    # 特别关注 ttyAS3
    ttyAS3_found = any(port['device'] == '/dev/ttyAS3' for port in ports)
    
    print("\n" + "=" * 50)
    if ttyAS3_found:
        print("✅ /dev/ttyAS3 已被检测到！")
        ttyAS3_info = next(port for port in ports if port['device'] == '/dev/ttyAS3')
        
        if not ttyAS3_info['busy']:
            print("🎉 设备可用，建议配置:")
            print("   设备路径: /dev/ttyAS3")
            print("   适配器类型: EZSP")
            print("   波特率: 115200")
            print("   用于: Zigbee2MQTT")
            
            # 生成 Z2M 配置建议
            z2m_config = {
                "serial": {
                    "port": "/dev/ttyAS3",
                    "adapter": "ezsp",
                    "baudrate": 115200
                },
                "mqtt": {
                    "server": "mqtt://127.0.0.1:1883"
                },
                "homeassistant": True
            }
            
            print("\n📋 建议的 Zigbee2MQTT 配置:")
            print(json.dumps(z2m_config, indent=2))
            
        else:
            print("⚠️ 设备被占用，可能已经在使用中")
    else:
        print("❌ /dev/ttyAS3 未找到")
    
    print(f"\n📊 扫描完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
