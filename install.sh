#!/bin/bash
# 串口适配器自动识别系统安装脚本
# 自动检测环境：Android Termux 或 Linux 系统

set -e

echo "🚀 开始安装串口适配器自动识别系统..."

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

# 检测运行环境
detect_environment() {
    print_info "检测运行环境..."
    
    if [ -n "$TERMUX_VERSION" ] || [ -d "/data/data/com.termux" ]; then
        ENVIRONMENT="termux"
        print_success "检测到 Termux 环境"
    elif [ -f "/etc/os-release" ] && grep -q "Ubuntu" /etc/os-release; then
        ENVIRONMENT="ubuntu"
        print_success "检测到 Ubuntu 环境"
    elif [ -f "/etc/debian_version" ]; then
        ENVIRONMENT="debian"
        print_success "检测到 Debian 环境"
    else
        ENVIRONMENT="linux"
        print_success "检测到 Linux 环境"
    fi
    
    # 检查是否有 sudo 权限
    if command -v sudo >/dev/null 2>&1 && [ "$ENVIRONMENT" != "termux" ]; then
        HAS_SUDO=true
        print_info "检测到 sudo 权限"
    else
        HAS_SUDO=false
        print_info "无 sudo 权限，将使用用户模式安装"
    fi
}

# 根据环境选择安装方式
choose_install_method() {
    case $ENVIRONMENT in
        "termux")
            print_info "使用 Termux 专用安装流程"
            install_for_termux
            ;;
        "ubuntu"|"debian"|"linux")
            if [ "$HAS_SUDO" = true ]; then
                # 检查是否以 root 运行
                if [ "$EUID" -ne 0 ]; then
                    print_error "请以 root 权限运行此脚本"
                    echo "使用: sudo $0"
                    exit 1
                fi
                print_info "使用 Linux 系统安装流程"
                install_for_linux
            else
                print_info "使用用户模式安装流程"
                install_for_user
            fi
            ;;
        *)
            print_warning "未知环境，尝试通用安装"
            install_for_user
            ;;
    esac
}

# Termux 环境安装
install_for_termux() {
    print_info "开始 Termux 环境安装..."
    
    # 调用 Termux 专用安装脚本
    if [ -f "install_termux.sh" ]; then
        print_info "使用专用 Termux 安装脚本"
        bash install_termux.sh
    else
        print_info "使用内置 Termux 安装流程"
        termux_install_builtin
    fi
}

# 内置 Termux 安装流程
termux_install_builtin() {
    # 更新包管理器
    pkg update && pkg upgrade -y
    
    # 安装基础工具
    pkg install -y python nodejs npm git curl wget
    
    # 创建虚拟环境
    python -m venv venv
    source venv/bin/activate
    
    # 安装 Python 依赖
    pip install --upgrade pip
    pip install pyserial paho-mqtt pyyaml colorama
    
    # 安装 NodeJS 依赖
    npm install zigbee-herdsman
    
    # 创建数据目录
    mkdir -p $HOME/serial_adapter_data
    mkdir -p $HOME/logs/serial-detector
    
    # 创建启动脚本
    create_termux_scripts
    
    print_success "Termux 安装完成"
}

# Linux 系统安装（需要 sudo）
install_for_linux() {
    print_info "开始 Linux 系统安装..."
    
    # 检查是否在 Proot Ubuntu 环境中
    if [ -n "$PROOT_TMP_DIR" ]; then
        print_success "检测到 Proot Ubuntu 环境"
    fi
    
    # 更新系统包
    update_system
    
    # 安装系统依赖
    install_system_tools
    install_python_deps
    install_nodejs_deps
    
    # 创建目录和设置权限
    create_directories
    setup_permissions
    create_start_script
    create_systemd_service
    
    # 运行测试
    run_test
    
    print_success "Linux 系统安装完成"
}

# 用户模式安装（无 sudo）
install_for_user() {
    print_info "开始用户模式安装..."
    
    # 检查必要命令
    check_user_requirements
    
    # 创建用户目录
    mkdir -p $HOME/.local/bin
    mkdir -p $HOME/.local/share/serial-detector
    mkdir -p $HOME/.config/serial-detector
    
    # 安装 Python 依赖（用户模式）
    pip install --user pyserial paho-mqtt pyyaml colorama
    
    # 安装 NodeJS 依赖（如果可能）
    if command -v npm >/dev/null 2>&1; then
        npm install zigbee-herdsman
    else
        print_warning "npm 不可用，跳过 NodeJS 依赖安装"
    fi
    
    # 创建启动脚本
    create_user_scripts
    
    print_success "用户模式安装完成"
}

