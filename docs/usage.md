# 使用说明

本文档详细介绍如何使用串口适配器自动识别系统，包括基本使用、高级配置和实际应用场景。

## 🚀 快速开始

### 基本使用

```bash
# 进入项目目录
cd serial-adapter-detector

# 激活虚拟环境
source venv/bin/activate

# 运行基本检测
python3 detect_serial_adapters.py

# 运行详细检测
python3 detect_serial_adapters.py --verbose
```

### 使用启动脚本

```bash
# 使用便捷启动脚本
./start_serial_detector.sh

# 详细模式
./start_serial_detector.sh --verbose

# 自定义配置
./start_serial_detector.sh --mqtt-broker 192.168.1.100 --verbose
```

## 📊 命令行参数

### 主要参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--config` | `zigbee_known.yaml` | Zigbee 设备配置文件路径 |
| `--storage` | `/sdcard/isgbackup/serialport/` | 数据存储目录 |
| `--verbose` | `false` | 启用详细输出模式 |

### MQTT 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--mqtt-broker` | `127.0.0.1` | MQTT Broker 地址 |
| `--mqtt-port` | `1883` | MQTT 端口 |
| `--mqtt-user` | `admin` | MQTT 用户名 |
| `--mqtt-pass` | `admin` | MQTT 密码 |
| `--mqtt-topic` | `isg/serial/scan` | MQTT 发布主题 |

### 使用示例

```bash
# 基本检测
python3 detect_serial_adapters.py

# 自定义存储路径
python3 detect_serial_adapters.py --storage /tmp/serial_data

# 连接远程 MQTT
python3 detect_serial_adapters.py \
  --mqtt-broker 192.168.1.100 \
  --mqtt-port 1883 \
  --mqtt-user homeassistant \
  --mqtt-pass mypassword

# 使用自定义配置文件
python3 detect_serial_adapters.py \
  --config my_zigbee_devices.yaml \
  --verbose

# 完整配置示例
python3 detect_serial_adapters.py \
  --config zigbee_known.yaml \
  --storage /data/serialport \
  --mqtt-broker mqtt.local \
  --mqtt-port 1883 \
  --mqtt-user admin \
  --mqtt-pass secret123 \
  --mqtt-topic homeassistant/serial/scan \
  --verbose
```

## 📋 输出解析

### 控制台输出

系统使用彩色输出提供直观的状态信息：

```
🚀 串口适配器检测系统初始化完成
✅ 加载了 25 个已知 Zigbee 设备
🔍 发现 2 个串口设备
🔍 检测设备: /dev/ttyUSB0
✅ Zigbee (VID/PID): Silicon Labs CP2102/CP2109 USB to UART Bridge
🔍 检测设备: /dev/ttyUSB1
✅ Z-Wave: /dev/ttyUSB1
💾 结果已保存: serial_ports_20240101120000.json
📡 MQTT 发布成功: isg/serial/scan
✅ 扫描完成并已上报

📊 扫描统计
📊 总设备数: 2
🏠 Zigbee: 1
🌊 Z-Wave: 1
🔒 被占用: 0
```

### JSON 输出格式

系统生成的 JSON 文件包含详细的设备信息：

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "ports": [
    {
      "device": "/dev/ttyUSB0",
      "name": "ttyUSB0",
      "description": "Silicon Labs CP2102 USB to UART Bridge",
      "hwid": "USB VID:PID=10C4:EA60 SER=0001 LOCATION=1-1.2:1.0",
      "vid": 4292,
      "pid": 60000,
      "serial_number": "0001",
      "manufacturer": "Silicon Labs",
      "product": "CP2102 USB to UART Bridge Controller",
      "timestamp": "2024-01-01T12:00:00Z",
      "busy": false,
      "zigbee": {
        "name": "Silicon Labs CP2102/CP2109 USB to UART Bridge",
        "method": "vid_pid",
        "type": "EZSP"
      },
      "zwave": false
    }
  ],
  "added": [
    {
      "device": "/dev/ttyUSB0",
      "name": "ttyUSB0"
    }
  ],
  "removed": []
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `device` | string | 设备路径 (如 /dev/ttyUSB0) |
| `name` | string | 设备名称 |
| `description` | string | 设备描述信息 |
| `vid` | integer | USB Vendor ID |
| `pid` | integer | USB Product ID |
| `manufacturer` | string | 制造商名称 |
| `product` | string | 产品名称 |
| `busy` | boolean | 是否被占用 |
| `zigbee` | object/null | Zigbee 检测结果 |
| `zwave` | boolean | 是否为 Z-Wave 设备 |

