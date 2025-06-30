#!/bin/bash
# 串口适配器自动识别系统 - Termux 专用安装脚本
# 适用于 Android Termux 环境（无需 root 权限）

set -e

echo "🚀 开始安装串口适配器自动识别系统 (Termux 版本)..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查是否在 Termux 环境中
check_termux_environment() {
    print_info "检查 Termux 环境..."
    
    if [ -z "$TERMUX_VERSION" ] && [ ! -d "/data/data/com.termux" ]; then
        print_warning "未检测到 Termux 环境"
        print_info "此脚本专为 Termux 设计，但会尝试继续安装"
    else
        print_success "检测到 Termux 环境"
    fi
    
    # 显示 Android 版本信息
    if command -v getprop >/dev/null 2>&1; then
        ANDROID_VERSION=$(getprop ro.build.version.release 2>/dev/null || echo "Unknown")
        print_info "Android 版本: $ANDROID_VERSION"
    fi
}

# 更新包管理器
update_packages() {
    print_info "更新 Termux 包管理器..."
    
    # 更新包列表
    pkg update -y
    
    # 升级已安装的包
    pkg upgrade -y
    
    print_success "包管理器更新完成"
}

# 安装系统工具
install_system_tools() {
    print_info "安装系统工具..."
    
    # 安装必要的系统工具
    pkg install -y \
        curl \
        wget \
        git \
        unzip \
        zip \
        tar \
        gzip \
        file \
        which \
        lsof \
        proot-distro
    
    print_success "系统工具安装完成"
}

# 安装 Python 环境
install_python() {
    print_info "安装 Python 环境..."
    
    # 安装 Python 和相关工具
    pkg install -y \
        python \
        python-pip
    
    # 检查 Python 版本
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    print_info "Python 版本: $PYTHON_VERSION"
    
    # 升级 pip
    pip install --upgrade pip
    
    print_success "Python 环境安装完成"
}

# 安装 NodeJS 环境
install_nodejs() {
    print_info "安装 NodeJS 环境..."
    
    # 在 Termux 中，npm 包含在 nodejs 包中
    pkg install -y nodejs
    
    # 检查版本
    if command -v node >/dev/null 2>&1; then
        NODE_VERSION=$(node --version)
        print_info "NodeJS 版本: $NODE_VERSION"
    else
        print_error "NodeJS 安装失败"
        return 1
    fi
    
    if command -v npm >/dev/null 2>&1; then
        NPM_VERSION=$(npm --version)
        print_info "NPM 版本: $NPM_VERSION"
        
        # 升级 npm（可选）
        npm install -g npm@latest 2>/dev/null || print_warning "npm 升级失败，但这不影响基本功能"
    else
        print_warning "npm 不可用，将跳过 NodeJS 依赖安装"
    fi
    
    print_success "NodeJS 环境安装完成"
}

# 安装 Python 依赖
install_python_deps() {
    print_info "安装 Python 依赖..."
    
    # 创建虚拟环境（推荐但可选）
    if [ ! -d "venv" ]; then
        print_info "创建 Python 虚拟环境..."
        python -m venv venv
        print_success "虚拟环境创建完成"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 安装依赖包
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Python 依赖安装完成"
    else
        print_warning "requirements.txt 文件不存在，手动安装核心依赖"
        pip install pyserial paho-mqtt pyyaml colorama
        print_success "核心 Python 依赖安装完成"
    fi
}

# 安装 NodeJS 依赖
install_nodejs_deps() {
    print_info "安装 NodeJS 依赖..."
    
    if command -v npm >/dev/null 2>&1; then
        if [ -f "package.json" ]; then
            print_info "使用 package.json 安装依赖..."
            npm install || {
                print_warning "npm install 失败，尝试手动安装核心依赖"
                npm install zigbee-herdsman --save 2>/dev/null || print_warning "zigbee-herdsman 安装失败"
            }
        else
            print_info "package.json 不存在，手动安装核心依赖..."
            npm install zigbee-herdsman --save 2>/dev/null || print_warning "zigbee-herdsman 安装失败，但这不影响基本功能"
        fi
        print_success "NodeJS 依赖安装完成"
    else
        print_warning "npm 不可用，跳过 NodeJS 依赖安装"
        print_info "系统将仅使用 VID/PID 匹配方式检测 Zigbee 设备"
    fi
}

# 创建必要的目录
create_directories() {
    print_info "创建必要目录..."
    
    # 创建数据存储目录
    mkdir -p $HOME/serial_adapter_data
    
    # 在 Termux 中，使用 $HOME 而不是 /sdcard
    # 如果需要访问外部存储，需要先授权
    if [ -d "/storage/emulated/0" ]; then
        # 尝试创建外部存储目录
        mkdir -p /storage/emulated/0/serial_adapter_data 2>/dev/null || {
            print_warning "无法访问外部存储，将使用内部存储"
            print_info "如需访问外部存储，请运行: termux-setup-storage"
        }
    fi
    
    # 创建日志目录
    mkdir -p $HOME/logs/serial-detector
    
    print_success "目录创建完成"
    print_info "数据目录: $HOME/serial_adapter_data"
    print_info "日志目录: $HOME/logs/serial-detector"
}

