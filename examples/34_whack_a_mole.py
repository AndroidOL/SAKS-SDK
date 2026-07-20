#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 34: 打地鼠 (Whack-a-Mole).

LED 随机亮起（地鼠冒头），玩家快速按下对应按键打中它。
错过或打错都会扣分，限时 30 秒，看你能打多少只！

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/34_whack_a_mole.py
"""

import time
import random
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 游戏常量 ----
GAME_DURATION: float = 30.0    # 游戏时长 (秒)
MOLE_SHOW_MIN: float = 0.4     # 地鼠最短出现时间
MOLE_SHOW_MAX: float = 1.5     # 地鼠最长出现时间
LEFT_LEDS: set[int] = {0, 1, 2, 3}
RIGHT_LEDS: set[int] = {4, 5, 6, 7}

score: int = 0
misses: int = 0
mole_pos: int = -1
mole_expire: float = 0.0
game_start: float = 0.0
game_active: bool = False


def spawn_mole() -> tuple[int, float]:
    """生成新地鼠."""
    pos = random.randint(0, 7)
    duration = random.uniform(MOLE_SHOW_MIN, MOLE_SHOW_MAX)
    return pos, duration


def show_mole(saks: SAKSHAT, pos: int) -> None:
    """显示地鼠 (LED 亮)."""
    row = [False] * 8
    row[pos] = True
    saks.ledrow.set_row(row)


def hit_animation(saks: SAKSHAT) -> None:
    """打中动画."""
    saks.ledrow.on()
    saks.buzzer.beep(0.03)
    time.sleep(0.05)
    saks.ledrow.off()


def miss_animation(saks: SAKSHAT) -> None:
    """错过动画."""
    saks.buzzer.beep(0.1)
    saks.ledrow.off()


def main() -> None:
    """主函数."""
    global score, misses, mole_pos, mole_expire, game_start, game_active

    print("=" * 58)
    print("  SAKS SDK 示例 34: 打地鼠 (Whack-a-Mole)")
    print("=" * 58)
    print()
    print("  规则说明:")
    print("    LED 亮起 = 地鼠冒头")
    print("    LED 0-3 对应左键，LED 4-7 对应右键")
    print("    地鼠消失前按对按键得分，打错或超时扣分")
    print(f"    游戏时长: {GAME_DURATION:.0f} 秒")
    print()
    print("  操作说明:")
    print("    左键 (TACT_LEFT)  = 打 LED 0-3")
    print("    右键 (TACT_RIGHT) = 打 LED 4-7")
    print("    拨码 S1: 启动游戏")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()

    try:
        saks.digital_display.show("READ")

        while True:
            # 等待启动
            if not game_active:
                if saks.dip_switch.is_on[0]:
                    game_active = True
                    game_start = time.monotonic()
                    score = 0
                    misses = 0
                    mole_pos, mole_expire = spawn_mole()
                    mole_expire += game_start
                    saks.digital_display.show("  00")
                    print(f"  游戏开始！{GAME_DURATION:.0f} 秒内尽可能多地打地鼠！")
                    time.sleep(0.3)
                else:
                    time.sleep(0.1)
                    continue

            now = time.monotonic()
            elapsed = now - game_start

            # 检查游戏结束
            if elapsed >= GAME_DURATION:
                game_active = False
                saks.digital_display.show(f"  {score:2d}")
                saks.ledrow.off()
                # 结束动画
                for _ in range(3):
                    saks.buzzer.beep(0.1)
                    time.sleep(0.1)
                print(f"  时间到！得分: {score}  失误: {misses}")
                time.sleep(2)
                saks.digital_display.show("READ")
                continue

            # 显示剩余时间
            remaining = int(GAME_DURATION - elapsed)
            saks.digital_display.show(f"  {score:2d}")

            # 检查地鼠是否过期
            if now > mole_expire:
                misses += 1
                miss_animation(saks)
                mole_pos, mole_expire = spawn_mole()
                mole_expire += now

            # 显示地鼠
            show_mole(saks, mole_pos)

            # 检测按键
            left = saks.tactrow.is_on(0)
            right = saks.tactrow.is_on(1)

            if left or right:
                hit_correct = False
                if left and mole_pos in LEFT_LEDS:
                    hit_correct = True
                elif right and mole_pos in RIGHT_LEDS:
                    hit_correct = True

                if hit_correct:
                    score += 1
                    hit_animation(saks)
                    print(f"  打中！得分: {score}")
                else:
                    misses += 1
                    miss_animation(saks)

                # 生成新地鼠
                mole_pos, mole_expire = spawn_mole()
                mole_expire += now
                time.sleep(0.1)

            time.sleep(0.03)

    except KeyboardInterrupt:
        print(f"\n\n  游戏结束。得分: {score}  失误: {misses}")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()