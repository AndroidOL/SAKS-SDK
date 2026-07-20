#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 28: 数字时钟.

在数码管上显示当前系统时间 (HH:MM)，LED 指示秒数。
按键切换 12/24 小时制，拨码开关开启秒闪烁。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/28_digital_clock.py
"""

import time
import sys
import signal
from datetime import datetime

from sakshat import SAKSHAT, SAKSPins

# ---- 全局状态 ----
hour_24: bool = True
show_seconds: bool = True
beep_requested: bool = False


def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关切换 12/24 小时制."""
    global hour_24, beep_requested
    if not status:
        return
    if pin == SAKSPins.TACT_RIGHT:
        hour_24 = not hour_24
    elif pin == SAKSPins.TACT_LEFT:
        global show_seconds
        show_seconds = not show_seconds
    beep_requested = True


def main() -> None:
    """主函数."""
    global hour_24, beep_requested

    print("=" * 58)
    print("  SAKS SDK 示例 28: 数字时钟")
    print("=" * 58)
    print()
    print("  操作说明:")
    print("    右键 (TACT_RIGHT): 切换 12/24 小时制")
    print("    左键 (TACT_LEFT):  切换秒闪烁")
    print("    拨码开关 S1: 静音模式 (ON=静音)")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()
    saks.tact_event_handler = on_tact_event

    # 段码: 数字 0-9
    digit_codes = {
        0: 0x3F, 1: 0x06, 2: 0x5B, 3: 0x4F, 4: 0x66,
        5: 0x6D, 6: 0x7D, 7: 0x07, 8: 0x7F, 9: 0x6F,
    }

    last_second = -1
    colon_on = True

    try:
        while True:
            if beep_requested:
                saks.buzzer.beep(0.03)
                beep_requested = False

            now = datetime.now()
            mute = saks.dip_switch.is_on[0]

            # 整点报时
            if not mute and now.minute == 0 and now.second == 0:
                saks.buzzer.beep(0.1)
                time.sleep(0.1)
                saks.buzzer.beep(0.1)

            # 秒变化时
            if now.second != last_second:
                last_second = now.second
                colon_on = not colon_on

                # 小时处理
                if hour_24:
                    h = now.hour
                else:
                    h = now.hour % 12
                    if h == 0:
                        h = 12

                m = now.minute

                # 构造段码: HH:MM
                # 第 0 位: 小时的十位
                h_ten = h // 10
                # 第 1 位: 小时的个位 + 冒号
                h_one = h % 10
                # 第 2 位: 分钟的十位
                m_ten = m // 10
                # 第 3 位: 分钟的个位
                m_one = m % 10

                codes = [
                    digit_codes.get(h_ten, 0x00),
                    digit_codes.get(h_one, 0x00) | (0x80 if colon_on else 0x00),
                    digit_codes.get(m_ten, 0x00),
                    digit_codes.get(m_one, 0x00),
                ]

                saks.digital_display.show_raw(codes)

                # LED 指示秒 (0-7 对应 0-60秒)
                if show_seconds:
                    sec_led = int(now.second / 60.0 * 8) % 8
                    row = [False] * 8
                    row[sec_led] = True
                    saks.ledrow.set_row(row)
                else:
                    saks.ledrow.off()

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\n  时钟已停止。")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()