# 串口适配器自动识别系统

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![Node.js](https://img.shields.io/badge/node.js-14+-green.svg)
![Platform](https://img.shields.io/badge/platform-Android%20Termux-orange.svg)

专为 **Android Termux + Proot Ubuntu** 环境设计的串口适配器自动识别系统。能够自动检测并识别 Zigbee 和 Z-Wave 串口适配器，通过 MQTT 实时上报设备状态。

## ✨ 主要功能

- 🔍 **自动扫描** 所有 `/dev/tty*` 串口设备
- 🏠 **Zigbee 检测** 支持 zigbee-herdsman 自动检测 + VID/PID 匹配
- 🌊 **Z-Wave 检测** 通过版本命令识别 Z-Wave 适配器
- 📊 **占用状态** 实时监控串口占用情况
- 📡 **MQTT 上报** 实时推送扫描结果
- 💾 **历史记录** JSON 文件存档，支持新增/移除设备对比
- 🎨 **彩色输出** 中文界面，直观的控制台显示
- ⚡ **高性能** 支持批量检测和异步处理

## 🚀 快速开始

### 环境要求

- Android 设备（已 root）
- Termux + Proot Ubuntu 环境
- Python 3.7+
- Node.js 14+
- MQTT Broker

### 一键安装

```bash
# 下载安装脚本
curl -fsSL https://raw.githubusercontent.com/your-repo/install.sh | sudo bash

# 或者克隆仓库手动安装
git clone https://github.com/your-repo/serial-adapter-detector.git
cd serial-adapter-detector
sudo chmod +x install.sh
sudo ./install.sh
```

### 手动安装

1. **安装系统依赖**
```bash
apt update && apt install -y python3 python3-pip nodejs npm udev usbutils
```

2. **安装 Python 依赖**
```bash
pip3 install -r requirements.txt
```

3. **安装 NodeJS 依赖**
```bash
npm install
```

4. **创建存储目录**
```bash
mkdir -p /sdcard/isgbackup/serialport/
```

5. **设置权限**
```bash
sudo usermod -a -G dialout $USER
```

## 📖 使用说明

### 基本用法

```bash
# 直接运行检测
python3 detect_serial_adapters.py

# 详细输出模式
python3 detect_serial_adapters.py --verbose

# 使用启动脚本
./start_serial_detector.sh

# 自定义 MQTT 配置
python3 detect_serial_adapters.py \
  --mqtt-broker 192.168.1.100 \
  --mqtt-port 1883 \
  --mqtt-user admin \
  --mqtt-pass password
```

### 参数选项

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--config` | `zigbee_known.yaml` | Zigbee 设备配置文件 |
| `--storage` | `/sdcard/isgbackup/serialport/` | 数据存储目录 |
| `--mqtt-broker` | `127.0.0.1` | MQTT Broker 地址 |
| `--mqtt-port` | `1883` | MQTT 端口 |
| `--mqtt-user` | `admin` | MQTT 用户名 |
| `--mqtt-pass` | `admin` | MQTT 密码 |
| `--mqtt-topic` | `isg/serial/scan` | MQTT 主题 |
| `--verbose` | `false` | 详细输出模式 |

### 定时服务

```bash
# 启动定时检测服务（每5分钟）
sudo systemctl start serial-detector.timer

# 查看服务状态
sudo systemctl status serial-detector.timer

# 停止服务
sudo systemctl stop serial-detector.timer
```

## 📊 输出格式

### MQTT 消息格式

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "ports": [
    {
      "device": "/dev/ttyUSB0",
      "name": "ttyUSB0",
      "description": "Silicon Labs CP2102 USB to UART Bridge",
      "vid": 4292,
      "pid": 60000,
      "manufacturer": "Silicon Labs",
      "product": "CP2102 USB to UART Bridge Controller",
      "busy": false,
      "zigbee": {
        "name": "Silicon Labs CP2102/CP2109 USB to UART Bridge",
        "method": "vid_pid",
        "type": "EZSP"
      },
      "zwave": false
    }
  ],
  "added": [],
  "removed": []
}
```

### 日志输出示例

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

## ⚙️ 配置文件

### zigbee_known.yaml

包含已知 Zigbee 设备的 VID/PID 数据库：

```yaml
- vid: 0x10C4
  pid: 0xEA60
  name: "Silicon Labs CP2102/CP2109 USB to UART Bridge"
  type: "EZSP"
  baudrate: 115200

- vid: 0x1CF1
  pid: 0x0030
  name: "Dresden Elektronik ConBee II"
  type: "deCONZ"
  baudrate: 38400
```

支持的设备类型：
- **EZSP**: Silicon Labs EmberZNet 协议栈
- **ZNP**: Texas Instruments Z-Stack 协议栈  
- **deCONZ**: Dresden Elektronik deCONZ 协议栈
- **ZiGate**: ZiGate 协议栈

## 🔧 高级功能

### 自定义检测脚本

可以通过修改 `detect_zigbee_with_z2m.js` 来自定义 Zigbee 检测逻辑：

```javascript
// 自定义适配器检测超时时间
const adapter = await herdsman.adapter.autoDetectAdapter(serialPort, {
    timeout: 20000,  // 20秒超时
    baudrates: [115200, 38400, 57600, 9600]
});
```

### 集成到现有系统

系统设计为模块化，可以轻松集成到其他项目：

```python
from detect_serial_adapters import SerialDetector

detector = SerialDetector()
results = detector.detect_adapters()
print(f"发现 {len(results)} 个设备")
```

### MQTT 订阅示例

```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, message):
    data = json.loads(message.payload.decode())
    print(f"检测到 {len(data['ports'])} 个串口设备")
    
    for port in data['ports']:
        if port.get('zigbee'):
            print(f"Zigbee: {port['device']} - {port['zigbee']['name']}")
        if port.get('zwave'):
            print(f"Z-Wave: {port['device']}")

client = mqtt.Client()
client.on_message = on_message
client.connect("127.0.0.1", 1883, 60)
client.subscribe("isg/serial/scan")
client.loop_forever()
```

## 🐛 故障排除

### 常见问题

**1. 权限问题**
```bash
# 检查用户组
groups $USER

# 添加到 dialout 组
sudo usermod -a -G dialout $USER

# 重新登录或重启
```

**2. NodeJS 依赖问题**
```bash
# 清理并重新安装
rm -rf node_modules package-lock.json
npm install

# 或使用 yarn
yarn install
```

**3. Python 依赖问题**
```bash
# 使用虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**4. 串口设备检测不到**
```bash
# 检查设备是否存在
ls -la /dev/tty*

# 检查设备权限
ls -la /dev/ttyUSB*

# 查看系统日志
dmesg | grep tty
```

**5. MQTT 连接失败**
```bash
# 测试 MQTT 连接
mosquitto_pub -h 127.0.0.1 -t test -m "hello"

# 检查防火墙
sudo ufw status
```

### 调试模式

启用详细日志进行调试：

```bash
# 启用详细输出
python3 detect_serial_adapters.py --verbose

# 查看日志文件
tail -f /sdcard/isgbackup/serialport/serial_detect.log

# 单独测试 Zigbee 检测
node detect_zigbee_with_z2m.js /dev/ttyUSB0
```

### 性能优化

```bash
# 限制扫描设备范围
export SCAN_PATTERN="/dev/ttyUSB*"

# 调整检测超时时间
export ZIGBEE_TIMEOUT=10000
export ZWAVE_TIMEOUT=5000
```

## 🔮 路线图

### v1.1 计划功能
- [ ] 自动波特率检测
- [ ] 支持更多协议（Thread、Matter）
- [ ] Web 管理界面
- [ ] 设备健康监控
- [ ] 配置文件热重载

### v1.2 计划功能
- [ ] 自动生成 z2m/zwave-js-ui 配置
- [ ] 设备固件版本检测
- [ ] 远程设备管理
- [ ] 集群部署支持
- [ ] 性能监控面板

### v2.0 愿景
- [ ] AI 驱动的设备识别
- [ ] 云端设备数据库
- [ ] 移动端 APP
- [ ] 企业级功能

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. **Fork 项目**
2. **创建功能分支** (`git checkout -b feature/amazing-feature`)
3. **提交更改** (`git commit -m 'Add amazing feature'`)
4. **推送到分支** (`git push origin feature/amazing-feature`)
5. **创建 Pull Request**

### 代码规范

- Python: 遵循 PEP 8，使用 `black` 格式化
- JavaScript: 遵循 ESLint 规则
- 提交信息: 使用 [Conventional Commits](https://conventionalcommits.org/)

### 测试

```bash
# Python 测试
pytest tests/

# JavaScript 测试
npm test

# 集成测试
./tests/integration_test.sh
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [zigbee-herdsman](https://github.com/Koenkk/zigbee-herdsman) - Zigbee 协议栈
- [pyserial](https://github.com/pyserial/pyserial) - Python 串口库
- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) - MQTT 客户端
- [Termux](https://termux.com/) - Android 终端环境

## 📞 支持

- 📚 [Wiki 文档](https://github.com/your-repo/serial-adapter-detector/wiki)
- 🐛 [问题反馈](https://github.com/your-repo/serial-adapter-detector/issues)
- 💬 [讨论区](https://github.com/your-repo/serial-adapter-detector/discussions)
- 📧 邮件: support@yourproject.com

---

<p align="center">
  <b>⭐ 如果这个项目对你有帮助，请给我们一个 Star！</b>
</p>

<p align="center">
  Made with ❤️ for the Smart Home Community
</p>
