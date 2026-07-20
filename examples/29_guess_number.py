#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 29: 猜数字游戏.

拨码开关设定 2 位目标数字 (0-3)，按键猜数字。
LED 提示: 越往右越接近，蜂鸣器提示高低。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/29_guess_number.py
"""

import time
import random
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 全局状态 ----
target: int = 0
current_guess: int = 0
attempts: int = 0
best_score: int = 999
game_over: bool = False
beep_requested: bool = False


def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关调整猜测."""
    global current_guess, beep_requested
    if not status:
        return
    if pin == SAKSPins.TACT_RIGHT:
        current_guess = (current_guess + 1) % 4
    elif pin == SAKSPins.TACT_LEFT:
        current_guess = (current_guess - 1) % 4
    beep_requested = True


def new_game(dip_val: int) -> None:
    """开始新游戏."""
    global target, attempts, game_over
    if dip_val == 0:
        target = random.randint(0, 3)
    else:
        target = dip_val - 1  # 拨码 1-4 对应数字 0-3
    attempts = 0
    game_over = False


def main() -> None:
    """主函数."""
    global current_guess, attempts, best_score, game_over, beep_requested

    print("=" * 58)
    print("  SAKS SDK 示例 29: 猜数字游戏")
    print("=" * 58)
    print()
    print("  规则说明:")
    print("    用拨码开关设定目标数字 (00=随机, 01=0, 10=1, 11=2, 同时=3)")
    print("    按键调整猜测数字 (0-3)")
    print("    数码管显示: 当前猜测 | 已猜次数")
    print("    LED 指示: 越往右越接近")
    print("    猜到后蜂鸣提示，显示最佳成绩")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()
    saks.tact_event_handler = on_tact_event

    try:
        # 初始化
        dip = saks.dip_switch.is_on
        dip_val = (1 if dip[0] else 0) + (2 if dip[1] else 0)
        new_game(dip_val)
        current_guess = 0
        saks.digital_display.show("GAME")

        print(f"  新游戏！目标数字 0-3 (拨码设定: {dip_val})")
        print(f"  当前猜测: {current_guess}")

        while True:
            if beep_requested:
                saks.buzzer.beep(0.02)
                saks.digital_display.show(f" {current_guess}{attempts:2d}")
                print(f"  当前猜测: {current_guess}  (已猜 {attempts} 次)")
                beep_requested = False

            # 检查拨码重置
            dip = saks.dip_switch.is_on
            new_dip_val = (1 if dip[0] else 0) + (2 if dip[1] else 0)
            if new_dip_val != (1 if saks.dip_switch.is_on[0] else 0) + (2 if saks.dip_switch.is_on[1] else 0):
                pass  # 仅在变化时处理

            # 检查按键确认 (两个同时按 = 确认猜测)
            left = saks.tactrow.is_on(0)
            right = saks.tactrow.is_on(1)

            if left and right and not game_over:
                attempts += 1

                if current_guess == target:
                    game_over = True
                    if attempts < best_score:
                        best_score = attempts
                    saks.digital_display.show(f"GOOD")
                    # 庆祝动画
                    for _ in range(3):
                        saks.ledrow.on()
                        saks.buzzer.beep(0.05)
                        time.sleep(0.1)
                        saks.ledrow.off()
                        time.sleep(0.1)
                    print(f"  ✅ 猜中了！数字 = {target}，用了 {attempts} 次")
                    print(f"  最佳成绩: {best_score} 次")
                else:
                    diff = current_guess - target
                    saks.digital_display.show(f" {current_guess}{attempts:2d}")

                    # LED 提示距离
                    distance = abs(diff)
                    row = [False] * 8
                    # 距离越大，LED 越靠左
                    lit = max(0, 8 - distance * 2)
                    for i in range(lit):
                        row[i] = True
                    saks.ledrow.set_row(row)

                    if diff > 0:
                        saks.buzzer.beep(0.15)
                        print(f"  ⬇  太大了！(猜 {current_guess}, 第 {attempts} 次)")
                    elif diff < 0:
                        saks.buzzer.beep(0.05)
                        print(f"  ⬆  太小了！(猜 {current_guess}, 第 {attempts} 次)")

                    time.sleep(0.5)
                    saks.ledrow.off()

                time.sleep(0.3)

            elif game_over:
                saks.digital_display.show(f"b{best_score:2d} ")
                time.sleep(0.3)

            time.sleep(0.1)

    except KeyboardInterrupt:
        print(f"\n\n  游戏结束。最佳成绩: {best_score} 次")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()