#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 39: 二进制解码挑战 (Binary Decoder).

LED 显示二进制数字，玩家用按键输入对应的十进制值。
数码管显示倒计时，答对得分，答错扣分。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/39_binary_decoder.py
"""

import time
import random
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 游戏常量 ----
GAME_DURATION: float = 30.0
ANSWER_TIME: float = 5.0

score: int = 0
current_value: int = 0
player_answer: int = 0
question_start: float = 0.0
game_active: bool = False
game_start: float = 0.0
best: int = 0


def show_binary(saks: SAKSHAT, value: int) -> None:
    """用 LED 显示 8-bit 二进制.

    Args:
        saks: SAKS 实例.
        value: 0-255 之间的值.
    """
    row = [False] * 8
    for i in range(8):
        if value & (1 << i):
            row[i] = True
    saks.ledrow.set_row(row)


def new_question() -> None:
    """生成新题目."""
    global current_value, player_answer, question_start
    current_value = random.randint(1, 255)
    player_answer = 0
    question_start = time.monotonic()


def main() -> None:
    """主函数."""
    global score, current_value, player_answer, question_start, game_active, game_start, best

    print("=" * 58)
    print("  SAKS SDK 示例 39: 二进制解码挑战")
    print("=" * 58)
    print()
    print("  规则说明:")
    print("    LED 显示 8-bit 二进制数字 (LED 0=LSB, LED 7=MSB)")
    print("    用按键输入十进制值，数码管显示当前输入")
    print("    5 秒内提交答案，超时计 0 分")
    print()
    print("  操作说明:")
    print("    左键 (TACT_LEFT)  = 减少数值")
    print("    右键 (TACT_RIGHT) = 增加数值")
    print("    同时按 = 提交答案")
    print("    拨码 S1: 开始游戏")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()

    try:
        saks.digital_display.show("BIND")

        print("  拨码 S1 开始游戏！")

        while True:
            if saks.dip_switch.is_on[0] and not game_active:
                game_active = True
                game_start = time.monotonic()
                score = 0
                new_question()
                saks.digital_display.show("  00")
                print(f"  游戏开始！{GAME_DURATION:.0f} 秒倒计时")
                time.sleep(0.3)

            if not game_active:
                time.sleep(0.1)
                continue

            now = time.monotonic()
            elapsed = now - game_start

            # 游戏结束
            if elapsed >= GAME_DURATION:
                game_active = False
                if score > best:
                    best = score
                saks.digital_display.show(f"  {score:2d}")
                for _ in range(3):
                    saks.buzzer.beep(0.1)
                    time.sleep(0.1)
                print(f"  时间到！得分: {score}")
                time.sleep(2)
                saks.digital_display.show("BIND")
                continue

            # 显示剩余时间
            remain = int(GAME_DURATION - elapsed)
            saks.digital_display.show(f" {player_answer:3d}")

            show_binary(saks, current_value)

            # 检查题目超时
            question_elapsed = now - question_start
            if question_elapsed > ANSWER_TIME:
                print(f"  超时！答案: {current_value}")
                saks.buzzer.beep(0.15)
                new_question()
                time.sleep(0.3)
                continue

            # 剩余时间闪烁
            if question_elapsed > ANSWER_TIME * 0.7:
                if int(question_elapsed * 4) % 2 == 0:
                    saks.buzzer.beep(0.01)

            # 按键处理
            left = saks.tactrow.is_on(0)
            right = saks.tactrow.is_on(1)

            if left and right:
                # 同时按 = 提交
                if player_answer == current_value:
                    score += 10
                    saks.ledrow.on()
                    saks.buzzer.beep(0.05)
                    time.sleep(0.1)
                    saks.ledrow.off()
                    print(f"  ✅ 正确！{current_value} = {bin(current_value)}  +10")
                else:
                    score = max(0, score - 5)
                    saks.buzzer.beep(0.2)
                    print(f"  ❌ 错误！答案: {current_value}，你输入了 {player_answer}")
                new_question()
                time.sleep(0.3)
            elif left:
                player_answer = max(0, player_answer - 1)
                saks.buzzer.beep(0.01)
                time.sleep(0.08)
            elif right:
                player_answer = min(255, player_answer + 1)
                saks.buzzer.beep(0.01)
                time.sleep(0.08)

            time.sleep(0.02)

    except KeyboardInterrupt:
        print(f"\n\n  游戏结束。得分: {score}")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()