## 🏠 Zigbee 设备检测

### 检测方法

系统使用两种方法检测 Zigbee 设备：

1. **VID/PID 匹配** - 基于已知设备数据库
2. **Herdsman 自动检测** - 使用 zigbee-herdsman 库

### 添加新的 Zigbee 设备

编辑 `zigbee_known.yaml` 文件：

```yaml
# 添加新设备
- vid: 0x1234
  pid: 0x5678
  name: "My Custom Zigbee Adapter"
  type: "EZSP"
  baudrate: 115200
```

### 支持的 Zigbee 协议类型

- **EZSP** - Silicon Labs EmberZNet 协议栈
- **ZNP** - Texas Instruments Z-Stack 协议栈
- **deCONZ** - Dresden Elektronik deCONZ 协议栈
- **ZiGate** - ZiGate 协议栈

### 单独测试 Zigbee 检测

```bash
# 使用 NodeJS 模块直接测试
node detect_zigbee_with_z2m.js /dev/ttyUSB0

# 查看详细输出
node detect_zigbee_with_z2m.js /dev/ttyUSB0 | jq '.'
```

## 🌊 Z-Wave 设备检测

### 检测原理

系统通过发送 Z-Wave 版本查询命令来识别 Z-Wave 适配器：

```
发送: 01 03 00 07 FB
期望回应: 01 XX XX XX ...
```

### 支持的 Z-Wave 适配器

- Aeotec Z-Stick Gen5/Gen5+
- Zooz ZST10 700 Series Z-Wave Plus S2 USB Stick
- HUSBZB-1 (Zigbee + Z-Wave)
- 其他兼容 Z-Wave Serial API 的设备

### Z-Wave 故障排除

如果 Z-Wave 检测失败：

1. 检查设备权限：
   ```bash
   ls -la /dev/ttyUSB*
   groups $USER  # 确保在 dialout 组中
   ```

2. 手动测试串口：
   ```bash
   # 使用 minicom 测试
   minicom -D /dev/ttyUSB1 -b 115200
   ```

3. 检查设备是否被占用：
   ```bash
   lsof /dev/ttyUSB1
   ```

## 📡 MQTT 集成

### MQTT 消息格式

系统发布的 MQTT 消息包含完整的检测结果：

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "ports": [...],
  "added": [...],
  "removed": [...]
}
```

### MQTT 订阅示例

#### Python 订阅者

```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload.decode())
        print(f"检测到 {len(data['ports'])} 个设备")
        
        for port in data['ports']:
            if port.get('zigbee'):
                print(f"Zigbee: {port['device']} - {port['zigbee']['name']}")
            if port.get('zwave'):
                print(f"Z-Wave: {port['device']}")
                
        if data['added']:
            print(f"新增设备: {[p['device'] for p in data['added']]}")
        if data['removed']:
            print(f"移除设备: {[p['device'] for p in data['removed']]}")
            
    except Exception as e:
        print(f"解析消息失败: {e}")

client = mqtt.Client()
client.on_message = on_message
client.connect("127.0.0.1", 1883, 60)
client.subscribe("isg/serial/scan")

