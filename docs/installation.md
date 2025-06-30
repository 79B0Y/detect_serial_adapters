# 安装指南

本文档将详细指导您在 Android Termux + Proot Ubuntu 环境中安装串口适配器自动识别系统。

## 📋 系统要求

### 硬件要求
- Android 设备（已 root，推荐 Android 7.0+）
- 至少 2GB RAM
- 至少 4GB 可用存储空间
- USB OTG 支持（用于连接串口适配器）

### 软件要求
- Termux 应用程序
- Proot Ubuntu 环境
- USB 串口适配器（Zigbee/Z-Wave）

### 支持的适配器
- **Zigbee**: ConBee/ConBee II, CC2531, CC2652P, SkyConnect 等
- **Z-Wave**: Aeotec Z-Stick, Zooz Z-Wave USB 棒等
- **通用**: 基于 FTDI, CP210x, CH340 芯片的 USB 转串口设备

## 🚀 快速安装

### 方法一：一键安装脚本（推荐）

```bash
# 下载并运行安装脚本
curl -fsSL https://raw.githubusercontent.com/79B0Y/detect_serial_adapters/main/install.sh | sudo bash

# 或者如果您已经下载了项目
git clone https://github.com/79B0Y/detect_serial_adapters.git
cd detect_serial_adapters
sudo chmod +x install.sh
sudo ./install.sh
```

### 方法二：手动安装

如果您想了解安装过程或需要自定义安装，请按照下面的详细步骤进行。棒等
- **通用**: 基于 FTDI, CP210x, CH340 芯片的 USB 转串口设备

## 🚀 快速安装

### 方法一：一键安装脚本（推荐）

```bash
# 下载并运行安装脚本
curl -fsSL https://raw.githubusercontent.com/your-username/serial-adapter-detector/main/install.sh | sudo bash

# 或者如果您已经下载了项目
git clone https://github.com/your-username/serial-adapter-detector.git
cd serial-adapter-detector
sudo chmod +x install.sh
sudo ./install.sh
```

### 方法二：手动安装

如果您想了解安装过程或需要自定义安装，请按照下面的详细步骤进行。

## 📱 步骤 1: 准备 Android 环境

### 1.1 安装 Termux