# 设置存储权限
setup_storage_permissions() {
    print_info "设置存储权限..."
    
    # 检查是否已设置存储权限
    if [ ! -d "$HOME/storage" ]; then
        print_warning "未检测到存储权限"
        print_info "正在设置 Termux 存储访问权限..."
        
        # 设置存储权限
        termux-setup-storage
        
        print_info "存储权限设置完成"
        print_warning "您可能需要在手机上确认权限请求"
    else
        print_success "存储权限已设置"
    fi
}

# 创建配置文件
create_config_files() {
    print_info "创建配置文件..."
    
    # 创建启动脚本
    if [ ! -f "start_detection.sh" ]; then
        cat > start_detection.sh << 'EOF'
#!/bin/bash
# Termux 串口检测启动脚本

cd "$(dirname "$0")"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 设置数据存储路径（使用 Termux 内部存储）
STORAGE_PATH="$HOME/serial_adapter_data"

# 运行检测脚本
python detect_serial_adapters.py \
    --storage "$STORAGE_PATH" \
    "$@"
EOF
        chmod +x start_detection.sh
        print_success "启动脚本创建完成"
    fi
    
    # 创建 Termux 专用配置文件
    if [ ! -f "termux_config.yaml" ]; then
        cat > termux_config.yaml << EOF
# Termux 环境配置
storage:
  data_path: "$HOME/serial_adapter_data"
  log_path: "$HOME/logs/serial-detector"
  
mqtt:
  broker: "127.0.0.1"
  port: 1883
  user: "admin"
  pass: "admin"
  topic: "termux/serial/scan"
  
detection:
  scan_interval: 300  # 5分钟
  timeout: 30
  
termux:
  use_internal_storage: true
  setup_storage_on_first_run: true
EOF
        print_success "Termux 配置文件创建完成"
    fi
}

# 设置 Proot Ubuntu（可选）
setup_proot_ubuntu() {
    print_info "设置 Proot Ubuntu 环境（可选）..."
    
    read -p "是否要安装 Proot Ubuntu 环境？这将提供更完整的 Linux 功能 (y/N): " INSTALL_PROOT
    
    if [[ "$INSTALL_PROOT" =~ ^[Yy]$ ]]; then
        print_info "安装 Proot Ubuntu..."
        
        # 安装 Ubuntu 发行版
        proot-distro install ubuntu
        
        print_success "Proot Ubuntu 安装完成"
        print_info "使用命令进入 Ubuntu 环境: proot-distro login ubuntu"
        
        # 创建进入 Ubuntu 环境的脚本
        cat > enter_ubuntu.sh << 'EOF'
#!/bin/bash
# 进入 Proot Ubuntu 环境并运行串口检测

echo "正在进入 Ubuntu 环境..."
proot-distro login ubuntu -- bash -c "
    cd /root && 
    if [ ! -d 'detect_serial_adapters' ]; then
        echo '请先将项目文件复制到 Ubuntu 环境中'
        echo '或在 Ubuntu 中克隆项目：'
        echo 'git clone https://github.com/79B0Y/detect_serial_adapters.git'
    else
        cd detect_serial_adapters
        python3 detect_serial_adapters.py \$*
    fi
"
EOF
        chmod +x enter_ubuntu.sh
        print_success "Ubuntu 环境脚本创建完成"
    else
        print_info "跳过 Proot Ubuntu 安装"
    fi
}

# 安装 MQTT Broker（可选）
install_mqtt_broker() {
    print_info "设置 MQTT Broker..."
    
    read -p "是否要安装本地 MQTT Broker (Mosquitto)？(y/N): " INSTALL_MQTT
    
    if [[ "$INSTALL_MQTT" =~ ^[Yy]$ ]]; then
        print_info "安装 Mosquitto MQTT Broker..."
        
        # 在 Termux 中安装 mosquitto
        pkg install -y mosquitto
        
        # 创建配置文件
        mkdir -p $HOME/.config/mosquitto
        cat > $HOME/.config/mosquitto/mosquitto.conf << 'EOF'
# Termux Mosquitto 配置
port 1883
allow_anonymous true
persistence true
persistence_location $HOME/.config/mosquitto/data/
log_dest file $HOME/.config/mosquitto/mosquitto.log
EOF
        
        mkdir -p $HOME/.config/mosquitto/data
        
        # 创建启动脚本
        cat > start_mqtt.sh << 'EOF'
#!/bin/bash
# 启动 MQTT Broker
echo "启动 MQTT Broker..."
mosquitto -c $HOME/.config/mosquitto/mosquitto.conf -d
echo "MQTT Broker 已在后台启动 (端口 1883)"
echo "查看日志: tail -f $HOME/.config/mosquitto/mosquitto.log"
EOF
        chmod +x start_mqtt.sh
        
        print_success "MQTT Broker 安装完成"
        print_info "启动命令: ./start_mqtt.sh"
    else
        print_info "跳过 MQTT Broker 安装"
    fi
}

