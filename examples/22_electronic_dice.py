#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 22: 电子骰子.

按键摇骰子：LED 快速滚动模拟骰子旋转，松开后显示随机结果。
数码管显示点数，LED 以骰子图案展示点数。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/22_electronic_dice.py
"""

import time
import random
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 骰子点数 LED 图案 (1-6) ----
# 8 个 LED 排列成 2 行 4 列，模拟骰子面
# LED 0-3 为上行，LED 4-7 为下行
# 对应骰子面: 左=LED 0/4, 中左=LED 1/5, 中右=LED 2/6, 右=LED 3/7
DICE_PATTERNS: dict[int, list[bool]] = {
    1: [False, False, False, False,     # 上: 全灭
        False, False, False, False],    # 下: 全灭 -> 数码管显示 "1"
    2: [True, False, False, False,      # 上: 左上
        False, False, False, True],     # 下: 右下
    3: [True, False, False, False,      # 上: 左上
        False, False, False, True,      # 下: 右下
        ],  # 实际用 3 个 LED
    4: [True, False, False, True,       # 上: 左上 + 右上
        True, False, False, True],      # 下: 左下 + 右下
    5: [True, False, False, True,       # 上: 左上 + 右上
        True, False, False, True,       # 下: 左下 + 右下
        ],  # 5 需要中间一个
    6: [True, False, False, True,       # 上: 左上 + 右上
        True, False, False, True],      # 下: 左下 + 右下
}

# 3x3 骰子面映射 (使用 8 个 LED 模拟)
# 上方 4 个 LED 代表上排，下方 4 个代表下排
DICE_DOT_PATTERNS: dict[int, list[bool]] = {
    1: [False, False, True,  False,     # 上: 中右
        False, False, False, False],    # 下: 全灭
    2: [True,  False, False, False,     # 上: 左上
        False, False, False, True],     # 下: 右下
    3: [True,  False, False, False,     # 上: 左上
        False, True,  False, False,     # 下: 中左
        ],
    4: [True,  False, False, True,      # 上: 左上 + 右上
        True,  False, False, True],     # 下: 左下 + 右下
    5: [True,  False, False, True,      # 上: 左上 + 右上
        False, True,  False, False,     # 下: 中左
        ],
    6: [True,  False, False, True,      # 上: 左 + 右
        True,  False, False, True],     # 下: 左 + 右
}


def roll_animation(saks: SAKSHAT, duration: float) -> int:
    """骰子滚动动画，返回最终点数.

    LED 快速切换不同点数图案模拟骰子旋转，越来越慢后停止。

    Args:
        saks: SAKS 实例.
        duration: 动画总时长 (秒).

    Returns:
        最终点数 (1-6).
    """
    result = random.randint(1, 6)
    steps = 20
    for i in range(steps):
        # 越接近结束，切换越慢
        delay = duration * (i / steps) * 0.15 + 0.02
        # 随机显示一个点数图案
        show = random.randint(1, 6) if i < steps - 1 else result
        pattern = DICE_DOT_PATTERNS.get(show, [False] * 8)
        saks.ledrow.set_row(pattern)
        time.sleep(delay)
    return result


def show_dice_number(saks: SAKSHAT, num: int) -> None:
    """数码管显示点数.

    Args:
        saks: SAKS 实例.
        num: 点数 (1-6).
    """
    saks.digital_display.show(f"  {num}")


def main() -> None:
    """主函数."""
    print("=" * 58)
    print("  SAKS SDK 示例 22: 电子骰子")
    print("=" * 58)
    print()
    print("  操作说明:")
    print("    按住任意轻触开关 -> 摇骰子 (LED 滚动)")
    print("    松开按键 -> 显示结果 (LED + 数码管)")
    print("    拨码开关 S1: 骰子数量 (ON=2颗, OFF=1颗)")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()

    try:
        # 显示初始状态
        saks.digital_display.show("READ")
        saks.ledrow.set_row([False] * 8)

        print("  按住轻触开关摇骰子...")

        while True:
            # 轮询按键状态
            left_pressed = saks.tactrow.is_on(0)
            right_pressed = saks.tactrow.is_on(1)

            if left_pressed or right_pressed:
                # 开始摇骰子
                dice_count = 2 if saks.dip_switch.is_on[0] else 1

                # 动画
                r1 = roll_animation(saks, 1.0)
                if dice_count == 2:
                    time.sleep(0.2)
                    r2 = roll_animation(saks, 0.8)
                    total = r1 + r2
                    saks.digital_display.show(f"{r1}{r2}{total:2d}")
                    # 显示两颗骰子图案
                    p1 = DICE_DOT_PATTERNS.get(r1, [False] * 8)
                    saks.ledrow.set_row(p1)
                    time.sleep(1.0)
                    p2 = DICE_DOT_PATTERNS.get(r2, [False] * 8)
                    saks.ledrow.set_row(p2)
                    time.sleep(1.0)
                    print(f"  结果: {r1} + {r2} = {total}")
                else:
                    show_dice_number(saks, r1)
                    pattern = DICE_DOT_PATTERNS.get(r1, [False] * 8)
                    saks.ledrow.set_row(pattern)
                    print(f"  结果: {r1}")

                saks.buzzer.beep(0.05)
                time.sleep(0.5)

                # 等待按键释放
                while saks.tactrow.is_on(0) or saks.tactrow.is_on(1):
                    time.sleep(0.05)

                # 准备下一轮
                saks.ledrow.off()
                saks.digital_display.show("READ")
                print("  按住轻触开关摇骰子...")

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\n  骰子已停止。")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()