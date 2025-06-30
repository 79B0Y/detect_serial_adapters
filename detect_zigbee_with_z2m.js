#!/usr/bin/env node

/**
 * Zigbee 适配器检测模块
 * 使用 zigbee-herdsman 的 autoDetectAdapter 功能
 * 被 Python 主脚本调用
 */

const path = require('path');
const fs = require('fs');

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

async function detectZigbeeAdapter(serialPort) {
    const result = {
        port: serialPort,
        isZigbee: false,
        adapterType: null,
        error: null,
        timestamp: new Date().toISOString()
    };

    try {
        const adapter = await herdsman.adapter.autoDetectAdapter(serialPort, {
            timeout: 15000,
            baudrates: [115200, 38400, 57600, 9600, 19200],
            rtscts: false
        });

        if (adapter && adapter.adapter) {
            result.isZigbee = true;
            result.adapterType = adapter.adapter.constructor.name;

            const adapterTypeMap = {
                'EzspAdapter': 'EZSP',
                'ZnpAdapter': 'ZNP', 
                'DeconzAdapter': 'deCONZ',
                'ZiGateAdapter': 'ZiGate',
                'EmberAdapter': 'Ember'
            };
            result.adapterType = adapterTypeMap[result.adapterType] || result.adapterType;

            try {
                if (adapter.adapter.getNetworkParameters) {
                    const networkInfo = await adapter.adapter.getNetworkParameters();
                    result.networkInfo = networkInfo;
                }
            } catch {
                result.networkInfo = null;
            }

            try {
                if (adapter.adapter.stop) {
                    await adapter.adapter.stop();
                }
            } catch {}
        }

    } catch (error) {
        result.error = error.message;

        if (error.message.includes('timeout')) {
            result.error = 'Detection timeout - possibly not a Zigbee adapter';
        } else if (error.message.includes('Permission denied')) {
            result.error = 'Permission denied - check device permissions';
        } else if (error.message.includes('No such file')) {
            result.error = 'Device not found';
        } else if (error.message.includes('Device or resource busy')) {
            result.error = 'Device busy - possibly in use by another process';
        }
    }

    return result;
}

async function main() {
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

setTimeout(() => {
    console.error(JSON.stringify({
        error: 'Detection timeout - process killed after 30 seconds',
        isZigbee: false
    }));
    process.exit(1);
}, 30000);

if (require.main === module) {
    main();
}

module.exports = { detectZigbeeAdapter };
