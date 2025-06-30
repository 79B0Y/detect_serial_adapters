#!/bin/bash
# 串口适配器自动识别系统 - Ubuntu/Proot Ubuntu 专用安装脚本

set -e

echo "🚀 开始安装串口适配器自动识别系统 (Ubuntu 版本)..."

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

# 检查环境
check_environment() {
    print_info "检查 Ubuntu 环境..."
    
    if [ -f "/etc/os-release" ]; then
        . /etc/os-release
        print_info "操作系统: $NAME $VERSION"
    fi
    
    # 检查是否在 Proot 环境中
    if [ -n "$PROOT_TMP_DIR" ]; then
        print_success "检测到 Proot Ubuntu 环境"
    else
        print_info "标准 Ubuntu 环境"
    fi
    
    # 检查是否为 root 用户
    if [ "$EUID" -eq 0 ]; then
        print_success "以 root 权限运行"
    else
        print_error "请以 root 权限运行此脚本"
        echo "使用: sudo $0"
        exit 1
    fi
}

# 更新系统包
update_system() {
    print_info "更新系统包..."
    export DEBIAN_FRONTEND=noninteractive
    apt update
    apt upgrade -y
    print_success "系统包更新完成"
}

# 安装系统工具
install_system_tools() {
    print_info "安装系统工具..."
    
    apt install -y \
        curl \
        wget \
        git \
        unzip \
        tar \
        gzip \
        lsof \
        usbutils \
        build-essential \
        pkg-config
    
    print_success "系统工具安装完成"
}

# 安装 Python 环境
install_python() {
    print_info "安装 Python 环境..."
    
    # 安装 Python 和相关工具
    apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev
    
    # 检查 Python 版本
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    print_info "Python 版本: $PYTHON_VERSION"
    
    # 升级 pip
    python3 -m pip install --upgrade pip
    
    print_success "Python 环境安装完成"
}

# 安装 NodeJS 环境
install_nodejs() {
    print_info "安装 NodeJS 环境..."
    
    # 安装 NodeJS 和 npm
    apt install -y nodejs npm
    
    # 检查版本
    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    print_info "NodeJS 版本: $NODE_VERSION"
    print_info "NPM 版本: $NPM_VERSION"
    
    # 升级 npm
    npm install -g npm@latest
    
    print_success "NodeJS 环境安装完成"
}

# 安装 Python 依赖
install_python_deps() {
    print_info "安装 Python 依赖..."
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        print_info "创建 Python 虚拟环境..."
        python3 -m venv venv
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
    
    if [ -f "package.json" ]; then
        npm install
        print_success "NodeJS 依赖安装完成"
    else
        print_warning "package.json 文件不存在，手动安装核心依赖"
        
        # 创建基础 package.json
        cat > package.json << 'EOF'
{
  "name": "detect-serial-adapters",
  "version": "1.0.0",
  "description": "Serial adapter detection system",
  "main": "detect_zigbee_with_z2m.js",
  "dependencies": {
    "zigbee-herdsman": "^0.21.0"
  }
}
EOF
        
        npm install zigbee-herdsman
        print_success "核心 NodeJS 依赖安装完成"
    fi
}

# 创建必要的目录
create_directories() {
    print_info "创建必要目录..."
    
    # 创建数据存储目录
    mkdir -p /sdcard/isgbackup/serialport/
    mkdir -p /var/log/serial-detector/
    
    # 设置权限
    chmod 755 /sdcard/isgbackup/serialport/
    chmod 755 /var/log/serial-detector/
    
    print_success "目录创建完成"
    print_info "数据目录: /sdcard/isgbackup/serialport/"
    print_info "日志目录: /var/log/serial-detector/"
}

# 设置设备权限
setup_permissions() {
    print_info "设置设备权限..."
    
    # 创建 udev 规则文件
    cat > /etc/udev/rules.d/99-serial-adapters.rules << 'EOF'
# 串口适配器 udev 规则
# 为串口设备设置适当的权限

# 通用串口设备
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="067b", MODE="0666", GROUP="dialout"

# ConBee/ConBee II
SUBSYSTEM=="tty", ATTRS{idVendor}=="1cf1", ATTRS{idProduct}=="0030", MODE="0666", GROUP="dialout"

# Texas Instruments CC2531
SUBSYSTEM=="tty", ATTRS{idVendor}=="0451", ATTRS{idProduct}=="16a8", MODE="0666", GROUP="dialout"

# 所有 ttyUSB 和 ttyACM 设备
KERNEL=="ttyUSB[0-9]*", MODE="0666", GROUP="dialout"
KERNEL=="ttyACM[0-9]*", MODE="0666", GROUP="dialout"
EOF

    # 重新加载 udev 规则（如果可能）
    if command -v udevadm >/dev/null 2>&1; then
        udevadm control --reload-rules
        udevadm trigger
        print_success "udev 规则设置完成"
    else
        print_warning "udevadm 不可用，跳过 udev 规则重载"
    fi
    
    # 添加用户到 dialout 组（如果不是 root）
    if [ "$EUID" -ne 0 ]; then
        usermod -a -G dialout $(whoami) 2>/dev/null || print_warning "无法添加用户到 dialout 组"
    fi
}