print("开始监听 MQTT 消息...")
client.loop_forever()
```

#### Home Assistant 集成

在 Home Assistant 的 `configuration.yaml` 中：

```yaml
# MQTT 传感器配置
mqtt:
  sensor:
    - name: "Serial Devices Count"
      state_topic: "isg/serial/scan"
      value_template: "{{ value_json.ports | length }}"
      icon: "mdi:usb-port"
      
    - name: "Zigbee Devices Count"
      state_topic: "isg/serial/scan"
      value_template: "{{ value_json.ports | selectattr('zigbee') | list | length }}"
      icon: "mdi:zigbee"
      
    - name: "Z-Wave Devices Count"
      state_topic: "isg/serial/scan"
      value_template: "{{ value_json.ports | selectattr('zwave') | list | length }}"
      icon: "mdi:z-wave"

# 自动化示例
automation:
  - alias: "New Serial Device Detected"
    trigger:
      platform: mqtt
      topic: "isg/serial/scan"
    condition:
      template: "{{ trigger.payload_json.added | length > 0 }}"
    action:
      service: notify.mobile_app_my_phone
      data:
        title: "新设备检测"
        message: "发现新的串口设备: {{ trigger.payload_json.added[0].device }}"
```

## 🔧 配置文件生成

### 生成所有配置

```bash
# 生成所有类型的配置文件
python3 generate_config.py --type all --output ./configs

# 查看生成的文件
ls -la configs/
```

### 生成特定类型配置

```bash
# 仅生成 Zigbee2MQTT 配置
python3 generate_config.py --type z2m --output ./z2m_configs

# 仅生成 Z-Wave JS UI 配置
python3 generate_config.py --type zwave --output ./zwave_configs

# 仅生成 Docker Compose
python3 generate_config.py --type docker --output ./docker_configs
```

### 使用生成的配置

```bash
# 进入配置目录
cd configs

# 启动 Docker 容器
./start_docker.sh

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
./stop_docker.sh
```

## 🔄 定时运行

### 使用 systemd 定时器

```bash
# 启动定时检测（每5分钟）
sudo systemctl start serial-detector.timer

# 查看定时器状态
sudo systemctl status serial-detector.timer

# 查看运行日志
sudo journalctl -u serial-detector.service -f

# 停止定时器
sudo systemctl stop serial-detector.timer
```

### 使用 cron

```bash
# 编辑 crontab
crontab -e

# 添加每5分钟运行一次的任务
*/5 * * * * cd /path/to/serial-adapter-detector && ./start_serial_detector.sh >/dev/null 2>&1

# 或者记录日志
*/5 * * * * cd /path/to/serial-adapter-detector && ./start_serial_detector.sh >> /var/log/serial-detector-cron.log 2>&1
```

### 手动触发

```bash
# 通过 SSH 远程触发（从 Android APK）
ssh user@termux-ip "cd /path/to/serial-adapter-detector && ./start_serial_detector.sh"

# 使用 Android Intent 触发
am start -n com.termux/.app.TermuxActivity \
  -e "com.termux.intent.extra.COMMAND" \
  "cd /path/to/serial-adapter-detector && ./start_serial_detector.sh"
```

## 📊 监控和调试

### 日志文件

系统会生成以下日志文件：

```bash
# 主日志文件
tail -f /sdcard/isgbackup/serialport/serial_detect.log

# 系统服务日志
sudo journalctl -u serial-detector.service -f

# 查看历史记录
ls -la /sdcard/isgbackup/serialport/serial_ports_*.json
```

### 调试模式

```bash
# 启用详细调试输出
python3 detect_serial_adapters.py --verbose

# 检查特定设备
python3 -c "
import detect_serial_adapters
detector = detect_serial_adapters.SerialDetector()
ports = detector.get_serial_ports()
for port in ports:
    print(f'设备: {port[\"device\"]}, VID: {port[\"vid\"]}, PID: {port[\"pid\"]}')
"

# 单独测试 Zigbee 检测
node detect_zigbee_with_z2m.js /dev/ttyUSB0

