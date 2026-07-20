#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 05: CPU 温度监控与报警.

读取树莓派 CPU/GPU 温度，在数码管上显示，温度过高时 LED 闪烁和蜂鸣器报警。
通过拨码开关切换显示来源 (CPU/GPU/DS18B20)。

硬件要求: 树莓派 + SAKS 扩展板 + DS18B20 (可选)
运行方式: python3 examples/05_cpu_temperature_alarm.py
"""

import subprocess
import time
import sys
import signal

from sakshat import SAKSHAT

ALARM_TEMP: float = 50.0
WARNING_TEMP: float = 45.0


def get_cpu_temperature() -> float:
    """读取树莓派 CPU 温度.

    Returns:
        CPU 温度 (摄氏度)，读取失败返回 -1.0.
    """
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return float(f.read().strip()) / 1000.0
    except (OSError, ValueError):
        return -1.0


def get_gpu_temperature() -> float:
    """读取树莓派 GPU 温度.

    Returns:
        GPU 温度 (摄氏度)，读取失败返回 -1.0.
    """
    try:
        result = subprocess.run(
            ["/opt/vc/bin/vcgencmd", "measure_temp"],
            capture_output=True, text=True, timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return float(
                result.stdout.replace("temp=", "").replace("'C", "").strip()
            )
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        pass
    return -1.0


def main() -> None:
    """主函数."""
    print("=" * 50)
    print("  SAKS SDK 示例 05: CPU 温度监控与报警")
    print("=" * 50)

    saks = SAKSHAT()

    display_mode: int = 0

    print(f"\n警告温度: {WARNING_TEMP}°C | 报警温度: {ALARM_TEMP}°C")
    print("按 Ctrl+C 退出\n")

    try:
        while True:
            cpu_temp = get_cpu_temperature()
            gpu_temp = get_gpu_temperature()

            if display_mode == 0:
                temp, label = cpu_temp, "CPU"
            elif display_mode == 1:
                temp, label = gpu_temp, "GPU"
            else:
                temp, label = saks.ds18b20.temperature, "EXT"

            if temp > 0:
                saks.digital_display.show(f"{temp:.1f}")
                print(f"  [{label}] {temp:.1f}°C", end="")

                if temp >= ALARM_TEMP:
                    print(" [高温报警!]", end="")
                    saks.ledrow.set_row([True] * 8)
                    saks.buzzer.beep(0.1)
                    time.sleep(0.1)
                    saks.ledrow.off()
                elif temp >= WARNING_TEMP:
                    print(" [警告]", end="")
                    saks.ledrow.set_row([True, False, True, False, True, False, True, False])
                    time.sleep(0.2)
                    saks.ledrow.set_row([False, True, False, True, False, True, False, True])
                    time.sleep(0.2)
                    saks.ledrow.off()
                print()

                dip = saks.dip_switch.is_on
                if dip[0] and not dip[1]:
                    display_mode = 0
                elif not dip[0] and dip[1]:
                    display_mode = 1
                elif dip[0] and dip[1]:
                    display_mode = 2
            else:
                print(f"  [错误] 无法读取 {label} 温度")
                saks.digital_display.show("----")
                time.sleep(1)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n监控已停止。")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("资源已清理。")
        print("=" * 50)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()