# 创建 Termux 脚本
create_termux_scripts() {
    cat > start_detection.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
if [ -d "venv" ]; then
    source venv/bin/activate
fi
python detect_serial_adapters.py \
    --storage "$HOME/serial_adapter_data" \
    "$@"
EOF
    chmod +x start_detection.sh
    
    print_success "Termux 启动脚本创建完成"
}

# 创建用户模式脚本
create_user_scripts() {
    cat > start_detection.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
if [ -d "venv" ]; then
    source venv/bin/activate
fi
python3 detect_serial_adapters.py \
    --storage "$HOME/.local/share/serial-detector" \
    "$@"
EOF
    chmod +x start_detection.sh
    
    print_success "用户模式启动脚本创建完成"
}

# 检查用户模式要求
check_user_requirements() {
    local missing_tools=()
    
    if ! command -v python3 &> /dev/null; then
        missing_tools+=("python3")
    fi
    
    if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
        missing_tools+=("pip")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "缺少以下必要工具: ${missing_tools[*]}"
        print_info "请先安装这些工具或使用包管理器"
        exit 1
    fi
}

# 原有的 Linux 安装函数（保持不变）
update_system() {
    print_info "更新系统包..."
    apt update
    apt upgrade -y
    print_success "系统包更新完成"
}

install_system_tools() {
    print_info "安装系统工具..."
    apt install -y \
        curl \
        wget \
        git \
        udev \
        usbutils \
        lsof \
        socat \
        screen \
        tmux
    print_success "系统工具安装完成"
}

install_python_deps() {
    print_info "安装 Python 依赖..."
    apt install -y python3 python3-pip python3-venv
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "创建 Python 虚拟环境"
    fi
    
    source venv/bin/activate
    pip install --upgrade pip
    pip install pyserial paho-mqtt pyyaml colorama
    print_success "Python 依赖安装完成"
}

install_nodejs_deps() {
    print_info "安装 NodeJS 依赖..."
    apt install -y nodejs npm
    
    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    print_info "NodeJS 版本: $NODE_VERSION"
    print_info "NPM 版本: $NPM_VERSION"
    
    npm install zigbee-herdsman
    print_success "NodeJS 依赖安装完成"
}

create_directories() {
    print_info "创建必要目录..."
    mkdir -p /sdcard/isgbackup/serialport/
    mkdir -p /var/log/serial-detector/
    chmod 755 /sdcard/isgbackup/serialport/
    chmod 755 /var/log/serial-detector/
    print_success "目录创建完成"
}

setup_permissions() {
    print_info "设置设备权限..."
    
    cat > /etc/udev/rules.d/99-serial-adapters.rules << 'EOF'
# 串口适配器 udev 规则
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="067b", MODE="0666", GROUP="dialout"
KERNEL=="ttyUSB[0-9]*", MODE="0666", GROUP="dialout"
KERNEL=="ttyACM[0-9]*", MODE="0666", GROUP="dialout"
EOF

    if command -v udevadm >/dev/null 2>&1; then
        udevadm control --reload-rules
        udevadm trigger
        print_success "udev 规则设置完成"
    else
        print_warning "udevadm 不可用，跳过 udev 规则设置"
    fi
    
    if id -nG | grep -qw dialout; then
        print_success "用户已在 dialout 组中"
    else
        usermod -a -G dialout $(whoami) 2>/dev/null || print_warning "无法添加用户到 dialout 组"
    fi
}

create_start_script() {
    cat > start_serial_detector.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
if [ -d "venv" ]; then
    source venv/bin/activate
fi
export PYTHONPATH="$PWD:$PYTHONPATH"
python3 detect_serial_adapters.py "$@"
EOF

    chmod +x start_serial_detector.sh
    print_success "启动脚本创建完成"
}

create_systemd_service() {
    if command -v systemctl >/dev/null 2>&1; then
        print_info "创建 systemd 服务..."
        
        cat > /etc/systemd/system/serial-detector.service << EOF
[Unit]
Description=Serial Adapter Auto Detection Service
After=network.target

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

        systemctl daemon-reload
        systemctl enable serial-detector.timer
        print_success "systemd 服务创建完成"
    else
        print_warning "systemctl 不可用，跳过 systemd 服务创建"
    fi
}

