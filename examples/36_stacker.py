#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 36: 堆叠挑战 (Stacker).

经典街机堆叠游戏：LED 方块左右移动，按键在正确时机停下。
停下的 LED 堆积起来，必须堆到顶部才能获胜。
每层越来越快，失手则从底部重新开始。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/36_stacker.py
"""

import time
import random
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 游戏常量 ----
STACK_HEIGHT: int = 8  # 8 层
BASE_SPEED: float = 0.12
MIN_SPEED: float = 0.03

stack: list[int] = []  # 已堆叠的 LED 索引
cursor_pos: float = 0.0
cursor_dir: int = 1
speed: float = BASE_SPEED
level: int = 0
last_move: float = 0.0
game_active: bool = False
score: int = 0
best: int = 0


def reset_game() -> None:
    """重置游戏."""
    global stack, cursor_pos, cursor_dir, speed, level, score
    stack = []
    cursor_pos = 0.0
    cursor_dir = 1
    speed = BASE_SPEED
    level = 0
    score = 0


def show_stack(saks: SAKSHAT) -> None:
    """显示堆叠状态."""
    row = [False] * 8
    # 已堆叠的层
    for i, pos in enumerate(stack):
        row[pos] = True
    # 当前光标
    if level < STACK_HEIGHT:
        cursor = int(cursor_pos) % 8
        row[cursor] = True
    saks.ledrow.set_row(row)


def fail_animation(saks: SAKSHAT) -> None:
    """失败动画."""
    for _ in range(3):
        saks.ledrow.off()
        saks.buzzer.beep(0.15)
        time.sleep(0.1)
        saks.ledrow.on()
        time.sleep(0.1)
    saks.ledrow.off()


def win_animation(saks: SAKSHAT) -> None:
    """胜利动画."""
    for _ in range(5):
        saks.ledrow.on()
        saks.buzzer.beep(0.05)
        time.sleep(0.08)
        saks.ledrow.off()
        time.sleep(0.08)
    saks.ledrow.on()
    saks.buzzer.beep(0.3)
    saks.ledrow.off()


def main() -> None:
    """主函数."""
    global stack, cursor_pos, cursor_dir, speed, level, last_move, game_active, score, best

    print("=" * 58)
    print("  SAKS SDK 示例 36: 堆叠挑战 (Stacker)")
    print("=" * 58)
    print()
    print("  规则说明:")
    print("    LED 方块左右移动，按任意键停下")
    print("    停下的方块必须叠在已有的方块上")
    print("    如果没对齐，方块会被切掉（变窄）")
    print("    堆到顶部 (8 层) 即获胜！")
    print()
    print("  操作说明:")
    print("    左键或右键: 停止方块")
    print("    拨码 S1: 开始新游戏")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()

    try:
        reset_game()
        saks.digital_display.show("STAK")
        last_move = time.monotonic()

        print("  拨码 S1 开始新游戏！")

        while True:
            # 检查新游戏
            if saks.dip_switch.is_on[0] and not game_active:
                game_active = True
                reset_game()
                saks.digital_display.show(" 0  0")
                print("  堆叠开始！")
                time.sleep(0.3)

            if not game_active:
                time.sleep(0.1)
                continue

            # 显示分数
            saks.digital_display.show(f" {score:2d} {level:2d}")

            now = time.monotonic()
            if now - last_move >= speed:
                last_move = now

                # 移动光标
                cursor_pos += cursor_dir
                if int(cursor_pos) >= 7:
                    cursor_dir = -1
                elif int(cursor_pos) <= 0:
                    cursor_dir = 1
                cursor_pos = max(0.0, min(7.0, cursor_pos))

            show_stack(saks)

            # 检测按键
            left = saks.tactrow.is_on(0)
            right = saks.tactrow.is_on(1)

            if left or right and level < STACK_HEIGHT:
                # 停止方块
                stopped = int(cursor_pos) % 8

                if level == 0:
                    # 第一层：任意位置都行
                    stack.append(stopped)
                    level += 1
                    score += 10
                    speed *= 0.9
                    saks.buzzer.beep(0.03)
                else:
                    # 后续层：必须叠在已有方块上
                    prev = stack[-1]
                    if stopped == prev:
                        # 完美对齐
                        stack.append(stopped)
                        level += 1
                        score += 20
                        speed = max(MIN_SPEED, speed * 0.92)
                        saks.buzzer.beep(0.05)
                    elif abs(stopped - prev) <= 1:
                        # 靠近但没对齐：切窄
                        stack.append(prev)  # 保持原位置
                        level += 1
                        score += 5
                        speed = max(MIN_SPEED, speed * 0.95)
                        saks.buzzer.beep(0.02)
                    else:
                        # 完全没对齐：失败
                        fail_animation(saks)
                        print(f"  堆叠失败！得分: {score}")
                        if score > best:
                            best = score
                        game_active = False
                        saks.digital_display.show(f"b{best:3d}")
                        saks.ledrow.off()
                        continue

                # 检查是否胜利
                if level >= STACK_HEIGHT:
                    score += 100
                    win_animation(saks)
                    print(f"  🏆 堆叠成功！得分: {score}")
                    if score > best:
                        best = score
                    game_active = False
                    saks.digital_display.show("WIN!")
                    saks.ledrow.off()
                    continue

                time.sleep(0.2)

            time.sleep(0.01)

    except KeyboardInterrupt:
        print(f"\n\n  游戏结束。最高分: {best}")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()