# 单独测试 Z-Wave 检测
python3 -c "
from detect_serial_adapters import SerialDetector
detector = SerialDetector()
result = detector.check_zwave('/dev/ttyUSB1')
print(f'Z-Wave 检测结果: {result}')
"
```

### 性能监控

```bash
# 查看系统资源使用
top -p $(pgrep -f detect_serial_adapters)

# 查看内存使用
ps aux | grep detect_serial_adapters

# 查看磁盘使用
du -sh /sdcard/isgbackup/serialport/

# 清理旧日志文件（保留最近30天）
find /sdcard/isgbackup/serialport/ -name "serial_ports_*.json" -mtime +30 -delete
```

## 🔧 高级配置

### 自定义 MQTT 主题结构

修改代码以使用自定义主题结构：

```python
# 在 detect_serial_adapters.py 中自定义 MQTT 主题
def custom_mqtt_publish(self, data):
    """自定义 MQTT 发布逻辑"""
    
    # 发布总体状态
    self.publish_mqtt({
        'topic': 'homeassistant/sensor/serial_devices/state',
        'payload': {
            'total_devices': len(data['ports']),
            'zigbee_count': sum(1 for p in data['ports'] if p.get('zigbee')),
            'zwave_count': sum(1 for p in data['ports'] if p.get('zwave')),
            'timestamp': data['timestamp']
        }
    })
    
    # 为每个设备发布单独的状态
    for port in data['ports']:
        device_id = port['device'].replace('/', '_').replace('/dev/', '')
        self.publish_mqtt({
            'topic': f'homeassistant/sensor/serial_device_{device_id}/state',
            'payload': port
        })
```

### 设备别名配置

创建 `device_aliases.yaml` 文件：

```yaml
# 设备别名配置
aliases:
  "/dev/ttyUSB0": "主要 Zigbee 协调器"
  "/dev/ttyUSB1": "Z-Wave 控制棒"
  "/dev/ttyACM0": "备用协调器"

# 设备分组
groups:
  zigbee_coordinators:
    - "/dev/ttyUSB0"
    - "/dev/ttyACM0"
  zwave_controllers:
    - "/dev/ttyUSB1"

# 优先级设置
priorities:
  "/dev/ttyUSB0": 1  # 最高优先级
  "/dev/ttyUSB1": 2
  "/dev/ttyACM0": 3
```

### 条件检测配置

创建 `detection_rules.yaml` 文件：

```yaml
# 检测规则配置
rules:
  # 跳过检测的设备
  skip_devices:
    - "/dev/tty"
    - "/dev/console"
    
  # 强制检测为 Zigbee 的设备
  force_zigbee:
    - vid: 0x1234
      pid: 0x5678
      
  # 强制检测为 Z-Wave 的设备  
  force_zwave:
    - vid: 0xABCD
      pid: 0xEF01
      
  # 检测超时设置
  timeouts:
    zigbee_detection: 15  # 秒
    zwave_detection: 5    # 秒
    
  # 重试配置
  retries:
    max_attempts: 3
    delay_between_attempts: 2  # 秒
```

## 🔒 安全和权限

### 最小权限原则

```bash
# 创建专用用户
sudo useradd -r -s /bin/bash -m -d /home/serialdetector -g dialout serialdetector

# 设置目录权限
sudo chown -R serialdetector:dialout /path/to/serial-adapter-detector
sudo chmod 750 /path/to/serial-adapter-detector

# 以专用用户运行
sudo -u serialdetector ./start_serial_detector.sh
```

### MQTT 认证配置

```bash
# 创建 MQTT 用户
sudo mosquitto_passwd -c /etc/mosquitto/passwd serialdetector

# 配置 ACL
sudo tee /etc/mosquitto/acl << 'EOF'
# 允许 serialdetector 用户发布到特定主题
user serialdetector
topic write isg/serial/scan
topic write homeassistant/sensor/serial_devices/+

# 拒绝其他操作
user serialdetector
topic read #
EOF