run_test() {
    print_info "运行安装测试..."
    
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    if python3 -c "import serial, paho.mqtt.client, yaml, colorama; print('Python 依赖检查通过')"; then
        print_success "Python 依赖测试通过"
    else
        print_error "Python 依赖测试失败"
        return 1
    fi
    
    if node -e "require('zigbee-herdsman'); console.log('NodeJS 依赖检查通过')"; then
        print_success "NodeJS 依赖测试通过"
    else
        print_warning "NodeJS 依赖测试失败，请检查安装"
    fi
    
    print_info "执行测试检测..."
    if python3 detect_serial_adapters.py --help >/dev/null 2>&1; then
        print_success "测试检测完成"
    else
        print_warning "测试检测可能有问题，请检查日志"
    fi
}

show_usage() {
    print_success "🎉 安装完成！"
    echo
    print_info "使用说明："
    echo
    
    case $ENVIRONMENT in
        "termux")
            echo "Termux 环境使用方法："
            echo "  ./start_detection.sh                    # 运行检测"
            echo "  ./start_detection.sh --verbose          # 详细模式"
            echo "  ls ~/serial_adapter_data/               # 查看结果"
            ;;
        *)
            echo "Linux 环境使用方法："
            echo "  ./start_serial_detector.sh              # 手动运行"
            echo "  systemctl start serial-detector.timer   # 启动定时服务"
            echo "  systemctl status serial-detector.timer  # 查看服务状态"
            echo "  tail -f /sdcard/isgbackup/serialport/serial_detect.log  # 查看日志"
            ;;
    esac
    
    echo
    echo "通用命令："
    echo "  python3 detect_serial_adapters.py --help   # 查看帮助"
    echo "  python3 generate_config.py --type all      # 生成配置"
    echo
    print_info "更多信息请查看："
    echo "  - 项目地址: https://github.com/79B0Y/detect_serial_adapters"
    echo "  - 安装文档: docs/installation.md"
    echo "  - 使用说明: docs/usage.md"
}

# 主函数
main() {
    print_info "串口适配器自动识别系统安装程序"
    echo "================================================"
    
    detect_environment
    choose_install_method
    show_usage
    
    print_success "🎊 安装完成！感谢使用串口适配器自动识别系统！"
}

# 错误处理
handle_error() {
    print_error "安装过程中出现错误"
    print_info "错误信息请查看上方输出"
    print_info "如需帮助，请访问: https://github.com/79B0Y/detect_serial_adapters/issues"
    exit 1
}

trap handle_error ERR

# 运行主函数
main "$@"#!/bin/bash
# 串口适配器自动识别系统安装脚本
# 适用于 Android Termux + Proot Ubuntu 环境

set -e

echo "🚀 开始安装串口适配器自动识别系统..."

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

# 检查是否在 Proot Ubuntu 环境中
check_environment() {
    print_info "检查运行环境..."
    
    if [ ! -f "/etc/os-release" ]; then
        print_error "无法检测操作系统信息"
        exit 1
    fi
    
    if grep -q "Ubuntu" /etc/os-release; then
        print_success "检测到 Ubuntu 环境"
    else
        print_warning "非 Ubuntu 环境，可能需要调整安装过程"
    fi
    
    if [ -n "$PROOT_TMP_DIR" ] || [ -n "$TERMUX_VERSION" ]; then
        print_success "检测到 Termux/Proot 环境"
    else
        print_warning "未检测到 Termux 环境，请确认运行环境"
    fi
}

# 更新系统包
update_system() {
    print_info "更新系统包..."
    apt update
    apt upgrade -y
    print_success "系统包更新完成"
}

# 安装 Python 依赖
install_python_deps() {
    print_info "安装 Python 依赖..."
    
    # 安装 Python 和 pip
    apt install -y python3 python3-pip python3-venv
    
    # 创建虚拟环境（可选）
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "创建 Python 虚拟环境"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级 pip
    pip install --upgrade pip
    
    # 安装必要的 Python 包
    pip install pyserial paho-mqtt pyyaml colorama
    
    print_success "Python 依赖安装完成"
}

