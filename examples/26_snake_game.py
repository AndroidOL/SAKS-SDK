#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 26: 贪吃蛇 - 8 LED 版.

在 8 颗 LED 上玩贪吃蛇！蛇在 LED 阵列上移动，按键控制方向。
吃到食物 (闪烁 LED) 后蛇身变长，根据蛇身长度得分。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/26_snake_game.py
"""

import time
import random
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 游戏常量 ----
LED_COUNT: int = 8
INITIAL_SPEED: float = 0.3
MIN_SPEED: float = 0.08
SPEED_INCREASE: float = 0.02

# ---- 全局状态 ----
direction: int = 1  # 1=右, -1=左
snake: list[int] = [3, 2, 1]  # 蛇身位置 (头在 index 0)
food: int = 6
score: int = 0
game_over: bool = False
last_move: float = 0.0
button_pressed: bool = False


def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关控制方向."""
    global direction, button_pressed
    if not status:
        return
    if pin == SAKSPins.TACT_RIGHT:
        direction = 1
    elif pin == SAKSPins.TACT_LEFT:
        direction = -1
    button_pressed = True


def spawn_food() -> int:
    """在空位生成食物."""
    available = [i for i in range(LED_COUNT) if i not in snake]
    return random.choice(available) if available else -1


def reset_game() -> None:
    """重置游戏."""
    global snake, food, score, game_over, direction
    snake = [3, 2, 1]
    food = 6
    score = 0
    game_over = False
    direction = 1


def show_game(saks: SAKSHAT) -> None:
    """显示当前游戏状态."""
    row = [False] * LED_COUNT
    for seg in snake:
        if 0 <= seg < LED_COUNT:
            row[seg] = True
    if food >= 0:
        row[food] = True
    saks.ledrow.set_row(row)


def game_over_animation(saks: SAKSHAT) -> None:
    """游戏结束动画."""
    for _ in range(3):
        saks.ledrow.on()
        saks.buzzer.beep(0.1)
        time.sleep(0.15)
        saks.ledrow.off()
        time.sleep(0.15)


def main() -> None:
    """主函数."""
    global direction, snake, food, score, game_over, last_move

    print("=" * 58)
    print("  SAKS SDK 示例 26: 贪吃蛇 (8 LED 版)")
    print("=" * 58)
    print()
    print("  规则说明:")
    print("    蛇在 8 颗 LED 上移动")
    print("    吃掉食物 (第二颗 LED) 后蛇身变长")
    print("    撞到自己或越界则游戏结束")
    print("    得分 = 蛇身长度")
    print()
    print("  操作说明:")
    print("    右键 (TACT_RIGHT): 向右移动")
    print("    左键 (TACT_LEFT):  向左移动")
    print("    拨码开关 S1: 重置游戏")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()
    saks.tact_event_handler = on_tact_event

    try:
        reset_game()
        last_move = time.monotonic()
        saks.digital_display.show(f"  {score:2d}")
        print("  游戏开始！按左右键控制方向。")

        while True:
            # 检查重置
            if saks.dip_switch.is_on[0]:
                reset_game()
                saks.digital_display.show(f"  {score:2d}")
                print("  游戏已重置。")
                time.sleep(0.3)

            if game_over:
                saks.digital_display.show(f"GA{score:2d}")
                # 等待重置
                while not saks.dip_switch.is_on[0]:
                    time.sleep(0.1)
                reset_game()
                saks.digital_display.show(f"  {score:2d}")
                print("  新游戏开始！")
                continue

            # 速度 = 基础速度 - 得分加速
            speed = max(MIN_SPEED, INITIAL_SPEED - score * SPEED_INCREASE)

            # 移动蛇
            now = time.monotonic()
            if now - last_move >= speed:
                last_move = now

                # 计算新头部位置
                new_head = snake[0] + direction

                # 检查碰撞
                if new_head < 0 or new_head >= LED_COUNT or new_head in snake:
                    game_over = True
                    game_over_animation(saks)
                    print(f"  游戏结束！得分: {score}")
                    continue

                # 移动蛇
                snake.insert(0, new_head)

                # 检查是否吃到食物
                if new_head == food:
                    score = len(snake)
                    saks.buzzer.beep(0.03)
                    food = spawn_food()
                    saks.digital_display.show(f"  {score:2d}")
                else:
                    snake.pop()

                show_game(saks)

            time.sleep(0.01)

    except KeyboardInterrupt:
        print(f"\n\n  游戏结束，最终得分: {score}")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()