# 运行测试
run_tests() {
    print_info "运行安装测试..."
    
    # 激活虚拟环境
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # 测试 Python 依赖
    python -c "
try:
    import serial
    print('✅ pyserial 可用')
except ImportError:
    print('❌ pyserial 不可用')

try:
    import paho.mqtt.client
    print('✅ paho-mqtt 可用')
except ImportError:
    print('❌ paho-mqtt 不可用')

try:
    import yaml
    print('✅ pyyaml 可用')
except ImportError:
    print('❌ pyyaml 不可用')

try:
    import colorama
    print('✅ colorama 可用')
except ImportError:
    print('❌ colorama 不可用')

print('Python 依赖检查完成')
"
    
    # 测试 NodeJS 依赖
    if command -v node >/dev/null 2>&1; then
        print_info "测试 NodeJS 环境..."
        node -e "console.log('✅ NodeJS 运行正常');" 2>/dev/null || print_warning "NodeJS 测试失败"
        
        if command -v npm >/dev/null 2>&1; then
            print_info "测试 npm 包..."
            node -e "
try {
    require('zigbee-herdsman');
    console.log('✅ zigbee-herdsman 可用');
} catch (e) {
    console.log('⚠️ zigbee-herdsman 不可用，将仅使用 VID/PID 匹配');
}
" 2>/dev/null || print_info "NodeJS 模块测试完成"
        fi
    else
        print_warning "NodeJS 不可用"
    fi
    
    # 测试核心脚本
    if [ -f "detect_serial_adapters.py" ]; then
        print_info "测试主脚本..."
        python detect_serial_adapters.py --help >/dev/null 2>&1 && \
        print_success "✅ 主脚本测试通过" || \
        print_warning "⚠️ 主脚本测试失败，请检查依赖"
    else
        print_warning "主脚本不存在，请确保项目文件完整"
    fi
    
    print_success "安装测试完成"
}

# 显示使用说明
show_usage() {
    print_success "🎉 安装完成！"
    echo
    print_info "📋 使用说明："
    echo
    echo "1. 基本使用："
    echo "   ./start_detection.sh                # 运行检测"
    echo "   ./start_detection.sh --verbose      # 详细模式"
    echo
    echo "2. 手动运行："
    echo "   source venv/bin/activate             # 激活环境"
    echo "   python detect_serial_adapters.py    # 运行脚本"
    echo
    echo "3. 查看数据："
    echo "   ls $HOME/serial_adapter_data/        # 查看检测结果"
    echo "   tail -f $HOME/logs/serial-detector/  # 查看日志"
    echo
    echo "4. 连接 USB 设备："
    echo "   - 确保 Android 设备支持 OTG"
    echo "   - 连接 USB 转串口适配器"
    echo "   - 运行检测查看结果"
    echo
    
    if [ -f "start_mqtt.sh" ]; then
        echo "5. MQTT 服务："
        echo "   ./start_mqtt.sh                   # 启动 MQTT Broker"
        echo "   mosquitto_sub -t termux/serial/scan  # 监听消息"
        echo
    fi
    
    if [ -f "enter_ubuntu.sh" ]; then
        echo "6. Ubuntu 环境："
        echo "   ./enter_ubuntu.sh                 # 进入 Ubuntu 环境"
        echo
    fi
    
    print_info "📖 详细文档："
    echo "   - GitHub: https://github.com/79B0Y/detect_serial_adapters"
    echo "   - 安装指南: docs/installation.md"
    echo "   - 使用说明: docs/usage.md"
    echo
    print_warning "⚠️ 注意事项："
    echo "   - 在 Termux 中，某些功能可能受限"
    echo "   - 如需完整功能，建议使用 Proot Ubuntu 环境"
    echo "   - 确保授予 Termux 存储权限"
}

# 主安装流程
main() {
    echo "🔍 串口适配器自动识别系统 - Termux 版本"
    echo "=================================================="
    echo
    
    check_termux_environment
    update_packages
    install_system_tools
    install_python
    install_nodejs
    install_python_deps
    install_nodejs_deps
    create_directories
    setup_storage_permissions
    create_config_files
    setup_proot_ubuntu
    install_mqtt_broker
    
    print_info "运行安装测试..."
    run_tests
    
    show_usage
    
    print_success "🎊 串口适配器自动识别系统安装完成！"
}

# 错误处理
trap 'print_error "安装过程中出现错误，请检查上面的错误信息"; exit 1' ERR

# 运行主安装流程
main "$@"
