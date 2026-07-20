#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 06: 综合演示.

综合展示 SAKS SDK 的所有功能：蜂鸣器音乐、LED 特效、数码管倒计时、温度显示。

硬件要求: 树莓派 + SAKS 扩展板 + DS18B20 (可选)
运行方式: python3 examples/06_full_demo.py
"""

import time
import sys
import signal

from sakshat import SAKSHAT


def demo_buzzer(saks: SAKSHAT) -> None:
    """蜂鸣器音乐演示."""
    print("\n  >> 蜂鸣器音乐...")
    notes = [(0.15, 0.05)] * 3 + [(0.30, 0.10)] + [(0.15, 0.05)] * 3 + [(0.30, 0.20)]
    for on_time, off_time in notes:
        saks.buzzer.beep(on_time)
        time.sleep(off_time)


def demo_led(saks: SAKSHAT) -> None:
    """LED 特效演示."""
    print("\n  >> LED 跑马灯...")
    for _ in range(2):
        for i in range(8):
            saks.ledrow.on_for_index(i)
            time.sleep(0.03)
            saks.ledrow.off_for_index(i)
    for i in range(8):
        saks.ledrow.on_for_index(i)
        time.sleep(0.08)
    for i in range(7, -1, -1):
        saks.ledrow.off_for_index(i)
        time.sleep(0.08)
    for _ in range(3):
        saks.ledrow.set_row([True, False, True, False, True, False, True, False])
        time.sleep(0.2)
        saks.ledrow.set_row([False, True, False, True, False, True, False, True])
        time.sleep(0.2)
    saks.ledrow.off()


def demo_countdown(saks: SAKSHAT, seconds: int = 5) -> None:
    """数码管倒计时演示."""
    print(f"\n  >> 倒计时 {seconds} 秒...")
    for n in range(seconds, -1, -1):
        saks.digital_display.show(f"{n:04d}")
        time.sleep(1)
    saks.buzzer.beep(0.5)


def demo_temperature(saks: SAKSHAT) -> None:
    """温度传感器演示."""
    print("\n  >> 温度传感器...")
    if saks.ds18b20.is_exist:
        temp = saks.ds18b20.temperature
        if temp != -128.0:
            print(f"     DS18B20: {temp:.1f}°C")
            saks.digital_display.show(f"{temp:.1f}")
            time.sleep(2)
        else:
            print("     [警告] 读取失败")
            saks.digital_display.show("----")
            time.sleep(1)
    else:
        print("     [提示] 未连接 DS18B20，跳过")
        saks.digital_display.show("----")
        time.sleep(1)


def main() -> None:
    """主函数."""
    print("=" * 50)
    print("  SAKS SDK 示例 06: 综合演示")
    print("=" * 50)

    with SAKSHAT() as saks:
        print("\n按 Ctrl+C 可随时退出\n")
        try:
            demo_buzzer(saks)
            time.sleep(0.5)
            demo_led(saks)
            time.sleep(0.5)
            demo_countdown(saks, seconds=5)
            time.sleep(0.5)
            for i in range(8):
                saks.ledrow.on_for_index(i)
                saks.digital_display.show(f"L{8 - i:03d}")
                time.sleep(0.3)
            saks.ledrow.off()
            demo_temperature(saks)
            print("\n  >> 演示结束！")
            saks.digital_display.show("END")
            for _ in range(3):
                saks.buzzer.beep(0.1)
                time.sleep(0.15)
            saks.digital_display.off()
        except KeyboardInterrupt:
            print("\n\n演示被中断。")

    print("资源已自动清理。")
    print("=" * 50)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()