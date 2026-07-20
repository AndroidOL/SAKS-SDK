#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 23: 呼吸灯 - LED 渐亮渐灭效果.

通过 PWM 控制 LED 亮度，实现呼吸灯效果。支持多种模式：
锥形、波浪、交替、心跳。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/23_breathing_led.py
"""

import time
import math
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 模式定义 ----
PATTERN_NAMES: dict[int, str] = {
    0: "B1",  # 锥形
    1: "B2",  # 波浪
    2: "B3",  # 交替
    3: "B4",  # 心跳
}

current_pattern: int = 0
beep_requested: bool = False


def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关切换模式."""
    global current_pattern, beep_requested
    if not status:
        return
    if pin == SAKSPins.TACT_RIGHT:
        current_pattern = (current_pattern + 1) % len(PATTERN_NAMES)
    elif pin == SAKSPins.TACT_LEFT:
        current_pattern = (current_pattern - 1) % len(PATTERN_NAMES)
    beep_requested = True


def get_brightness_wave(step: int, total: int, led_idx: int, num_leds: int) -> float:
    """生成锥形亮度分布.

    中心 LED 最亮，向两侧递减。

    Args:
        step: 当前步数.
        total: 总步数.
        led_idx: LED 索引.
        num_leds: LED 总数.

    Returns:
        亮度值 (0.0-1.0).
    """
    center = num_leds / 2 - 0.5
    dist = abs(led_idx - center) / center
    base = math.sin(step / total * math.pi)
    return base * (1.0 - dist)


def get_brightness_alternating(step: int, total: int, led_idx: int, num_leds: int) -> float:
    """交替呼吸: 奇数位和偶数位交替亮灭."""
    phase = step / total * math.pi
    if led_idx % 2 == 0:
        return math.sin(phase)
    else:
        return math.sin(phase + math.pi)


def get_brightness_heartbeat(step: int, total: int, led_idx: int, num_leds: int) -> float:
    """心跳模式: 两下快速脉冲 + 停顿."""
    cycle = (step / total) % 1.0
    if cycle < 0.15:
        return 1.0
    elif cycle < 0.25:
        return 0.0
    elif cycle < 0.40:
        return 1.0
    elif cycle < 0.50:
        return 0.0
    else:
        return 0.0


def main() -> None:
    """主函数."""
    global current_pattern, beep_requested

    print("=" * 58)
    print("  SAKS SDK 示例 23: 呼吸灯")
    print("=" * 58)
    print()
    print("  模式:")
    print("    B1 - 锥形: 中心最亮，向两侧渐暗")
    print("    B2 - 波浪: LED 依次亮灭形成波浪")
    print("    B3 - 交替: 奇偶位交替呼吸")
    print("    B4 - 心跳: 模拟心跳脉冲")
    print()
    print("  操作说明:")
    print("    右键 (TACT_RIGHT): 下一个模式")
    print("    左键 (TACT_LEFT):  上一个模式")
    print("    拨码开关 S1: 速度 (ON=快, OFF=慢)")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()
    saks.tact_event_handler = on_tact_event

    try:
        pattern_name = PATTERN_NAMES[current_pattern]
        saks.digital_display.show(pattern_name)

        while True:
            if beep_requested:
                saks.buzzer.beep(0.03)
                saks.digital_display.show(PATTERN_NAMES[current_pattern])
                beep_requested = False

            fast = saks.dip_switch.is_on[0]
            steps = 40 if fast else 60
            delay = 0.015 if fast else 0.025

            for step in range(steps):
                if current_pattern == 0:
                    # 锥形呼吸
                    brightness = math.sin(step / steps * math.pi)
                    row = [brightness > 0.3] * 8
                    # 中心亮，两侧暗
                    for i in range(8):
                        row[i] = (get_brightness_wave(step, steps, i, 8) > 0.15)
                    saks.ledrow.set_row(row)

                elif current_pattern == 1:
                    # 波浪: LED 依次亮起
                    wave_pos = int(step / steps * 8 + 2) % 8
                    row = [False] * 8
                    row[wave_pos] = True
                    row[(wave_pos + 1) % 8] = True
                    saks.ledrow.set_row(row)

                elif current_pattern == 2:
                    # 交替呼吸
                    row = [False] * 8
                    for i in range(8):
                        b = get_brightness_alternating(step, steps, i, 8)
                        row[i] = b > 0.3
                    saks.ledrow.set_row(row)

                elif current_pattern == 3:
                    # 心跳
                    cycle = (step / steps) % 1.0
                    if cycle < 0.15:
                        saks.ledrow.on()
                    elif cycle < 0.25:
                        saks.ledrow.off()
                    elif cycle < 0.40:
                        saks.ledrow.on()
                    else:
                        saks.ledrow.off()

                time.sleep(delay)

    except KeyboardInterrupt:
        print("\n\n  呼吸灯已停止。")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()