#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 01: 基础入门.

展示 SAKS SDK 最基本的使用方式：创建 SAKS 实例、控制蜂鸣器、LED 阵列、安全退出。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/01_hello_saks.py
"""

import time
import sys
import signal

from sakshat import SAKSHAT


def main() -> None:
    """主函数."""
    print("=" * 50)
    print("  SAKS SDK 示例 01: 基础入门")
    print("=" * 50)

    saks = SAKSHAT()
    print("  初始化完成！")

    print("\n[1/4] 蜂鸣器测试...")
    saks.buzzer.beep(0.3)
    time.sleep(0.5)

    print("\n[2/4] LED 流水灯...")
    for i in range(8):
        saks.ledrow.on_for_index(i)
        time.sleep(0.1)
        saks.ledrow.off_for_index(i)
    for i in range(6, -1, -1):
        saks.ledrow.on_for_index(i)
        time.sleep(0.1)
        saks.ledrow.off_for_index(i)

    print("\n[3/4] LED 交替闪烁...")
    for _ in range(3):
        saks.ledrow.set_row([True, False, True, False, True, False, True, False])
        time.sleep(0.3)
        saks.ledrow.set_row([False, True, False, True, False, True, False, True])
        time.sleep(0.3)
    saks.ledrow.off()

    print("\n[4/4] 清理资源...")
    saks.cleanup()
    print("  完成！")
    print("=" * 50)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()