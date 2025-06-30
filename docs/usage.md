# 串口适配器自动识别系统使用说明

本说明文档介绍如何正确使用 `detect_serial_adapters.py` 脚本进行串口设备识别，并解释输出结果和常见用途。

---

## 🔧 运行脚本

### 命令方式（Proot Ubuntu 中执行）

```bash
cd /sdcard/isgbackup/serialport
python3 detect_serial_adapters.py
```

### 环境变量覆盖 MQTT（可选）

```bash
export MQTT_BROKER=192.168.1.100
export MQTT_PORT=1883
export MQTT_USER=admin
export MQTT_PASS=pass
export MQTT_TOPIC=isg/serial/scan
```

---

## 📋 探测过程说明

脚本将依次完成：

1. MQTT 上报运行开始 `{ status: running }`
2. 遍历所有符合规则的串口 `/dev/ttyUSB*`, `/dev/ttyACM*`, `/dev/ttyAS*`, `/dev/ttyS*`, `/dev/ttyAMA*`
3. 每个串口：

   * 上报 `{ status: detecting }`
   * 若被占用，上报 `{ status: occupied }`
   * 若可用：

     * 尝试 Zigbee（EZSP）波特率及协议匹配
     * 匹配失败后尝试 Z-Wave 识别（发送版本命令）
     * 若识别成功，分别上报 `{ status: zigbee_detected }` 或 `{ status: zwave_detected }`
4. 全部识别完成后，上报最终结果（带新增/移除设备）
5. 保存本地 JSON 文件并更新 `latest.json`

---

## 📤 上报格式说明

### 状态过程上报（每个串口）

```json
{
  "status": "zigbee_detected",
  "port": "/dev/ttyAS3",
  "protocol": "ezsp",
  "baudrate": 115200,
  "confidence": "medium",
  "timestamp": "2025-06-30T14:30:22Z"
}
```

### 结果汇总上报

```json
{
  "timestamp": "2025-06-30T14:31:10Z",
  "ports": [ { 每个设备信息 } ],
  "added": ["/dev/ttyAS3"],
  "removed": []
}
```

---

## 🧾 本地输出文件

* `serial_ports_YYYYMMDDHHMMSS.json`：本次扫描完整记录
* `latest.json`：最近一次识别结果快照
* `serial_detect.log`：中文运行日志，记录探测过程、响应情况、错误信息等

最多保留 3 个历史 JSON 记录，自动清理旧文件。

---

## 📊 输出字段说明

每个串口返回的 JSON 包含：

* `port`：串口路径
* `type`：设备类型（zigbee / zwave / error / unknown）
* `protocol`：协议（如 ezsp）
* `baudrate`：识别成功使用的波特率
* `raw_response`：设备返回的响应（hex）
* `busy`：是否占用
* `timestamp`：识别时间
* `error`：错误信息（如无权限、响应超时）

---

## 🧪 常见用途

* 设备上线识别：Zigbee/Z-Wave 适配器插入后运行脚本立即识别
* Z2M/zwave-js-ui 配置前自动选定串口
* MQTT 接收识别结果并构建 UI 或存档数据库

---

## 🆘 故障排查

| 现象       | 原因                 | 解决方法                                 |
| -------- | ------------------ | ------------------------------------ |
| 无法打开串口   | 权限不足               | 确认 Termux 是否以 root 权限运行 Proot Ubuntu |
| 无响应      | 设备未接通 / 波特率不匹配     | 检查串口连接，尝试其它波特率                       |
| MQTT 无上报 | 网络不通 / broker 参数错误 | 使用 `mosquitto_sub` 验证 broker 通信      |

---

## ✅ 推荐配合

* `zigbee_known.yaml`：定义常见 Zigbee VID/PID，用于 VID 识别
* 配合 `generate_config_yaml.py` 构建 z2m / zwave-js-ui 配置文件
* 可配合 runit 或 Termux\:Boot 设置开机自启识别

---

如需支持定制、远程控制触发识别、接入 UI 等功能，请参考设计说明或联系维护者。
