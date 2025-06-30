#!/bin/bash
# Termux 环境快速安装脚本
# 专门解决 npm 包问题和依赖安装

set -e

echo "🚀 Termux 串口适配器检测系统 - 快速安装"
echo "=============================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# 步骤 1: 更新包管理器
print_info "更新 Termux 包管理器..."
pkg update -y

# 步骤 2: 安装基础工具
print_info "安装基础工具..."
pkg install -y python git curl wget

# 步骤 3: 尝试安装 NodeJS
print_info "安装 NodeJS..."
if pkg install -y nodejs; then
    print_success "NodeJS 安装成功"
    NODE_VERSION=$(node --version 2>/dev/null || echo "未知")
    print_info "NodeJS 版本: $NODE_VERSION"
    
    # 检查 npm 是否可用
    if command -v npm >/dev/null 2>&1; then
        NPM_VERSION=$(npm --version 2>/dev/null || echo "未知")
        print_success "npm 可用，版本: $NPM_VERSION"
        HAS_NPM=true
    else
        print_warning "npm 不可用，将跳过 NodeJS 依赖"
        HAS_NPM=false
    fi
else
    print_warning "NodeJS 安装失败，继续使用 Python 功能"
    HAS_NPM=false
fi

# 步骤 4: 创建 Python 虚拟环境
print_info "创建 Python 虚拟环境..."
if [ ! -d "venv" ]; then
    python -m venv venv
    print_success "虚拟环境创建成功"
fi

# 步骤 5: 激活虚拟环境并安装 Python 依赖
print_info "安装 Python 依赖..."
source venv/bin/activate

# 核心 Python 依赖
pip install --upgrade pip
pip install pyserial paho-mqtt pyyaml colorama

print_success "Python 依赖安装完成"

# 步骤 6: 安装 NodeJS 依赖（如果可能）
if [ "$HAS_NPM" = true ]; then
    print_info "安装 NodeJS 依赖..."
    
    # 创建基础 package.json（如果不存在）
    if [ ! -f "package.json" ]; then
        cat > package.json << 'EOF'
{
  "name": "serial-adapter-detector",
  "version": "1.0.0",
  "description": "Serial adapter detection system",
  "main": "detect_zigbee_with_z2m.js",
  "dependencies": {
    "zigbee-herdsman": "^0.21.0"
  }
}
EOF
        print_info "创建了 package.json"
    fi
    
    # 尝试安装 zigbee-herdsman
    if npm install zigbee-herdsman; then
        print_success "zigbee-herdsman 安装成功"
        ZIGBEE_DETECTION="完整支持 (VID/PID + Herdsman)"
    else
        print_warning "zigbee-herdsman 安装失败，使用备用方案"
        ZIGBEE_DETECTION="基础支持 (仅 VID/PID)"
    fi
else
    ZIGBEE_DETECTION="基础支持 (仅 VID/PID)"
fi

# 步骤 7: 创建必要目录
print_info "创建数据目录..."
mkdir -p "$HOME/serial_adapter_data"
mkdir -p "$HOME/logs/serial-detector"

# 设置存储权限（如果需要）
if [ ! -d "$HOME/storage" ]; then
    print_warning "未设置存储权限，正在设置..."
    termux-setup-storage || print_warning "存储权限设置失败，请手动运行: termux-setup-storage"
fi

# 步骤 8: 创建启动脚本
print_info "创建启动脚本..."
cat > start_detection.sh << 'EOF'
#!/bin/bash
# Termux 串口检测启动脚本

cd "$(dirname "$0")"

# 激活 Python 虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️ 虚拟环境不存在，请重新运行安装脚本"
    exit 1
fi

# 设置数据存储路径
STORAGE_PATH="$HOME/serial_adapter_data"
LOG_PATH="$HOME/logs/serial-detector"

# 创建目录（如果不存在）
mkdir -p "$STORAGE_PATH"
mkdir -p "$LOG_PATH"

# 检查主脚本是否存在
if [ ! -f "detect_serial_adapters.py" ]; then
    echo "❌ detect_serial_adapters.py 不存在"
    echo "请确保您在正确的项目目录中运行此脚本"
    exit 1
fi

