#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 31: 幸运大转盘.

LED 快速旋转形成转盘效果，按键停止后显示中奖结果。
数码管显示最终数值，蜂鸣器配合音效。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/31_lucky_wheel.py
"""

import time
import random
import sys
import signal
import math

from sakshat import SAKSHAT, SAKSPins

# 奖品定义
PRIZES: list[tuple[str, int, int]] = [
    ("一等奖", 0, 0),    # 停在第 0 个 LED
    ("二等奖", 2, 1),
    ("三等奖", 4, 2),
    ("参与奖", 6, 3),
    ("一等奖", 0, 0),
    ("二等奖", 2, 1),
    ("三等奖", 4, 2),
    ("参与奖", 6, 3),
]

spinning: bool = False
result: int = -1


def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关启动/停止转盘."""
    global spinning
    if not status:
        return
    spinning = not spinning


def spin_wheel(saks: SAKSHAT) -> int:
    """转盘旋转动画，返回停止位置.

    LED 快速旋转，逐渐减速后停止。

    Args:
        saks: SAKS 实例.

    Returns:
        停止的 LED 索引 (0-7).
    """
    # 预选一个结果
    target = random.randint(0, 7)
    total_steps = random.randint(30, 50)

    for step in range(total_steps):
        # 减速曲线: 越往后越慢
        progress = step / total_steps
        delay = 0.02 + 0.15 * progress * progress

        # 当前位置
        pos = step % 8

        row = [False] * 8
        row[pos] = True
        saks.ledrow.set_row(row)

        # 蜂鸣
        if step < total_steps - 1:
            saks.buzzer.beep(0.005)

        time.sleep(delay)

    # 最终停在目标位置
    row = [False] * 8
    row[target] = True
    saks.ledrow.set_row(row)

    return target


def celebrate(saks: SAKSHAT, prize_name: str) -> None:
    """中奖庆祝动画."""
    for _ in range(4):
        saks.ledrow.on()
        saks.buzzer.beep(0.08)
        time.sleep(0.12)
        saks.ledrow.off()
        time.sleep(0.12)
    saks.digital_display.show("WIN!")


def main() -> None:
    """主函数."""
    global spinning, result

    print("=" * 58)
    print("  SAKS SDK 示例 31: 幸运大转盘")
    print("=" * 58)
    print()
    print("  操作说明:")
    print("    右键 (TACT_RIGHT): 启动转盘")
    print("    左键 (TACT_LEFT):  停止转盘")
    print("    5 秒内未操作自动停止")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()
    saks.tact_event_handler = on_tact_event

    try:
        saks.digital_display.show("READ")

        while True:
            # 等待启动
            print("  按右键启动转盘...")
            while not spinning:
                # 待机动画: LED 呼吸
                for i in range(8):
                    row = [False] * 8
                    row[i] = True
                    saks.ledrow.set_row(row)
                    time.sleep(0.08)
                for i in range(6, 0, -1):
                    row = [False] * 8
                    row[i] = True
                    saks.ledrow.set_row(row)
                    time.sleep(0.08)

            saks.digital_display.show("----")
            print("  转盘旋转中...")

            # 旋转动画
            start_time = time.monotonic()
            auto_timeout = 5.0  # 自动停止时间

            target = random.randint(0, 7)
            step = 0
            while spinning:
                step += 1
                pos = step % 8
                elapsed = time.monotonic() - start_time

                # 自动停止
                if elapsed > auto_timeout:
                    spinning = False
                    break

                row = [False] * 8
                row[pos] = True
                saks.ledrow.set_row(row)
                saks.buzzer.beep(0.005)
                time.sleep(0.04)

            # 减速停止
            result = spin_wheel(saks)
            prize_name = PRIZES[result][0]

            saks.digital_display.show(f"P{result}")
            celebrate(saks, prize_name)

            print(f"  🎉 结果: {prize_name}！(LED #{result})")
            time.sleep(2)

            saks.digital_display.show("READ")
            saks.ledrow.off()

    except KeyboardInterrupt:
        print("\n\n  转盘已停止。")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()