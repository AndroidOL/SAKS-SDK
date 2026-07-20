#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 30: 警报器 - 多模式警报音效.

蜂鸣器发出多种警报音效，LED 配合闪烁。
按键切换模式，拨码开关控制音量节奏。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/30_alarm_siren.py
"""

import time
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 警报模式 ----
ALARM_MODES: list[tuple[str, str]] = [
    ("A1", "警笛"),     # 频率渐变
    ("A2", "火警"),     # 急促脉冲
    ("A3", "救护"),     # 交替高低音
    ("A4", "门铃"),     # 叮咚
    ("A5", "倒计时"),   # 滴答滴答
    ("A6", "警报"),     # 持续振荡
]

current_mode: int = 0
beep_requested: bool = False
active: bool = True


def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关切换模式."""
    global current_mode, beep_requested, active
    if not status:
        return
    if pin == SAKSPins.TACT_RIGHT:
        current_mode = (current_mode + 1) % len(ALARM_MODES)
    elif pin == SAKSPins.TACT_LEFT:
        active = not active
    beep_requested = True


def play_siren(saks: SAKSHAT, fast: bool) -> None:
    """警笛: 频率从低到高再回到低."""
    from sakshat._gpio import GPIO
    duration = 0.8 if fast else 1.2
    for freq in range(400, 800, 20):
        pwm = GPIO.PWM(SAKSPins.BUZZER, freq)
        pwm.start(50)
        saks.ledrow.on()
        time.sleep(duration / 40)
        pwm.stop()
        saks.ledrow.off()
        time.sleep(0.002)
    for freq in range(800, 400, -20):
        pwm = GPIO.PWM(SAKSPins.BUZZER, freq)
        pwm.start(50)
        saks.ledrow.on()
        time.sleep(duration / 40)
        pwm.stop()
        saks.ledrow.off()
        time.sleep(0.002)


def play_fire_alarm(saks: SAKSHAT, fast: bool) -> None:
    """火警: 急促短脉冲."""
    count = 15 if fast else 10
    for i in range(count):
        saks.ledrow.on()
        saks.buzzer.beep(0.08)
        saks.ledrow.off()
        time.sleep(0.05)


def play_ambulance(saks: SAKSHAT, fast: bool) -> None:
    """救护车: 交替高低音."""
    from sakshat._gpio import GPIO
    delay = 0.3 if fast else 0.5
    for _ in range(3):
        pwm = GPIO.PWM(SAKSPins.BUZZER, 600)
        pwm.start(50)
        saks.ledrow.on()
        time.sleep(delay)
        pwm.stop()
        pwm = GPIO.PWM(SAKSPins.BUZZER, 400)
        pwm.start(50)
        saks.ledrow.off()
        time.sleep(delay)
        pwm.stop()


def play_doorbell(saks: SAKSHAT, fast: bool) -> None:
    """门铃: 叮-咚."""
    from sakshat._gpio import GPIO
    delay = 0.2 if fast else 0.35
    saks.ledrow.on()
    pwm = GPIO.PWM(SAKSPins.BUZZER, 700)
    pwm.start(50)
    time.sleep(delay)
    pwm.stop()
    time.sleep(0.1)
    saks.ledrow.off()
    time.sleep(0.1)
    saks.ledrow.on()
    pwm = GPIO.PWM(SAKSPins.BUZZER, 500)
    pwm.start(50)
    time.sleep(delay * 1.5)
    pwm.stop()
    saks.ledrow.off()


def play_countdown(saks: SAKSHAT, fast: bool) -> None:
    """倒计时: 滴答滴答."""
    count = 10
    for i in range(count, 0, -1):
        saks.digital_display.show(f"  {i:2d}")
        row = [False] * 8
        row[i % 8] = True
        saks.ledrow.set_row(row)
        saks.buzzer.beep(0.05)
        time.sleep(0.5 if fast else 0.8)
    saks.digital_display.show("GOOO")
    saks.ledrow.on()
    saks.buzzer.beep(0.5)
    saks.ledrow.off()


def play_oscillation(saks: SAKSHAT, fast: bool) -> None:
    """警报: 持续振荡."""
    from sakshat._gpio import GPIO
    delay = 0.04 if fast else 0.06
    for _ in range(15):
        for freq in [500, 600, 400, 700]:
            pwm = GPIO.PWM(SAKSPins.BUZZER, freq)
            pwm.start(50)
            saks.ledrow.on()
            time.sleep(delay)
            pwm.stop()
            saks.ledrow.off()
            time.sleep(delay * 0.5)


PLAYERS = [play_siren, play_fire_alarm, play_ambulance,
           play_doorbell, play_countdown, play_oscillation]


def main() -> None:
    """主函数."""
    global current_mode, beep_requested, active

    print("=" * 58)
    print("  SAKS SDK 示例 30: 警报器")
    print("=" * 58)
    print()
    print("  警报模式:")
    for code, name in ALARM_MODES:
        print(f"    {code}: {name}")
    print()
    print("  操作说明:")
    print("    右键 (TACT_RIGHT): 切换模式")
    print("    左键 (TACT_LEFT):  暂停/继续")
    print("    拨码开关 S1: 速度 (ON=快, OFF=慢)")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()
    saks.tact_event_handler = on_tact_event

    try:
        code, name = ALARM_MODES[current_mode]
        saks.digital_display.show(code)

        while True:
            if beep_requested:
                code, name = ALARM_MODES[current_mode]
                saks.digital_display.show(code)
                saks.buzzer.beep(0.02)
                beep_requested = False

            if active:
                fast = saks.dip_switch.is_on[0]
                print(f"  播放: {name}")
                PLAYERS[current_mode](saks, fast)
                time.sleep(0.5)
            else:
                saks.digital_display.show("PAUS")
                time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n  警报器已停止。")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()