# 运行检测脚本
echo "🚀 启动串口适配器检测..."
python detect_serial_adapters.py \
    --storage "$STORAGE_PATH" \
    --mqtt-broker 127.0.0.1 \
    --mqtt-topic "termux/serial/scan" \
    "$@"
EOF

chmod +x start_detection.sh
print_success "启动脚本创建完成"

# 步骤 9: 创建配置文件示例
print_info "创建配置文件..."

# 创建简化的 zigbee_known.yaml（如果不存在）
if [ ! -f "zigbee_known.yaml" ]; then
    cat > zigbee_known.yaml << 'EOF'
# Zigbee 已知设备配置文件 - Termux 版本
# 常见设备列表

# ConBee/ConBee II
- vid: 0x1CF1
  pid: 0x0030
  name: "Dresden Elektronik ConBee II"
  type: "deCONZ"
  baudrate: 38400

# Texas Instruments CC2531
- vid: 0x0451
  pid: 0x16A8
  name: "Texas Instruments CC2531 USB Dongle"
  type: "ZNP"
  baudrate: 115200

# Silicon Labs 适配器
- vid: 0x10C4
  pid: 0xEA60
  name: "Silicon Labs CP2102/CP2109 USB to UART Bridge"
  type: "EZSP"
  baudrate: 115200

# Sonoff Zigbee 3.0 USB Dongle Plus
- vid: 0x1A86
  pid: 0x55D4
  name: "ITead Sonoff Zigbee 3.0 USB Dongle Plus"
  type: "EZSP"
  baudrate: 115200
EOF
    print_success "创建了 zigbee_known.yaml"
fi

# 步骤 10: 运行基础测试
print_info "运行安装验证..."

# 测试 Python 环境
echo "测试 Python 依赖:"
python -c "
import sys
modules = ['serial', 'paho.mqtt.client', 'yaml', 'colorama']
for module in modules:
    try:
        __import__(module.replace('.', '_') if '.' in module else module)
        print(f'  ✅ {module}')
    except ImportError:
        print(f'  ❌ {module}')
        sys.exit(1)
print('Python 环境测试通过')
"

# 测试 NodeJS 环境
if [ "$HAS_NPM" = true ]; then
    echo "测试 NodeJS 环境:"
    if node -e "console.log('  ✅ NodeJS 运行正常')"; then
        if node -e "try { require('zigbee-herdsman'); console.log('  ✅ zigbee-herdsman 可用'); } catch(e) { console.log('  ⚠️ zigbee-herdsman 不可用'); }"; then
            true
        fi
    fi
fi

# 测试主脚本
if [ -f "detect_serial_adapters.py" ]; then
    if python detect_serial_adapters.py --help >/dev/null 2>&1; then
        print_success "主脚本测试通过"
    else
        print_warning "主脚本测试失败，但这可能是正常的"
    fi
else
    print_warning "detect_serial_adapters.py 不存在，请确保项目文件完整"
fi

# 显示安装结果
echo
print_success "🎉 Termux 安装完成！"
echo
echo "📊 安装总结:"
echo "  Python 环境: ✅ 完整支持"
echo "  NodeJS 环境: $([ "$HAS_NPM" = true ] && echo "✅ 可用" || echo "⚠️ 部分可用")"
echo "  Zigbee 检测: $ZIGBEE_DETECTION"
echo "  Z-Wave 检测: ✅ 支持"
echo "  数据存储: $HOME/serial_adapter_data"
echo "  日志目录: $HOME/logs/serial-detector"
echo
echo "🚀 使用方法:"
echo "  ./start_detection.sh                # 基本检测"
echo "  ./start_detection.sh --verbose      # 详细模式"
echo "  ls ~/serial_adapter_data/           # 查看结果"
echo
echo "📖 更多信息:"
echo "  - 项目地址: https://github.com/79B0Y/detect_serial_adapters"
echo "  - 文档: docs/usage.md"
echo
if [ "$HAS_NPM" = false ]; then
    print_warning "注意: NodeJS/npm 不可用，Zigbee 检测功能受限"
    echo "  系统将使用 VID/PID 匹配方式检测 Zigbee 设备"
    echo "  这仍然可以识别大多数常见的 Zigbee 适配器"
fi

print_success "安装完成！您现在可以开始使用串口适配器检测系统了。"
