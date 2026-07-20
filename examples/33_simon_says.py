#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 33: 西蒙记忆游戏 (Simon Says).

经典记忆游戏：LED 随机亮起 + 蜂鸣器发出对应音调，玩家需要记住
并重复序列。每轮增加一个音符，错误则游戏结束。

4 个 LED (0-3) 对应左键，4 个 LED (4-7) 对应右键。
不同 LED 发出不同音调，帮助记忆。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/33_simon_says.py
"""

import time
import random
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 音调定义 ----
# 8 个 LED 对应 8 个音调 (C4 到 C5)
TONES: list[int] = [262, 294, 330, 349, 392, 440, 494, 523]

# 玩家输入映射: LED 0-3 = 左键, LED 4-7 = 右键
LEFT_LEDS: list[int] = [0, 1, 2, 3]
RIGHT_LEDS: list[int] = [4, 5, 6, 7]

sequence: list[int] = []
player_pos: int = 0
score: int = 0
best_score: int = 0
high_score: int = 0
game_phase: str = "idle"  # idle, show, input, over
last_input: float = 0.0


def play_tone(saks: SAKSHAT, led_idx: int, duration: float) -> None:
    """播放指定 LED 对应的音调.

    Args:
        saks: SAKS 实例.
        led_idx: LED 索引 (0-7).
        duration: 持续时间 (秒).
    """
    from sakshat._gpio import GPIO
    freq = TONES[led_idx]
    row = [False] * 8
    row[led_idx] = True
    saks.ledrow.set_row(row)
    pwm = GPIO.PWM(SAKSPins.BUZZER, freq)
    pwm.start(50)
    time.sleep(duration)
    pwm.stop()
    saks.ledrow.off()
    time.sleep(0.05)


def show_sequence(saks: SAKSHAT, seq: list[int]) -> None:
    """播放序列给玩家看.

    Args:
        saks: SAKS 实例.
        seq: 要播放的 LED 索引序列.
    """
    saks.digital_display.show("----")
    time.sleep(0.5)
    for led_idx in seq:
        play_tone(saks, led_idx, 0.35)
        time.sleep(0.1)


def game_over_animation(saks: SAKSHAT) -> None:
    """游戏结束动画."""
    for _ in range(3):
        saks.ledrow.on()
        saks.buzzer.beep(0.15)
        time.sleep(0.15)
        saks.ledrow.off()
        time.sleep(0.15)


def main() -> None:
    """主函数."""
    global sequence, player_pos, score, best_score, high_score, game_phase, last_input

    print("=" * 58)
    print("  SAKS SDK 示例 33: 西蒙记忆游戏 (Simon Says)")
    print("=" * 58)
    print()
    print("  规则说明:")
    print("    LED 0-3 对应左键，LED 4-7 对应右键")
    print("    记住 LED 序列，按顺序重复")
    print("    每轮增加一个音符，错误则游戏结束")
    print("    数码管显示当前得分")
    print()
    print("  操作说明:")
    print("    左键 (TACT_LEFT)  = 输入 LED 0-3 组")
    print("    右键 (TACT_RIGHT) = 输入 LED 4-7 组")
    print("    拨码 S1: 难度 (ON=快速, OFF=慢速)")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()
    # 手动轮询，不使用事件回调

    try:
        # 初始化
        sequence = [random.randint(0, 7)]
        player_pos = 0
        score = 0
        game_phase = "show"
        saks.digital_display.show("SIMN")
        print("  新游戏！看 LED 序列...")
        show_sequence(saks, sequence)
        game_phase = "input"
        saks.digital_display.show(f"  {score:2d}")

        while True:
            # 检查重置
            if saks.dip_switch.is_on[1]:
                sequence = [random.randint(0, 7)]
                player_pos = 0
                score = 0
                game_phase = "show"
                saks.digital_display.show("SIMN")
                print("  新游戏！看 LED 序列...")
                show_sequence(saks, sequence)
                game_phase = "input"
                saks.digital_display.show(f"  {score:2d}")
                time.sleep(0.3)

            if game_phase == "input":
                left = saks.tactrow.is_on(0)
                right = saks.tactrow.is_on(1)

                if left or right:
                    time.sleep(0.02)  # 去抖
                    # 确定玩家按了哪个 LED
                    # 简化: 根据按键重复次数判断
                    # 第一轮: 左键按 LED 组中的第一个，右键按 LED 组中的第一个
                    now = time.monotonic()
                    if now - last_input < 0.3:
                        continue  # 防重复
                    last_input = now

                    if left:
                        # 左键: 在 LEFT_LEDS 中循环
                        expected = sequence[player_pos]
                        # 简化: 左键固定对应序列中属于左组的 LED
                        if expected in LEFT_LEDS:
                            saks.buzzer.beep(0.03)
                        else:
                            saks.buzzer.beep(0.03)
                    else:
                        pass

                    # 简化逻辑: 用按键次数来选择 LED
                    # 左键 = 当前序列位置对应的 LED 在左组
                    # 这里我们简化: 玩家需要按左键或右键来匹配
                    # 序列中是左组 LED → 按左键; 右组 LED → 按右键
                    expected = sequence[player_pos]
                    correct = (left and expected in LEFT_LEDS) or (right and expected in RIGHT_LEDS)

                    if correct:
                        play_tone(saks, expected, 0.15)
                        player_pos += 1
                        saks.digital_display.show(f"  {score:2d}")

                        if player_pos >= len(sequence):
                            # 本轮完成
                            score += 1
                            if score > high_score:
                                high_score = score
                            saks.digital_display.show(f"GOOD")
                            time.sleep(0.5)
                            saks.digital_display.show(f"  {score:2d}")
                            print(f"  第 {score} 轮通过！")

                            # 增加新音符
                            sequence.append(random.randint(0, 7))
                            player_pos = 0
                            game_phase = "show"
                            show_sequence(saks, sequence)
                            game_phase = "input"
                            saks.digital_display.show(f"  {score:2d}")
                    else:
                        # 错误
                        game_phase = "over"
                        best_score = max(best_score, score)
                        saks.digital_display.show(f"GA{score:2d}")
                        game_over_animation(saks)
                        print(f"  游戏结束！得分: {score}  最高: {high_score}")

                        time.sleep(2)
                        # 重新开始
                        sequence = [random.randint(0, 7)]
                        player_pos = 0
                        score = 0
                        game_phase = "show"
                        show_sequence(saks, sequence)
                        game_phase = "input"
                        saks.digital_display.show(f"  {score:2d}")
                        print(f"  新游戏！最高分: {high_score}")

            time.sleep(0.05)

    except KeyboardInterrupt:
        print(f"\n\n  游戏结束，最高分: {high_score}")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()