# 串口适配器自动识别系统安装指南

本指南介绍如何在 Android + Termux + Proot Ubuntu 环境中安装并运行串口自动识别系统。

---

## 📦 安装环境要求

### 系统环境

* 已 root 的 Android 设备
* 已安装 Termux 与 Termux\:Boot
* 已安装 Proot Ubuntu 环境（通过 `proot-distro`）

### 软件依赖

Termux 中需安装：

```bash
pkg update
pkg install proot-distro git python tsu
```

Proot Ubuntu 中需安装：

```bash
apt update
apt install python3 python3-pip lsof -y
pip3 install pyserial paho-mqtt
```

---

## 📂 文件准备

目录：`/sdcard/isgbackup/serialport/`

### 1. 下载脚本文件

将以下文件复制到上述目录中：

* `detect_serial_adapters.py`（主脚本）

你也可以从 GitHub 拉取：

```bash
cd /sdcard/isgbackup/serialport
curl -O https://your-server.com/detect_serial_adapters.py
chmod +x detect_serial_adapters.py
```

---

## 🚀 手动运行脚本

在 Proot Ubuntu 中运行：

```bash
proot-distro login ubuntu
cd /sdcard/isgbackup/serialport
python3 detect_serial_adapters.py
```

执行后将：

* 自动识别所有 `/dev/tty*` 串口
* 区分 Zigbee、Z-Wave、占用、未知设备
* 输出中文日志至 `serial_detect.log`
* 上报识别状态至 MQTT（默认 127.0.0.1:1883）
* 保存结果文件 `serial_ports_*.json` 与 `latest.json`

---

## ⚙️ 配置 MQTT 参数

可通过环境变量覆盖 MQTT 设置：

```bash
export MQTT_BROKER=192.168.1.100
export MQTT_PORT=1883
export MQTT_USER=admin
export MQTT_PASS=pass
export MQTT_TOPIC=isg/serial/scan
```

---

## 🛠 设置自动启动（可选）

1. 安装 Termux\:Boot 并创建开机脚本：

```bash
mkdir -p ~/.termux/boot
nano ~/.termux/boot/detect_serial.sh
```

2. 脚本内容示例：

```bash
#!/data/data/com.termux/files/usr/bin/sh
sleep 10
proot-distro login ubuntu -- bash -c 'cd /sdcard/isgbackup/serialport && python3 detect_serial_adapters.py'
```

3. 赋予执行权限：

```bash
chmod +x ~/.termux/boot/detect_serial.sh
```

重启设备后将自动运行串口识别脚本。

---

## 🧪 验证结果

* 查看 `serial_detect.log` 是否包含设备识别记录
* MQTT 服务器是否收到设备状态与识别结果
* `/sdcard/isgbackup/serialport/` 目录中是否生成最新 JSON 文件

---

## 🔄 更新脚本

若你有 Git 仓库：

```bash
cd /sdcard/isgbackup/serialport
git pull
```

或直接替换脚本文件。

---

## ✅ 安装完成

至此你已完成串口适配器自动识别系统的部署。如需集成 z2m/zwave-js-ui、WebUI 或远程控制触发，参阅后续拓展文档或联系维护者。