# 更新 Mosquitto 配置
sudo tee -a /etc/mosquitto/mosquitto.conf << 'EOF'
password_file /etc/mosquitto/passwd
acl_file /etc/mosquitto/acl
allow_anonymous false
EOF

# 重启服务
sudo systemctl restart mosquitto
```

## 📈 性能优化

### 减少检测频率

```bash
# 仅在设备变化时检测
python3 detect_serial_adapters.py --detect-only-changes

# 设置最小检测间隔
python3 detect_serial_adapters.py --min-interval 300  # 5分钟
```

### 缓存优化

```python
# 在 detect_serial_adapters.py 中添加缓存
import time
from functools import lru_cache

class SerialDetector:
    def __init__(self):
        self.last_scan_time = 0
        self.scan_cache = {}
        self.cache_ttl = 60  # 缓存60秒
    
    @lru_cache(maxsize=128)
    def get_device_info_cached(self, device_path):
        """缓存设备信息"""
        return self.get_device_info(device_path)
    
    def should_skip_scan(self):
        """检查是否应该跳过扫描"""
        current_time = time.time()
        if current_time - self.last_scan_time < self.cache_ttl:
            return True
        return False
```

## 🔄 数据备份和恢复

### 备份数据

```bash
# 创建备份脚本
cat > backup_data.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/sdcard/isgbackup/serialport_backup"
DATA_DIR="/sdcard/isgbackup/serialport"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# 压缩备份
tar -czf "$BACKUP_DIR/serial_data_$DATE.tar.gz" -C "$DATA_DIR" .

# 清理旧备份（保留最近10个）
ls -t "$BACKUP_DIR"/serial_data_*.tar.gz | tail -n +11 | xargs -r rm

echo "备份完成: $BACKUP_DIR/serial_data_$DATE.tar.gz"
EOF

chmod +x backup_data.sh

