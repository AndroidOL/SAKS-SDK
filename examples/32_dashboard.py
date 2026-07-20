#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 32: 环境监测仪表盘.

综合展示所有外设功能:
  数码管: 温度 + CPU 占用率交替显示
  LED: 温度柱状图 + CPU 占用率柱状图
  蜂鸣器: 高温报警
  拨码开关: 切换显示模式
  轻触开关: 手动切换通道

硬件要求: 树莓派 + SAKS 扩展板 + DS18B20 (可选)
运行方式: python3 examples/32_dashboard.py
"""

import time
import sys
import signal
import subprocess

from sakshat import SAKSHAT, SAKSPins

# ---- 显示模式 ----
MODE_TEMP: int = 0
MODE_CPU: int = 1
MODE_AUTO: int = 2


def get_cpu_usage() -> float:
    """读取 CPU 使用率 (%)"""
    try:
        result = subprocess.run(
            ["top", "-bn1"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.split("\n"):
            if "Cpu(s)" in line:
                # 格式: %Cpu(s):  5.2 us, ...
                parts = line.split(",")
                for p in parts:
                    if "id" in p:
                        idle = float(p.strip().split()[0])
                        return 100.0 - idle
        return 50.0
    except Exception:
        return 50.0


def temp_to_leds(temp: float, t_min: float, t_max: float) -> list[bool]:
    """温度映射到 8 LED."""
    clamped = max(t_min, min(t_max, temp))
    ratio = (clamped - t_min) / (t_max - t_min)
    lit = int(round(ratio * 8))
    return [True if i < lit else False for i in range(8)]


def beep_alarm(saks: SAKSHAT, temp: float) -> None:
    """高温报警."""
    if temp > 70:
        saks.buzzer.beep(0.2)
        time.sleep(0.1)
        saks.buzzer.beep(0.2)
    elif temp > 60:
        saks.buzzer.beep(0.1)


def main() -> None:
    """主函数."""
    print("=" * 58)
    print("  SAKS SDK 示例 32: 环境监测仪表盘")
    print("=" * 58)
    print()
    print("  显示内容:")
    print("    数码管: 温度 (°C) | CPU 占用率 (%)")
    print("    LED: 柱状图指示数值")
    print("    蜂鸣: 高温报警 (>60°C)")
    print()
    print("  操作说明:")
    print("    右键 (TACT_RIGHT): 切换显示通道")
    print("    左键 (TACT_LEFT):  自动切换模式")
    print("    拨码开关: 切换显示模式")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()

    has_sensor = saks.ds18b20.is_exist
    if not has_sensor:
        print("  [提示] 未检测到 DS18B20，仅显示 CPU 数据")
        print()

    digit_codes = {
        0: 0x3F, 1: 0x06, 2: 0x5B, 3: 0x4F, 4: 0x66,
        5: 0x6D, 6: 0x7D, 7: 0x07, 8: 0x7F, 9: 0x6F,
    }

    current_mode = MODE_AUTO
    last_switch = time.monotonic()
    switch_interval = 3.0
    last_alarm = 0.0

    try:
        while True:
            # 读取传感器
            if has_sensor:
                ambient_temp = saks.ds18b20.temperature
            else:
                ambient_temp = 0.0
            cpu_temp = get_cpu_usage()

            # 读取拨码
            dip = saks.dip_switch.is_on
            if dip[0] and dip[1]:
                current_mode = MODE_AUTO
            elif dip[0]:
                current_mode = MODE_TEMP
            elif dip[1]:
                current_mode = MODE_CPU

            now = time.monotonic()

            if current_mode == MODE_AUTO and now - last_switch >= switch_interval:
                current_mode = MODE_CPU if current_mode == MODE_TEMP else MODE_TEMP
                last_switch = now

            # 显示
            if current_mode == MODE_TEMP:
                if has_sensor:
                    # 格式: T12.3
                    temp = ambient_temp
                    if temp < -9.9:
                        temp = -9.9
                    elif temp > 99.9:
                        temp = 99.9
                    abs_t = abs(temp)
                    int_part = int(abs_t)
                    dec_part = int(round(abs_t - int_part, 1) * 10)

                    codes = [
                        digit_codes.get(int_part // 10, 0x00),
                        digit_codes.get(int_part % 10, 0x00) | 0x80,
                        digit_codes.get(dec_part, 0x00),
                        0x39,  # "C"
                    ]
                    saks.digital_display.show_raw(codes)
                    saks.ledrow.set_row(temp_to_leds(temp, 0, 50))

                    # 高温报警
                    if now - last_alarm > 5.0:
                        beep_alarm(saks, temp)
                        last_alarm = now
                else:
                    saks.digital_display.show("----")
                    saks.ledrow.off()

            elif current_mode == MODE_CPU:
                # 格式: U45.2
                usage = cpu_temp
                if usage > 99.9:
                    usage = 99.9
                int_part = int(usage)
                dec_part = int(round(usage - int_part, 1) * 10)

                codes = [
                    digit_codes.get(int_part // 10, 0x00),
                    digit_codes.get(int_part % 10, 0x00) | 0x80,
                    digit_codes.get(dec_part, 0x00),
                    0x3E,  # "U"
                ]
                saks.digital_display.show_raw(codes)
                saks.ledrow.set_row(temp_to_leds(usage, 0, 100))

            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n\n  仪表盘已停止。")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()