# 安装 NodeJS 和依赖
install_nodejs_deps() {
    print_info "安装 NodeJS 依赖..."
    
    # 安装 NodeJS 和 npm
    apt install -y nodejs npm
    
    # 检查版本
    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    print_info "NodeJS 版本: $NODE_VERSION"
    print_info "NPM 版本: $NPM_VERSION"
    
    # 安装 zigbee-herdsman
    print_info "安装 zigbee-herdsman..."
    npm install zigbee-herdsman
    
    print_success "NodeJS 依赖安装完成"
}

# 安装系统工具
install_system_tools() {
    print_info "安装系统工具..."
    
    # 安装必要的系统工具
    apt install -y \
        curl \
        wget \
        git \
        udev \
        usbutils \
        lsof \
        socat \
        screen \
        tmux
    
    print_success "系统工具安装完成"
}

# 创建必要的目录
create_directories() {
    print_info "创建必要目录..."
    
    # 创建存储目录
    mkdir -p /sdcard/isgbackup/serialport/
    
    # 创建日志目录
    mkdir -p /var/log/serial-detector/
    
    # 设置权限
    chmod 755 /sdcard/isgbackup/serialport/
    chmod 755 /var/log/serial-detector/
    
    print_success "目录创建完成"
}

# 设置权限和 udev 规则
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

    # 重新加载 udev 规则
    if command -v udevadm >/dev/null 2>&1; then
        udevadm control --reload-rules
        udevadm trigger
        print_success "udev 规则设置完成"
    else
        print_warning "udevadm 不可用，跳过 udev 规则设置"
    fi
    
    # 将当前用户添加到 dialout 组
    if id -nG | grep -qw dialout; then
        print_success "用户已在 dialout 组中"
    else
        usermod -a -G dialout $(whoami) 2>/dev/null || print_warning "无法添加用户到 dialout 组"
    fi
}

# 创建启动脚本
create_start_script() {
    print_info "创建启动脚本..."
    
    cat > start_serial_detector.sh << 'EOF'
#!/bin/bash
# 串口适配器检测系统启动脚本

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

# 创建 systemd 服务（可选）
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
    print_info "运行测试..."
    
    # 激活虚拟环境
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # 测试 Python 脚本
    if python3 -c "import serial, paho.mqtt.client, yaml, colorama; print('Python 依赖检查通过')"; then
        print_success "Python 依赖测试通过"
    else
        print_error "Python 依赖测试失败"
        return 1
    fi
    
    # 测试 NodeJS 脚本
    if node -e "require('zigbee-herdsman'); console.log('NodeJS 依赖检查通过')"; then
        print_success "NodeJS 依赖测试通过"
    else
        print_error "NodeJS 依赖测试失败"
        return 1
    fi
    
    # 运行一次检测（测试模式）
    print_info "执行测试检测..."
    if python3 detect_serial_adapters.py --verbose; then
        print_success "测试检测完成"
    else
        print_warning "测试检测可能有警告，请检查日志"
    fi
}

# 显示使用说明
show_usage() {
    print_info "安装完成！使用说明："
    echo
    echo "手动运行："
    echo "  ./start_serial_detector.sh"
    echo
    echo "带参数运行："
    echo "  ./start_serial_detector.sh --verbose"
    echo "  ./start_serial_detector.sh --mqtt-broker 192.168.1.100"
    echo
    echo "启动定时服务："
    echo "  systemctl start serial-detector.timer"
    echo
    echo "查看日志："
    echo "  tail -f /sdcard/isgbackup/serialport/serial_detect.log"
    echo
    echo "配置文件："
    echo "  zigbee_known.yaml - Zigbee 设备库"
    echo
    print_success "系统安装完成！"
}

# 主安装流程
main() {
    print_info "开始安装串口适配器自动识别系统"
    
    check_environment
    update_system
    install_system_tools
    install_python_deps
    install_nodejs_deps
    create_directories
    setup_permissions
    create_start_script
    create_systemd_service
    
    print_success "安装流程完成，开始测试..."
    
    if run_test; then
        show_usage
    else
        print_error "测试失败，请检查安装过程"
        exit 1
    fi
}

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then
    print_error "请以 root 权限运行此脚本"
    echo "使用: sudo $0"
    exit 1
fi

# 运行主安装流程
main "$@"