# 定时备份（每天凌晨2点）
echo "0 2 * * * /path/to/backup_data.sh" | crontab -
```

### 恢复数据

```bash
# 恢复备份
cat > restore_data.sh << 'EOF'
#!/bin/bash
if [ $# -ne 1 ]; then
    echo "用法: $0 <backup_file.tar.gz>"
    exit 1
fi

BACKUP_FILE="$1"
DATA_DIR="/sdcard/isgbackup/serialport"

# 备份当前数据
mv "$DATA_DIR" "${DATA_DIR}_backup_$(date +%Y%m%d_%H%M%S)"

# 创建新目录并恢复
mkdir -p "$DATA_DIR"
tar -xzf "$BACKUP_FILE" -C "$DATA_DIR"

echo "数据恢复完成"
EOF

chmod +x restore_data.sh
```

## 📱 Android 集成

### APK 调用示例

```java
// Android 代码示例
public class SerialDetectorService {
    
    public void triggerDetection() {
        try {
            // 方法1: 使用 SSH 调用
            String command = "cd /data/data/com.termux/files/home/serial-adapter-detector && ./start_serial_detector.sh";
            Runtime.getRuntime().exec(new String[]{"su", "-c", command});
            
            // 方法2: 使用 Termux API
            Intent intent = new Intent("com.termux.RUN_COMMAND");
            intent.putExtra("com.termux.RUN_COMMAND_PATH", "/data/data/com.termux/files/home/serial-adapter-detector/start_serial_detector.sh");
            intent.putExtra("com.termux.RUN_COMMAND_ARGUMENTS", new String[]{"--verbose"});
            intent.putExtra("com.termux.RUN_COMMAND_WORKDIR", "/data/data/com.termux/files/home/serial-adapter-detector");
            context.sendBroadcast(intent);
            
        } catch (Exception e) {
            Log.e("SerialDetector", "执行检测失败", e);
        }
    }
    
    public void subscribeToMQTT() {
        // 订阅 MQTT 消息获取检测结果
        MqttAndroidClient client = new MqttAndroidClient(context, "tcp://127.0.0.1:1883", "android_client");
        
        client.setCallback(new MqttCallback() {
            @Override
            public void messageArrived(String topic, MqttMessage message) {
                if ("isg/serial/scan".equals(topic)) {
                    // 处理检测结果
                    String jsonData = new String(message.getPayload());
                    processDetectionResult(jsonData);
                }
            }
        });
        
        client.subscribe("isg/serial/scan", 0);
    }
}
```

## 🧪 测试和验证

### 单元测试

```bash
# 运行 Python 测试
pytest tests/ -v --cov=.

# 运行 JavaScript 测试
npm test

# 运行集成测试
./scripts/integration_test.sh
```

### 手动测试清单

```bash
# 1. 基本功能测试
□ 系统启动无错误
□ 能够检测已连接的 USB 设备
□ Zigbee 设备正确识别
□ Z-Wave 设备正确识别
□ 占用状态检测准确

# 2. MQTT 功能测试  
□ MQTT 连接成功
□ 消息发布正常
□ 消息格式正确
□ 认证工作正常

# 3. 数据持久化测试
□ JSON 文件正确生成
□ 历史记录对比正确
□ 日志文件记录完整

# 4. 配置生成测试
□ Z2M 配置生成正确
□ ZwaveJS 配置生成正确
□ Docker 配置可用

# 5. 错误处理测试
□ 设备拔出处理正确
□ 网络断开恢复正常
□ 权限错误提示清晰
```

## 📞 故障排除

### 常见问题及解决方案

**问题：检测不到任何设备**
```bash
# 解决步骤
1. 检查 USB 设备连接: lsusb
2. 检查设备文件: ls -la /dev/tty*
3. 检查权限: groups $USER
4. 重新插拔设备
5. 检查 udev 规则: sudo udevadm test /dev/ttyUSB0
```

**问题：MQTT 连接失败**
```bash
# 解决步骤
1. 检查服务状态: sudo systemctl status mosquitto
2. 测试连接: mosquitto_pub -h 127.0.0.1 -t test -m hello
3. 检查防火墙: sudo ufw status
4. 查看日志: sudo journalctl -u mosquitto
```

**问题：Zigbee 检测失败**
```bash
# 解决步骤
1. 检查 Node.js 依赖: npm list zigbee-herdsman
2. 手动测试: node detect_zigbee_with_z2m.js /dev/ttyUSB0
3. 检查设备支持: 查看 zigbee_known.yaml
4. 更新设备库: git pull origin main
```

**问题：权限被拒绝**
```bash
# 解决步骤
1. 添加用户到组: sudo usermod -a -G dialout $USER
2. 重新登录或重启
3. 检查文件权限: ls -la /dev/ttyUSB*
4. 临时测试: sudo python3 detect_serial_adapters.py
```

### 获取帮助

- 📚 查看完整文档: [GitHub Wiki](https://github.com/79B0Y/detect_serial_adapters/wiki)
- 🐛 报告问题: [GitHub Issues](https://github.com/79B0Y/detect_serial_adapters/issues)
- 💬 社区讨论: [GitHub Discussions](https://github.com/79B0Y/detect_serial_adapters/discussions)
- 📧 邮件支持: 通过 GitHub Issues 联系

## 🎯 最佳实践

### 生产环境建议

1. **定期备份数据**
2. **监控日志文件大小**
3. **设置告警机制**
4. **定期更新设备库**
5. **使用专用用户运行**
6. **配置日志轮转**

### 性能建议

1. **合理设置检测间隔**
2. **使用缓存减少重复检测**
3. **定期清理历史数据**
4. **监控系统资源使用**

### 安全建议

1. **使用强密码保护 MQTT**
2. **限制网络访问**
3. **定期更新依赖包**
4. **审查 udev 规则**

---

🎉 恭喜！您现在已经掌握了串口适配器自动识别系统的完整使用方法。

如有任何问题，请参考文档或联系支持团队。
