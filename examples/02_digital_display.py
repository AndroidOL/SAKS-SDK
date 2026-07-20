#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 02: 数码管显示.

展示 4 位数码管的各种显示效果：数字、小数点、负号、倒计时。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/02_digital_display.py
"""

import time
import sys
import signal

from sakshat import SAKSHAT


def main() -> None:
    """主函数."""
    print("=" * 50)
    print("  SAKS SDK 示例 02: 数码管显示")
    print("=" * 50)

    saks = SAKSHAT()

    print("\n显示数字 0-9...")
    saks.digital_display.show("0123")
    time.sleep(1)
    saks.digital_display.show("4567")
    time.sleep(1)
    saks.digital_display.show("89--")
    time.sleep(1)

    print("小数点演示...")
    saks.digital_display.show("1.2.3.4.")
    time.sleep(1)
    saks.digital_display.show("12.34")
    time.sleep(1)

    print("空白位演示...")
    saks.digital_display.show("###1")
    time.sleep(1)
    saks.digital_display.show("##12")
    time.sleep(1)

    print("倒计时 10 -> 0...")
    for n in range(10, -1, -1):
        saks.digital_display.show(f"##{n:02d}")
        time.sleep(0.5)

    saks.buzzer.beep(0.3)
    saks.digital_display.show("----")
    time.sleep(0.5)

    saks.digital_display.off()
    saks.cleanup()
    print("\n演示完成！")
    print("=" * 50)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()