#!/usr/bin/env node

/**
 * Zigbee 适配器检测模块
 * 使用 zigbee-herdsman 的 autoDetectAdapter 功能
 * 被 Python 主脚本调用
 */

const path = require('path');
const fs = require('fs');

// 检查是否安装了 zigbee-herdsman
let herdsman;
try {
    herdsman = require('zigbee-herdsman');
} catch (error) {
    console.error(JSON.stringify({
        error: 'zigbee-herdsman not installed',
        message: 'Please install: npm install zigbee-herdsman',
        isZigbee: false
    }));
    process.exit(1);
}

/**
 * 检测指定串口是否为 Zigbee 适配器
 * @param {string} serialPort - 串口设备路径
 * @returns {Promise<Object>} 检测结果
 */
async function detectZigbeeAdapter(serialPort) {
    const result = {
        port: serialPort,
        isZigbee: false,
        adapterType: null,
        error: null,
        timestamp: new Date().toISOString()
    };

    try {
        // 使用 zigbee-herdsman 的自动检测功能
        const adapter = await herdsman.adapter.autoDetectAdapter(serialPort, {
            // 设置超时时间
            timeout: 15000,
            // 设置波特率尝试列表
            baudrates: [115200, 38400, 57600, 9600, 19200],
            // 其他选项
            rtscts: false
        });

        if (adapter && adapter.adapter) {
            result.isZigbee = true;
            result.adapterType = adapter.adapter.constructor.name;
            
            // 根据适配器类型提供更友好的名称
            const adapterTypeMap = {
                'EzspAdapter': 'EZSP',
                'ZnpAdapter': 'ZNP', 
                'DeconzAdapter': 'deCONZ',
                'ZiGateAdapter': 'ZiGate',
                'EmberAdapter': 'Ember'
            };
            
            result.adapterType = adapterTypeMap[result.adapterType] || result.adapterType;
            
            // 尝试获取更多信息
            try {
                if (adapter.adapter.getNetworkParameters) {
                    const networkInfo = await adapter.adapter.getNetworkParameters();
                    result.networkInfo = networkInfo;
                }
            } catch (networkError) {
                // 忽略网络信息获取错误
                result.networkInfo = null;
            }
            
            // 清理适配器连接
            try {
                if (adapter.adapter.stop) {
                    await adapter.adapter.stop();
                }
            } catch (stopError) {
                // 忽略停止错误
            }
        }

    } catch (error) {
        result.error = error.message;
        
        // 特定错误类型判断
        if (error.message.includes('timeout') || error.message.includes('TIMEOUT')) {
            result.error = 'Detection timeout - possibly not a Zigbee adapter';
        } else if (error.message.includes('Permission denied') || error.message.includes('EACCES')) {
            result.error = 'Permission denied - check device permissions';
        } else if (error.message.includes('No such file') || error.message.includes('ENOENT')) {
            result.error = 'Device not found';
        } else if (error.message.includes('Device or resource busy') || error.message.includes('EBUSY')) {
            result.error = 'Device busy - possibly in use by another process';
        }
    }

    return result;
}

/**
 * 主函数
 */
async function main() {
    // 获取命令行参数
    const args = process.argv.slice(2);
    
    if (args.length === 0) {
        console.error(JSON.stringify({
            error: 'No serial port specified',
            usage: 'node detect_zigbee_with_z2m.js <serial_port>',
            isZigbee: false
        }));
        process.exit(1);
    }

    const serialPort = args[0];
    
    // 检查串口设备是否存在
    if (!fs.existsSync(serialPort)) {
        console.error(JSON.stringify({
            error: `Serial port ${serialPort} does not exist`,
            isZigbee: false
        }));
        process.exit(1);
    }

    try {
        const result = await detectZigbeeAdapter(serialPort);
        console.log(JSON.stringify(result, null, 0));
        
        // 返回适当的退出代码
        process.exit(result.isZigbee ? 0 : 1);
        
    } catch (error) {
        console.error(JSON.stringify({
            error: `Unexpected error: ${error.message}`,
            isZigbee: false,
            stack: error.stack
        }));
        process.exit(1);
    }
}

// 处理未捕获的异常
process.on('uncaughtException', (error) => {
    console.error(JSON.stringify({
        error: `Uncaught exception: ${error.message}`,
        isZigbee: false,
        stack: error.stack
    }));
    process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error(JSON.stringify({
        error: `Unhandled rejection: ${reason}`,
        isZigbee: false,
        promise: promise.toString()
    }));
    process.exit(1);
});

// 设置超时保护
setTimeout(() => {
    console.error(JSON.stringify({
        error: 'Detection timeout - process killed after 30 seconds',
        isZigbee: false
    }));
    process.exit(1);
}, 30000);

// 运行主函数
if (require.main === module) {
    main();
}

module.exports = { detectZigbeeAdapter };