1. 从 [F-Droid](https://f-droid.org/packages/com.termux/) 下载安装 Termux
   ```bash
   # 不要从 Google Play 安装，版本可能过旧
   ```

2. 打开 Termux 并更新包管理器：
   ```bash
   pkg update && pkg upgrade -y
   ```

3. 安装基础工具：
   ```bash
   pkg install -y git curl wget proot-distro
   ```

### 1.2 安装 Proot Ubuntu

1. 安装 Ubuntu 发行版：
   ```bash
   proot-distro install ubuntu
   ```

2. 登录到 Ubuntu 环境：
   ```bash
   proot-distro login ubuntu
   ```

3. 更新 Ubuntu 系统：
   ```bash
   apt update && apt upgrade -y
   ```

### 1.3 配置 USB 权限

1. 安装 USB 工具：
   ```bash
   pkg install -y libusb usbutils
   ```

2. 检查 USB 设备识别：
   ```bash
   lsusb
   ```

3. 如果需要 root 权限，确保设备已正确 root。

## 🐧 步骤 2: 在 Ubuntu 环境中安装依赖

### 2.1 安装系统依赖

```bash
# 进入 Ubuntu 环境
proot-distro login ubuntu

# 安装必要的系统包
apt update
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    git \
    curl \
    wget \
    udev \
    usbutils \
    lsof \
    socat \
    build-essential \
    pkg-config \
    libusb-1.0-0-dev \
    libudev-dev
```

### 2.2 检查版本

```bash
# 检查 Python 版本 (应该 >= 3.7)
python3 --version

# 检查 Node.js 版本 (应该 >= 14)
node --version

# 检查 npm 版本
npm --version
```

如果版本过低，请更新：

```bash
# 更新 Node.js (如果需要)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt-get install -y nodejs
```

## 📦 步骤 3: 安装项目

### 3.1 下载项目

```bash
# 方法一：使用 git 克隆
git clone https://github.com/79B0Y/detect_serial_adapters.git
cd detect_serial_adapters

# 方法二：下载压缩包
wget https://github.com/79B0Y/detect_serial_adapters/archive/main.zip
unzip main.zip
cd detect_serial_adapters-main
```

### 3.2 创建 Python 虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip
```

### 3.3 安装 Python 依赖

```bash
# 安装运行时依赖
pip install -r requirements.txt

# 如果需要开发环境，也安装开发依赖
pip install -r requirements-dev.txt
```

### 3.4 安装 NodeJS 依赖

```bash
# 安装 Node.js 依赖
npm install

# 如果安装失败，尝试清理缓存
npm cache clean --force
npm install
```

## ⚙️ 步骤 4: 配置系统

### 4.1 设置设备权限

```bash
# 添加当前用户到 dialout 组
sudo usermod -a -G dialout $USER

# 创建 udev 规则文件
sudo tee /etc/udev/rules.d/99-serial-adapters.rules << 'EOF'
# 串口适配器 udev 规则
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="067b", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1cf1", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="0451", MODE="0666", GROUP="dialout"
KERNEL=="ttyUSB[0-9]*", MODE="0666", GROUP="dialout"
KERNEL=="ttyACM[0-9]*", MODE="0666", GROUP="dialout"
EOF

# 重新加载 udev 规则
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 4.2 创建存储目录

```bash
# 创建数据存储目录
mkdir -p /sdcard/isgbackup/serialport/

# 创建日志目录
sudo mkdir -p /var/log/serial-detector/

# 设置权限
sudo chmod 755 /sdcard/isgbackup/serialport/
sudo chmod 755 /var/log/serial-detector/
```

### 4.3 配置 MQTT Broker（可选）

如果您需要本地 MQTT Broker：

```bash
# 安装 Mosquitto
apt install -y mosquitto mosquitto-clients

# 启动 Mosquitto
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# 测试 MQTT 连接
mosquitto_pub -h localhost -t test -m "Hello MQTT"
mosquitto_sub -h localhost -t test -C 1
```

## 🧪 步骤 5: 测试安装

### 5.1 基本功能测试

```bash
# 激活虚拟环境（如果还没激活）
source venv/bin/activate

# 测试 Python 依赖
python3 -c "import serial, paho.mqtt.client, yaml, colorama; print('✅ Python 依赖测试通过')"

# 测试 NodeJS 依赖
node -e "require('zigbee-herdsman'); console.log('✅ NodeJS 依赖测试通过')"

# 检查串口设备
ls -la /dev/tty*

# 运行检测器测试
python3 detect_serial_adapters.py --help
```

### 5.2 串口设备测试

连接您的 USB 串口适配器，然后：

```bash
# 查看新连接的设备
dmesg | tail -10

# 列出串口设备
ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null

# 运行完整检测
python3 detect_serial_adapters.py --verbose
```

### 5.3 MQTT 测试

```bash
# 测试 MQTT 发布
python3 detect_serial_adapters.py \
  --mqtt-broker 127.0.0.1 \
  --mqtt-port 1883 \
  --mqtt-user admin \
  --mqtt-pass admin \
  --verbose

# 在另一个终端监听 MQTT 消息
mosquitto_sub -h 127.0.0.1 -t "isg/serial/scan" -v
```

## 🔧 步骤 6: 配置服务（可选）

### 6.1 创建 systemd 服务

```bash
# 创建服务文件
sudo tee /etc/systemd/system/serial-detector.service << EOF
[Unit]
Description=Serial Adapter Auto Detection Service
After=network.target
Wants=network.target

[Service]
Type=oneshot
User=root
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/start_serial_detector.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 创建定时器
sudo tee /etc/systemd/system/serial-detector.timer << 'EOF'
[Unit]
Description=Run Serial Adapter Detection every 5 minutes
Requires=serial-detector.service

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable serial-detector.timer
sudo systemctl start serial-detector.timer

# 查看服务状态
sudo systemctl status serial-detector.timer
```

### 6.2 创建便捷脚本

```bash
# 创建启动脚本
cat > start_detection.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || true
python3 detect_serial_adapters.py "$@"
EOF

chmod +x start_detection.sh

# 创建停止脚本
cat > stop_detection.sh << 'EOF'
#!/bin/bash
sudo systemctl stop serial-detector.timer
echo "检测服务已停止"
EOF

chmod +x stop_detection.sh
```

## 🎯 步骤 7: 验证安装

### 7.1 完整功能测试

```bash
# 运行完整检测
./start_detection.sh --verbose

# 检查日志文件
tail -f /sdcard/isgbackup/serialport/serial_detect.log

# 查看生成的 JSON 文件
ls -la /sdcard/isgbackup/serialport/

# 查看最新检测结果
cat /sdcard/isgbackup/serialport/latest.json
```

### 7.2 生成配置文件测试

```bash
# 生成所有配置文件
python3 generate_config.py --type all --output ./test_configs

# 查看生成的配置
ls -la test_configs/

# 测试 Docker 部署
cd test_configs
./start_docker.sh
```

## 🐛 故障排除

### 常见问题

**1. 权限问题**
```bash
# 检查用户组
groups $USER

# 重新添加到组
sudo usermod -a -G dialout $USER

# 注销并重新登录
```

**2. Python 依赖安装失败**
```bash
# 更新 pip
pip install --upgrade pip

# 清理缓存
pip cache purge

# 重新安装
pip install -r requirements.txt --force-reinstall
```

**3. NodeJS 依赖问题**
```bash
# 清理 npm 缓存
npm cache clean --force

# 删除 node_modules
rm -rf node_modules package-lock.json

# 重新安装
npm install
```

**4. 串口设备不可见**
```bash
# 检查 USB 设备
lsusb

# 检查内核消息
dmesg | grep tty

# 检查 udev 规则
sudo udevadm test /dev/ttyUSB0
```

**5. MQTT 连接失败**
```bash
# 检查 MQTT 服务
sudo systemctl status mosquitto

# 测试连接
mosquitto_pub -h 127.0.0.1 -t test -m "hello"

# 查看端口
netstat -an | grep 1883
```

### 获取支持

如果您遇到其他问题：

1. 查看 [FAQ 文档](https://github.com/79B0Y/detect_serial_adapters/wiki/FAQ)
2. 搜索 [GitHub Issues](https://github.com/79B0Y/detect_serial_adapters/issues)
3. 创建新的 Issue 并提供详细信息：
   - 操作系统版本
   - Python 和 Node.js 版本
   - 错误日志
   - 硬件信息

## ✅ 安装完成

恭喜！您已成功安装串口适配器自动识别系统。

**下一步：**
- 阅读 [使用说明](usage.md) 了解详细使用方法
- 配置您的 Zigbee 和 Z-Wave 设备
- 设置自动化和监控

**有用的命令：**
```bash
# 运行检测
./start_detection.sh

# 查看帮助
python3 detect_serial_adapters.py --help

# 生成配置
python3 generate_config.py --help

# 查看日志
tail -f /sdcard/isgbackup/serialport/serial_detect.log
```

享受您的智能家居检测系统！🎉
