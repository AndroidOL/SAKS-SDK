#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 37: 节奏大师 (Rhythm Master).

DDR 风格节奏游戏：LED 按节拍依次亮起，蜂鸣器播放节拍音。
在 LED 到达目标位置时按键，精准度决定得分。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/37_rhythm_master.py
"""

import time
import random
import sys
import signal
import math

from sakshat import SAKSHAT, SAKSPins

# ---- 游戏常量 ----
BPM: int = 100
BEAT_INTERVAL: float = 60.0 / BPM
HIT_WINDOW_PERFECT: float = 0.08   # 完美判定窗口
HIT_WINDOW_GOOD: float = 0.18      # 良好判定窗口
LED_COUNT: int = 8

score: int = 0
combo: int = 0
max_combo: int = 0
beat_led: int = 0
beat_timer: float = 0.0
game_active: bool = False
game_duration: float = 20.0
game_start: float = 0.0
last_judgment: str = ""


def play_beat(saks: SAKSHAT) -> None:
    """播放节拍音."""
    saks.buzzer.beep(0.02)


def show_judgment(saks: SAKSHAT, judgment: str) -> None:
    """显示判定结果."""
    if judgment == "PERFECT":
        saks.ledrow.on()
        saks.buzzer.beep(0.03)
        time.sleep(0.05)
        saks.ledrow.off()
    elif judgment == "GOOD":
        row = [False] * 8
        for i in range(4):
            row[i] = True
        saks.ledrow.set_row(row)
        saks.buzzer.beep(0.02)
        time.sleep(0.05)
        saks.ledrow.off()
    elif judgment == "MISS":
        saks.buzzer.beep(0.1)
        saks.ledrow.off()


def main() -> None:
    """主函数."""
    global score, combo, max_combo, beat_led, beat_timer, game_active, game_start, last_judgment

    print("=" * 58)
    print("  SAKS SDK 示例 37: 节奏大师 (Rhythm Master)")
    print("=" * 58)
    print()
    print("  规则说明:")
    print("    LED 从左到右依次亮起 = 节拍接近")
    print("    LED 7 亮起时按任意键 = 击打节拍")
    print("    判定: PERFECT (+10) / GOOD (+5) / MISS (-3)")
    print("    连击加分，断连扣分")
    print()
    print("  操作说明:")
    print("    左键或右键: 击打节拍")
    print("    拨码 S1: 开始游戏")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()

    try:
        saks.digital_display.show("RHYM")
        beat_timer = time.monotonic()
        beat_led = 0

        print("  拨码 S1 开始游戏！")

        while True:
            if saks.dip_switch.is_on[0] and not game_active:
                game_active = True
                game_start = time.monotonic()
                score = 0
                combo = 0
                max_combo = 0
                beat_led = 0
                beat_timer = game_start
                saks.digital_display.show("  00")
                print("  节奏开始！")
                time.sleep(0.3)

            if not game_active:
                time.sleep(0.1)
                continue

            now = time.monotonic()
            elapsed = now - game_start

            # 时间到
            if elapsed >= game_duration:
                game_active = False
                saks.digital_display.show(f"  {score:2d}")
                for _ in range(3):
                    saks.buzzer.beep(0.08)
                    time.sleep(0.1)
                print(f"  时间到！得分: {score}  最大连击: {max_combo}")
                time.sleep(2)
                saks.digital_display.show("RHYM")
                continue

            # 显示剩余时间和得分
            remain = int(game_duration - elapsed)
            saks.digital_display.show(f" {score:2d}{remain:2d}")

            # 节拍进度
            beat_progress = (now - beat_timer) / BEAT_INTERVAL
            if beat_progress >= 1.0:
                # 新节拍
                beat_timer = now
                beat_led = (beat_led + 1) % LED_COUNT
                play_beat(saks)

            # LED 显示节拍位置
            approaching = int(beat_progress * LED_COUNT) % LED_COUNT
            row = [False] * 8
            row[approaching] = True
            # 显示目标位置
            if approaching >= 6:
                row[7] = True
            saks.ledrow.set_row(row)

            # 检测按键
            left = saks.tactrow.is_on(0)
            right = saks.tactrow.is_on(1)

            if left or right:
                # 判断离目标 (LED 7) 的距离
                dist = abs(beat_progress - 1.0)
                if dist < HIT_WINDOW_PERFECT:
                    score += 10 + combo
                    combo += 1
                    max_combo = max(max_combo, combo)
                    last_judgment = "PERFECT"
                    print(f"  PERFECT! +{10 + combo - 1}  连击: {combo}")
                elif dist < HIT_WINDOW_GOOD:
                    score += 5 + combo // 2
                    combo += 1
                    max_combo = max(max_combo, combo)
                    last_judgment = "GOOD"
                    print(f"  GOOD +{5 + combo // 2}  连击: {combo}")
                else:
                    score = max(0, score - 3)
                    combo = 0
                    last_judgment = "MISS"
                    print(f"  MISS!  得分: {score}")

                # 下一个节拍
                beat_timer = now
                beat_led = (beat_led + 1) % LED_COUNT
                show_judgment(saks, last_judgment)
                time.sleep(0.1)

            time.sleep(0.01)

    except KeyboardInterrupt:
        print(f"\n\n  游戏结束。得分: {score}  最大连击: {max_combo}")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()