#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件生成器
根据检测到的串口适配器自动生成 zigbee2mqtt 和 zwave-js-ui 配置文件
"""

import json
import yaml
import os
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class ConfigGenerator:
    def __init__(self, scan_result_file: str = "/sdcard/isgbackup/serialport/latest.json"):
        self.scan_result_file = scan_result_file
        self.scan_data = self.load_scan_results()
        
    def load_scan_results(self) -> Dict:
        """加载扫描结果"""
        try:
            with open(self.scan_result_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 无法加载扫描结果: {e}")
            return {'ports': []}
    
    def get_zigbee_adapters(self) -> List[Dict]:
        """获取所有 Zigbee 适配器"""
        zigbee_adapters = []
        for port in self.scan_data.get('ports', []):
            if port.get('zigbee') and not port.get('busy'):
                zigbee_adapters.append(port)
        return zigbee_adapters
    
    def get_zwave_adapters(self) -> List[Dict]:
        """获取所有 Z-Wave 适配器"""
        zwave_adapters = []
        for port in self.scan_data.get('ports', []):
            if port.get('zwave') and not port.get('busy'):
                zwave_adapters.append(port)
        return zwave_adapters
    
    def generate_z2m_config(self, output_dir: str = "./configs") -> List[str]:
        """生成 zigbee2mqtt 配置文件"""
        zigbee_adapters = self.get_zigbee_adapters()
        if not zigbee_adapters:
            print("⚠️ 未发现可用的 Zigbee 适配器")
            return []
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        
        for i, adapter in enumerate(zigbee_adapters):
            # 确定适配器类型和配置
            zigbee_info = adapter.get('zigbee', {})
            adapter_type = zigbee_info.get('type', 'auto').lower()
            
            # 适配器类型映射
            adapter_mapping = {
                'ezsp': 'ezsp',
                'znp': 'znp', 
                'deconz': 'deconz',
                'zigate': 'zigate',
                'ember': 'ember'
            }
            
            z2m_adapter = adapter_mapping.get(adapter_type, 'auto')
            
            # 生成配置
            config = {
                'homeassistant': True,
                'permit_join': False,
                'mqtt': {
                    'base_topic': f'zigbee2mqtt_{i}' if i > 0 else 'zigbee2mqtt',
                    'server': 'mqtt://127.0.0.1:1883',
                    'user': 'admin',
                    'password': 'admin'
                },
                'serial': {
                    'port': adapter['device'],
                    'adapter': z2m_adapter,
                    'baudrate': self._get_baudrate(adapter),
                    'rtscts': False
                },
                'advanced': {
                    'log_level': 'info',
                    'pan_id': 6754 + i,
                    'channel': 11 + (i % 5),  # 分散到不同信道
                    'network_key': 'GENERATE'
                },
                'frontend': {
                    'port': 8080 + i,
                    'host': '0.0.0.0'
                },
                'experimental': {
                    'new_api': True
                }
            }
            
            # 添加设备特定配置
            if adapter_type == 'deconz':
                config['serial']['adapter'] = 'deconz'
                config['serial']['baudrate'] = 38400
            elif adapter_type == 'ezsp':
                config['advanced']['ezsp_config'] = {
                    'CONCENTRATOR_RAM_TYPE': 'high_ram',
                    'CONCENTRATOR_DISCOVERY_TIME': 10
                }
            
            # 保存配置文件
            config_filename = f"z2m_config_{i}.yaml" if i > 0 else "z2m_configuration.yaml"
            config_path = output_path / config_filename
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            generated_files.append(str(config_path))
            print(f"✅ 生成 Z2M 配置: {config_filename}")
            print(f"   设备: {adapter['device']}")
            print(f"   类型: {zigbee_info.get('name', 'Unknown')}")
            print(f"   前端端口: {config['frontend']['port']}")
        
        return generated_files
    
    def generate_zwave_js_ui_config(self, output_dir: str = "./configs") -> List[str]:
        """生成 zwave-js-ui 配置文件"""
        zwave_adapters = self.get_zwave_adapters()
        if not zwave_adapters:
            print("⚠️ 未发现可用的 Z-Wave 适配器")
            return []
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        
        for i, adapter in enumerate(zwave_adapters):
            # 生成配置
            config = {
                'zwave': {
                    'port': adapter['device'],
                    'baudrate': 115200,
                    'networkKey': None,  # 将自动生成
                    'enableSoftReset': True,
                    'rf': {
                        'region': 'Default'  # 可配置为具体地区
                    }
                },
                'mqtt': {
                    'enabled': True,
                    'host': '127.0.0.1',
                    'port': 1883,
                    'username': 'admin',
                    'password': 'admin',
                    'name': f'zwave-js-ui-{i}' if i > 0 else 'zwave-js-ui',
                    'qos': 1,
                    'prefix': f'zwave_{i}' if i > 0 else 'zwave',
                    'retained': True
                },
                'gateway': {
                    'type': 1,  # Named topics
                    'payloadType': 0,  # JSON Time-Value
                    'nodeNames': True,
                    'ignoreLoc': True,
                    'sendEvents': True
                },
                'ui': {
                    'port': 8091 + i,
                    'host': '0.0.0.0',
                    'title': f'Z-Wave JS UI {i}' if i > 0 else 'Z-Wave JS UI'
                },
                'session': {
                    'secret': f'zwave-js-ui-secret-{i}',
                    'cookie': {
                        'maxAge': 86400000
                    }
                }
            }
            
            # 保存配置文件
            config_filename = f"zwave_js_ui_config_{i}.json" if i > 0 else "zwave_js_ui_settings.json"
            config_path = output_path / config_filename
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            generated_files.append(str(config_path))
            print(f"✅ 生成 Z-Wave JS UI 配置: {config_filename}")
            print(f"   设备: {adapter['device']}")
            print(f"   Web 端口: {config['ui']['port']}")
        
        return generated_files
    
    def generate_docker_compose(self, output_dir: str = "./configs") -> Optional[str]:
        """生成 Docker Compose 配置"""
        zigbee_adapters = self.get_zigbee_adapters()
        zwave_adapters = self.get_zwave_adapters()
        
        if not zigbee_adapters and not zwave_adapters:
            print("⚠️ 未发现任何可用适配器")
            return None
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        services = {}
        
        # 添加 MQTT 服务
        services['mqtt'] = {
            'image': 'eclipse-mosquitto:latest',
            'container_name': 'mqtt',
            'restart': 'unless-stopped',
            'ports': ['1883:1883', '9001:9001'],
            'volumes': [
                './mqtt/config:/mosquitto/config',
                './mqtt/data:/mosquitto/data',
                './mqtt/log:/mosquitto/log'
            ],
            'environment': {
                'MOSQUITTO_USERNAME': 'admin',
                'MOSQUITTO_PASSWORD': 'admin'
            }
        }
        
        # 添加 Zigbee2MQTT 服务
        for i, adapter in enumerate(zigbee_adapters):
            service_name = f'zigbee2mqtt_{i}' if i > 0 else 'zigbee2mqtt'
            config_file = f'z2m_config_{i}.yaml' if i > 0 else 'z2m_configuration.yaml'
            
            services[service_name] = {
                'image': 'koenkk/zigbee2mqtt:latest',
                'container_name': service_name,
                'restart': 'unless-stopped',
                'depends_on': ['mqtt'],
                'environment': {
                    'TZ': 'Asia/Shanghai'
                },
                'ports': [f'{8080 + i}:8080'],
                'volumes': [
                    f'./z2m_{i}/data:/app/data',
                    f'./configs/{config_file}:/app/data/configuration.yaml'
                ],
                'devices': [f'{adapter["device"]}:{adapter["device"]}']
            }
        
        # 添加 Z-Wave JS UI 服务
        for i, adapter in enumerate(zwave_adapters):
            service_name = f'zwave_js_ui_{i}' if i > 0 else 'zwave_js_ui'
            config_file = f'zwave_js_ui_config_{i}.json' if i > 0 else 'zwave_js_ui_settings.json'
            
            services[service_name] = {
                'image': 'zwavejs/zwave-js-ui:latest',
                'container_name': service_name,
                'restart': 'unless-stopped',
                'depends_on': ['mqtt'],
                'environment': {
                    'TZ': 'Asia/Shanghai'
                },
                'ports': [f'{8091 + i}:8091'],
                'volumes': [
                    f'./zwave_{i}/store:/usr/src/app/store',
                    f'./configs/{config_file}:/usr/src/app/store/settings.json'
                ],
                'devices': [f'{adapter["device"]}:{adapter["device"]}']
            }
        
        # 生成 docker-compose.yml
        compose_config = {
            'version': '3.8',
            'services': services,
            'networks': {
                'default': {
                    'name': 'smart_home'
                }
            }
        }
        
        compose_path = output_path / "docker-compose.yml"
        with open(compose_path, 'w', encoding='utf-8') as f:
            yaml.dump(compose_config, f, default_flow_style=False, indent=2)
        
        print(f"✅ 生成 Docker Compose 配置: {compose_path}")
        return str(compose_path)
    
    def generate_startup_scripts(self, output_dir: str = "./configs") -> List[str]:
        """生成启动脚本"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        
        # 生成 Docker 启动脚本
        docker_script = output_path / "start_docker.sh"
        with open(docker_script, 'w', encoding='utf-8') as f:
            f.write("""#!/bin/bash
# Docker 容器启动脚本

set -e

echo "🚀 启动智能家居服务..."

# 创建必要的目录
mkdir -p mqtt/{config,data,log}
mkdir -p z2m_*/data
mkdir -p zwave_*/store

# 创建 MQTT 配置
cat > mqtt/config/mosquitto.conf << 'EOF'
listener 1883
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log
EOF

# 启动所有服务
docker-compose up -d

echo "✅ 服务启动完成！"
echo
echo "📊 服务状态:"
docker-compose ps

echo
echo "🌐 Web 界面:"
""")
            
            # 添加服务 URL
            zigbee_adapters = self.get_zigbee_adapters()
            zwave_adapters = self.get_zwave_adapters()
            
            for i, _ in enumerate(zigbee_adapters):
                name = f"Zigbee2MQTT {i}" if i > 0 else "Zigbee2MQTT"
                f.write(f'echo "  {name}: http://localhost:{8080 + i}"\n')
            
            for i, _ in enumerate(zwave_adapters):
                name = f"Z-Wave JS UI {i}" if i > 0 else "Z-Wave JS UI"
                f.write(f'echo "  {name}: http://localhost:{8091 + i}"\n')
            
            f.write('\necho\necho "📝 查看日志: docker-compose logs -f"\n')
        
        os.chmod(docker_script, 0o755)
        generated_files.append(str(docker_script))
        
        # 生成停止脚本
        stop_script = output_path / "stop_docker.sh"
        with open(stop_script, 'w', encoding='utf-8') as f:
            f.write("""#!/bin/bash
# Docker 容器停止脚本

echo "🛑 停止智能家居服务..."
docker-compose down
echo "✅ 服务已停止"
""")
        
        os.chmod(stop_script, 0o755)
        generated_files.append(str(stop_script))
        
        print(f"✅ 生成启动脚本: {len(generated_files)} 个")
        return generated_files
    
    def _get_baudrate(self, adapter: Dict) -> int:
        """根据适配器类型获取波特率"""
        zigbee_info = adapter.get('zigbee', {})
        adapter_type = zigbee_info.get('type', '').lower()
        
        # 根据适配器类型返回默认波特率
        baudrate_map = {
            'deconz': 38400,
            'ezsp': 115200,
            'znp': 115200,
            'zigate': 115200
        }
        
        return baudrate_map.get(adapter_type, 115200)
    
    def generate_all_configs(self, output_dir: str = "./configs") -> Dict:
        """生成所有配置文件"""
        print("🔧 开始生成配置文件...")
        
        result = {
            'z2m_configs': [],
            'zwave_configs': [],
            'docker_compose': None,
            'startup_scripts': []
        }
        
        # 生成各种配置
        result['z2m_configs'] = self.generate_z2m_config(output_dir)
        result['zwave_configs'] = self.generate_zwave_js_ui_config(output_dir)
        result['docker_compose'] = self.generate_docker_compose(output_dir)
        result['startup_scripts'] = self.generate_startup_scripts(output_dir)
        
        # 生成总结报告
        self._generate_summary_report(result, output_dir)
        
        print("\n🎉 配置文件生成完成！")
        return result
    
    def _generate_summary_report(self, result: Dict, output_dir: str):
        """生成总结报告"""
        output_path = Path(output_dir)
        report_path = output_path / "generation_report.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# 配置文件生成报告\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 设备统计
            zigbee_count = len(self.get_zigbee_adapters())
            zwave_count = len(self.get_zwave_adapters())
            
            f.write(f"## 设备统计\n\n")
            f.write(f"- Zigbee 适配器: {zigbee_count} 个\n")
            f.write(f"- Z-Wave 适配器: {zwave_count} 个\n\n")
            
            # 生成的文件
            f.write(f"## 生成的配置文件\n\n")
            for config_file in result['z2m_configs']:
                f.write(f"- 📱 {os.path.basename(config_file)}\n")
            for config_file in result['zwave_configs']:
                f.write(f"- 🌊 {os.path.basename(config_file)}\n")
            if result['docker_compose']:
                f.write(f"- 🐳 {os.path.basename(result['docker_compose'])}\n")
            for script in result['startup_scripts']:
                f.write(f"- 🚀 {os.path.basename(script)}\n")
            
            f.write(f"\n## 启动说明\n\n")
            f.write(f"1. 进入配置目录: `cd {output_dir}`\n")
            f.write(f"2. 启动服务: `./start_docker.sh`\n")
            f.write(f"3. 停止服务: `./stop_docker.sh`\n")
            f.write(f"4. 查看日志: `docker-compose logs -f`\n")
        
        print(f"📋 生成报告: {report_path}")


def main():
    parser = argparse.ArgumentParser(description='串口适配器配置文件生成器')
    parser.add_argument('--input', '-i', default='/sdcard/isgbackup/serialport/latest.json',
                        help='扫描结果文件路径')
    parser.add_argument('--output', '-o', default='./configs',
                        help='输出目录')
    parser.add_argument('--type', choices=['z2m', 'zwave', 'docker', 'all'], default='all',
                        help='生成配置类型')
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not os.path.exists(args.input):
        print(f"❌ 扫描结果文件不存在: {args.input}")
        print("请先运行 detect_serial_adapters.py 进行设备扫描")
        return 1
    
    generator = ConfigGenerator(args.input)
    
    try:
        if args.type == 'z2m':
            generator.generate_z2m_config(args.output)
        elif args.type == 'zwave':
            generator.generate_zwave_js_ui_config(args.output)
        elif args.type == 'docker':
            generator.generate_docker_compose(args.output)
        elif args.type == 'all':
            generator.generate_all_configs(args.output)
            
    except Exception as e:
        print(f"❌ 生成配置失败: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
