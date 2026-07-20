#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 24: 莫尔斯电码发送器.

用蜂鸣器和 LED 发送莫尔斯电码，数码管显示当前字母。
拨码开关选择预设消息，按键开始发送。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/24_morse_code.py
"""

import time
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 莫尔斯电码表 ----
MORSE_CODE: dict[str, str] = {
    "A": ".-",    "B": "-...",  "C": "-.-.",  "D": "-..",
    "E": ".",     "F": "..-.",  "G": "--.",   "H": "....",
    "I": "..",    "J": ".---",  "K": "-.-",   "L": ".-..",
    "M": "--",    "N": "-.",    "O": "---",   "P": ".--.",
    "Q": "--.-",  "R": ".-.",   "S": "...",   "T": "-",
    "U": "..-",   "V": "...-",  "W": ".--",   "X": "-..-",
    "Y": "-.--",  "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--",
    "4": "....-", "5": ".....", "6": "-....", "7": "--...",
    "8": "---..", "9": "----.",
    " ": "/",
}

# ---- 预设消息 ----
MESSAGES: list[tuple[str, str]] = [
    ("M1", "SOS"),
    ("M2", "HELLO"),
    ("M3", "SAKS"),
    ("M4", "RASPBERRY PI"),
]

# 时间常量 (秒)
DOT_DURATION: float = 0.08
DASH_DURATION: float = DOT_DURATION * 3
SYMBOL_GAP: float = DOT_DURATION
LETTER_GAP: float = DOT_DURATION * 3
WORD_GAP: float = DOT_DURATION * 7

current_msg_idx: int = 0
beep_requested: bool = False
sending: bool = False


def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关切换消息 / 发送."""
    global current_msg_idx, beep_requested, sending
    if not status:
        return
    if pin == SAKSPins.TACT_RIGHT:
        current_msg_idx = (current_msg_idx + 1) % len(MESSAGES)
    elif pin == SAKSPins.TACT_LEFT:
        if not sending:
            sending = True
    beep_requested = True


def send_morse(saks: SAKSHAT, message: str) -> None:
    """发送莫尔斯电码.

    Args:
        saks: SAKS 实例.
        message: 要发送的消息.
    """
    for ch in message.upper():
        if ch not in MORSE_CODE:
            continue

        code = MORSE_CODE[ch]

        # 数码管显示当前字符
        if ch == " ":
            saks.digital_display.show("____")
        else:
            saks.digital_display.show_char(0, ch)

        # 发送符号
        for symbol in code:
            if symbol == ".":
                saks.buzzer.on()
                saks.ledrow.on_for_index(0)
                time.sleep(DOT_DURATION)
                saks.buzzer.off()
                saks.ledrow.off()
            elif symbol == "-":
                saks.buzzer.on()
                saks.ledrow.on_for_index(0)
                time.sleep(DASH_DURATION)
                saks.buzzer.off()
                saks.ledrow.off()
            elif symbol == "/":
                time.sleep(WORD_GAP - SYMBOL_GAP)
                continue
            time.sleep(SYMBOL_GAP)

        # 字母间间隔
        time.sleep(LETTER_GAP - SYMBOL_GAP)


def main() -> None:
    """主函数."""
    global current_msg_idx, beep_requested, sending

    print("=" * 58)
    print("  SAKS SDK 示例 24: 莫尔斯电码发送器")
    print("=" * 58)
    print()
    print("  预设消息:")
    for code, msg in MESSAGES:
        print(f"    {code}: {msg}")
    print()
    print("  操作说明:")
    print("    右键 (TACT_RIGHT): 切换消息")
    print("    左键 (TACT_LEFT):  发送当前消息")
    print("    拨码开关 S1: 速度 (ON=快, OFF=慢)")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()
    saks.tact_event_handler = on_tact_event

    try:
        code, msg = MESSAGES[current_msg_idx]
        saks.digital_display.show(code)

        while True:
            if beep_requested:
                code, msg = MESSAGES[current_msg_idx]
                saks.digital_display.show(code)
                beep_requested = False

            if sending:
                global DOT_DURATION
                orig_dot = DOT_DURATION
                if saks.dip_switch.is_on[0]:
                    DOT_DURATION = 0.05  # 快速
                else:
                    DOT_DURATION = 0.10  # 慢速

                print(f"\n  发送: {msg}")
                print(f"  电码: {' '.join(MORSE_CODE.get(c, '?') for c in msg.upper())}")
                send_morse(saks, msg)
                print("  发送完毕。")
                sending = False
                saks.digital_display.show(code)
                saks.ledrow.off()

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n  发送器已停止。")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()