# 创建启动脚本
create_startup_script() {
    print_info "创建启动脚本..."
    
    cat > start_serial_detector.sh << 'EOF'
#!/bin/bash
# Ubuntu 串口适配器检测系统启动脚本

# 进入脚本目录
cd "$(dirname "$0")"

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 设置环境变量
export PYTHONPATH="$PWD:$PYTHONPATH"

# 运行检测脚本
python3 detect_serial_adapters.py "$@"
EOF

    chmod +x start_serial_detector.sh
    print_success "启动脚本创建完成"
}

# 创建 systemd 服务
create_systemd_service() {
    print_info "创建 systemd 服务..."
    
    cat > /etc/systemd/system/serial-detector.service << EOF
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
    cat > /etc/systemd/system/serial-detector.timer << 'EOF'
[Unit]
Description=Run Serial Adapter Detection every 5 minutes
Requires=serial-detector.service

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

    if command -v systemctl >/dev/null 2>&1; then
        systemctl daemon-reload
        systemctl enable serial-detector.timer
        print_success "systemd 服务创建完成"
    else
        print_warning "systemctl 不可用，跳过 systemd 服务创建"
    fi
}

# 运行测试
run_test() {
    print_info "运行安装测试..."
    
    # 激活虚拟环境
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # 测试 Python 依赖
    if python3 -c "import serial, paho.mqtt.client, yaml, colorama; print('✅ Python 依赖检查通过')"; then
        print_success "Python 依赖测试通过"
    else
        print_error "Python 依赖测试失败"
        return 1
    fi
    
    # 测试 NodeJS 依赖
    if node -e "require('zigbee-herdsman'); console.log('✅ NodeJS 依赖检查通过')"; then
        print_success "NodeJS 依赖测试通过"
    else
        print_warning "NodeJS 依赖测试失败，请检查安装"
    fi
    
    # 测试核心脚本
    if [ -f "detect_serial_adapters.py" ]; then
        if python3 detect_serial_adapters.py --help >/dev/null 2>&1; then
            print_success "主脚本测试通过"
        else
            print_warning "主脚本测试可能有问题，请检查日志"
        fi
    else
        print_warning "detect_serial_adapters.py 不存在，请确保项目文件完整"
    fi
}

# 显示使用说明
show_usage() {
    print_success "🎉 Ubuntu 安装完成！"
    echo
    print_info "使用说明："
    echo
    echo "手动运行："
    echo "  ./start_serial_detector.sh                    # 基本检测"
    echo "  ./start_serial_detector.sh --verbose          # 详细模式"
    echo "  ./start_serial_detector.sh --mqtt-broker 192.168.1.100  # 自定义MQTT"
    echo
    echo "系统服务："
    echo "  systemctl start serial-detector.timer         # 启动定时服务"
    echo "  systemctl status serial-detector.timer        # 查看服务状态"
    echo "  systemctl stop serial-detector.timer          # 停止服务"
    echo
    echo "查看结果："
    echo "  ls /sdcard/isgbackup/serialport/              # 查看数据文件"
    echo "  tail -f /var/log/serial-detector/             # 查看日志"
    echo "  cat /sdcard/isgbackup/serialport/latest.json  # 最新结果"
    echo
    echo "配置生成："
    echo "  python3 generate_config.py --type all         # 生成所有配置"
    echo "  python3 generate_config.py --type z2m         # 生成Z2M配置"
    echo
    print_info "项目地址: https://github.com/79B0Y/detect_serial_adapters"
    print_info "文档: docs/usage.md"
}

# 主安装流程
main() {
    print_info "串口适配器自动识别系统 - Ubuntu 安装程序"
    echo "==============================================="
    
    check_environment
    update_system
    install_system_tools
    install_python
    install_nodejs
    install_python_deps
    install_nodejs_deps
    create_directories
    setup_permissions
    create_startup_script
    create_systemd_service
    
    print_info "运行安装测试..."
    run_test
    
    show_usage
    
    print_success "🎊 Ubuntu 安装完成！感谢使用串口适配器自动识别系统！"
}

# 错误处理
trap 'print_error "安装过程中出现错误，请检查上面的错误信息"; exit 1' ERR

# 运行主函数
main "$@"
