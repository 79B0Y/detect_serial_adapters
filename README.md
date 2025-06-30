# 串口适配器自动识别系统设计说明

## 📌 项目目标

构建一套运行于 Android Termux + Proot Ubuntu 环境中的自动串口适配器识别系统，支持识别 Zigbee（EZSP 协议）与 Z-Wave 适配器，并通过 MQTT 实时上报识别过程与结果。

---

## 🧩 系统组成

### 1. 主脚本：`detect_serial_adapters.py`

负责整个串口识别流程，包括串口枚举、协议识别、状态上报、结果保存。

### 2. 状态记录与上报

* 本地存储：每次识别结果保存为 `serial_ports_YYYYMMDDHHMMSS.json`
* 最新结果文件为 `latest.json`
* 保留最近 3 次识别结果
* MQTT 实时上报串口状态与最终识别列表

### 3. 支持协议

* **Zigbee**（EZSP）：发送标准重置帧 `1AC038BC7E`，匹配 `11` 开头响应
* **Z-Wave**：发送版本请求 `01030015E9`，匹配 `01 10` 响应开头
* 支持常见波特率自动匹配（如 115200, 57600, 38400 等）

---

## ⚙️ 系统工作流程

1. 启动脚本 → MQTT 上报 `{ status: running }`
2. 遍历所有串口设备：`/dev/ttyUSB*`, `/dev/ttyACM*`, `/dev/ttyAS*`, `/dev/ttyS*`, `/dev/ttyAMA*`
3. 对每个串口：

   * 上报状态 `{ status: detecting, port: /dev/ttyXYZ }`
   * 判断是否被占用（lsof）

     * 若占用，上报 `{ status: occupied }`
   * 若空闲：

     * 依次尝试 Zigbee 波特率列表，发送 EZSP 命令 → 匹配响应 → 上报 `zigbee_detected`
     * 若 Zigbee 失败，继续尝试 Z-Wave 波特率，发送 Z-Wave 命令 → 匹配响应 → 上报 `zwave_detected`
     * 若全部失败，记录为未知设备
4. 所有串口探测完成后：

   * 与 `latest.json` 比对设备变更（新增/移除）
   * MQTT 上报完整列表，包括 ports, added, removed
   * 保存当前结果为 JSON 文件，并更新 latest.json
   * 清理旧记录文件，保留最新 3 个

---

## 📤 MQTT 上报格式

### 运行开始：

```json
{
  "status": "running",
  "timestamp": "2025-06-30T14:20:00Z"
}
```

### 探测状态（每个串口）

```json
{
  "status": "zigbee_detecting",
  "port": "/dev/ttyAS3",
  "timestamp": "..."
}
```

### 协议识别成功：

```json
{
  "status": "zigbee_detected",
  "port": "/dev/ttyAS3",
  "protocol": "ezsp",
  "baudrate": 115200,
  "confidence": "medium",
  "timestamp": "..."
}
```

### 最终结果汇总：

```json
{
  "timestamp": "2025-06-30T14:25:00Z",
  "ports": [ { 每个设备信息 } ],
  "added": ["/dev/ttyAS3"],
  "removed": []
}
```

---

## 📁 文件结构

```
/sdcard/isgbackup/serialport/
├── detect_serial_adapters.py      # 主程序
├── serial_detect.log              # 中文运行日志
├── serial_ports_*.json            # 每次完整结果快照
├── latest.json                    # 最新一次扫描快照
```

---

## 🔒 错误与异常处理

* 串口无法打开 → 标记为 busy / occupied
* 响应解析失败 → 忽略，标为 unknown
* MQTT 连接失败 → 控制台警告，不影响流程
* 旧记录文件删除失败 → 警告但不终止

---

## 🔜 后续优化建议

* 支持自定义 VID/PID 与设备库（zigbee\_known.yaml）
* 转为 runit 服务（开机自动探测）
* 接收 MQTT 命令触发扫描（如 `isg/serial/scan/cmd`）
* 高亮异常串口 / 多次失败串口追踪
* Web UI 状态查看
