#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 40: 烫手山芋 (Hot Potato).

"炸弹" LED 在玩家之间传递，蜂鸣器滴答声越来越快。
随机时间后爆炸，最后持有者输掉。多人轮流按键传递。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/40_hot_potato.py
"""

import time
import random
import sys
import signal
import math

from sakshat import SAKSHAT, SAKSPins

# ---- 游戏常量 ----
FUSE_MIN: float = 3.0    # 最短引信时间
FUSE_MAX: float = 10.0   # 最长引信时间
TICK_START: float = 0.5   # 初始滴答间隔
TICK_END: float = 0.05    # 最快滴答间隔

fuse_time: float = 0.0
fuse_start: float = 0.0
potato_pos: int = 0
player_count: int = 2
current_player: int = 0
game_active: bool = False
score: int = 0
best: int = 0
last_tick: float = 0.0
tick_interval: float = TICK_START


def reset_fuse() -> None:
    """重置引信."""
    global fuse_time, fuse_start, last_tick, tick_interval
    fuse_time = random.uniform(FUSE_MIN, FUSE_MAX)
    fuse_start = time.monotonic()
    last_tick = fuse_start
    tick_interval = TICK_START


def explode_animation(saks: SAKSHAT) -> None:
    """爆炸动画."""
    for _ in range(4):
        saks.ledrow.on()
        saks.buzzer.beep(0.1)
        time.sleep(0.08)
        saks.ledrow.off()
        time.sleep(0.08)
    saks.buzzer.beep(0.5)


def pass_animation(saks: SAKSHAT) -> None:
    """传递动画."""
    saks.buzzer.beep(0.02)


def main() -> None:
    """主函数."""
    global fuse_time, fuse_start, potato_pos, game_active, score, best, last_tick, tick_interval

    print("=" * 58)
    print("  SAKS SDK 示例 40: 烫手山芋 (Hot Potato)")
    print("=" * 58)
    print()
    print("  规则说明:")
    print("    LED 1 和 LED 6 代表两个玩家")
    print("    '山芋'在玩家之间传递，蜂鸣器滴答声渐快")
    print("    随机时间后爆炸，持有者输掉")
    print("    存活轮数越多得分越高")
    print()
    print("  操作说明:")
    print("    左键 (TACT_LEFT)  = 玩家 1 传递山芋")
    print("    右键 (TACT_RIGHT) = 玩家 2 传递山芋")
    print("    拨码 S1: 开始新游戏")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()

    try:
        saks.digital_display.show("HOTP")
        potato_pos = 0  # 0=玩家1, 1=玩家2

        print("  拨码 S1 开始游戏！")

        while True:
            if saks.dip_switch.is_on[0] and not game_active:
                game_active = True
                potato_pos = 0
                score = 0
                reset_fuse()
                saks.digital_display.show("  00")
                print("  山芋出现！快传！")
                time.sleep(0.3)

            if not game_active:
                time.sleep(0.1)
                continue

            now = time.monotonic()
            elapsed = now - fuse_start

            # 显示得分
            saks.digital_display.show(f" P{potato_pos + 1}{score:2d}")

            # 滴答声
            progress = elapsed / fuse_time
            tick_interval = TICK_START - (TICK_START - TICK_END) * progress
            if now - last_tick >= tick_interval:
                last_tick = now
                saks.buzzer.beep(0.01)

            # 显示山芋位置
            if potato_pos == 0:
                row = [True, True, False, False, False, False, False, False]
            else:
                row = [False, False, False, False, False, False, True, True]
            saks.ledrow.set_row(row)

            # 检查爆炸
            if elapsed >= fuse_time:
                explode_animation(saks)
                loser = potato_pos + 1
                print(f"  💥 爆炸！玩家 {loser} 被炸！存活 {score} 轮")
                if score > best:
                    best = score
                game_active = False
                saks.digital_display.show(f"b{best:3d}")
                time.sleep(2)
                saks.digital_display.show("HOTP")
                continue

            # 按键传递
            left = saks.tactrow.is_on(0)
            right = saks.tactrow.is_on(1)

            if left and potato_pos == 0:
                # 玩家 1 传给玩家 2
                potato_pos = 1
                pass_animation(saks)
                print(f"  玩家 1 → 玩家 2")
                time.sleep(0.15)
            elif right and potato_pos == 1:
                # 玩家 2 传给玩家 1
                potato_pos = 0
                score += 1
                pass_animation(saks)
                print(f"  玩家 2 → 玩家 1  存活: {score} 轮")
                # 重置引信
                reset_fuse()
                time.sleep(0.15)

            time.sleep(0.02)

    except KeyboardInterrupt:
        print(f"\n\n  游戏结束。最高存活: {best} 轮")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()