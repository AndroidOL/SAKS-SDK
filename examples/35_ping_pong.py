#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 35: LED 乒乓球 (Ping Pong).

在 8 颗 LED 上玩乒乓球！LED 光点代表球，在 LED 阵列上来回弹跳。
按键充当球拍，在球到达两端时按键回击。错过球则对方得分。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/35_ping_pong.py
"""

import time
import random
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 游戏常量 ----
LED_COUNT: int = 8
INITIAL_SPEED: float = 0.25
MAX_SPEED: float = 0.06
SPEED_INCREASE: float = 0.015

ball_pos: float = 3.5
ball_dir: int = 1  # 1=右, -1=左
speed: float = INITIAL_SPEED
score_left: int = 0
score_right: int = 0
last_move: float = 0.0
game_active: bool = False
rally_count: int = 0


def reset_ball() -> None:
    """重置球到中间."""
    global ball_pos, ball_dir, speed
    ball_pos = 3.5
    ball_dir = random.choice([-1, 1])
    speed = INITIAL_SPEED


def serve_ball(winner: str) -> None:
    """发球，朝向输家."""
    global ball_pos, ball_dir, speed, rally_count
    ball_pos = 3.5
    ball_dir = 1 if winner == "left" else -1
    speed = INITIAL_SPEED
    rally_count = 0


def hit_animation(saks: SAKSHAT) -> None:
    """击球音效."""
    freq = 500 + rally_count * 20
    from sakshat._gpio import GPIO
    pwm = GPIO.PWM(SAKSPins.BUZZER, min(freq, 1000))
    pwm.start(50)
    time.sleep(0.02)
    pwm.stop()


def score_animation(saks: SAKSHAT) -> None:
    """得分音效."""
    saks.buzzer.beep(0.15)
    time.sleep(0.1)
    saks.buzzer.beep(0.15)


def main() -> None:
    """主函数."""
    global ball_pos, ball_dir, speed, score_left, score_right, last_move, game_active, rally_count

    print("=" * 58)
    print("  SAKS SDK 示例 35: LED 乒乓球 (Ping Pong)")
    print("=" * 58)
    print()
    print("  规则说明:")
    print("    LED 光点 = 乒乓球")
    print("    球到达 LED 0 时按左键击球")
    print("    球到达 LED 7 时按右键击球")
    print("    球速随回合数加快，先到 5 分者胜")
    print()
    print("  操作说明:")
    print("    左键 (TACT_LEFT)  = 左球拍 (LED 0/1)")
    print("    右键 (TACT_RIGHT) = 右球拍 (LED 6/7)")
    print("    拨码 S1: 开始新游戏")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()

    try:
        saks.digital_display.show("PONG")
        reset_ball()
        last_move = time.monotonic()

        print("  拨码 S1 开始新游戏！")

        while True:
            # 检查新游戏
            if saks.dip_switch.is_on[0]:
                game_active = True
                score_left = 0
                score_right = 0
                reset_ball()
                saks.digital_display.show(" 0  0")
                print("  新游戏！先到 5 分者胜！")
                time.sleep(0.3)

            if not game_active:
                time.sleep(0.1)
                continue

            # 显示比分
            if score_left >= 5 or score_right >= 5:
                winner = "左" if score_left >= 5 else "右"
                saks.digital_display.show(f" {score_left}W{score_right}")
                for _ in range(5):
                    saks.ledrow.on()
                    saks.buzzer.beep(0.05)
                    time.sleep(0.1)
                    saks.ledrow.off()
                    time.sleep(0.1)
                print(f"  🏆 {winner}方获胜！{score_left}:{score_right}")
                game_active = False
                saks.digital_display.show("PONG")
                continue

            saks.digital_display.show(f" {score_left}  {score_right}")

            now = time.monotonic()
            if now - last_move >= speed:
                last_move = now

                # 移动球
                ball_pos += ball_dir * 0.5

                # 检查击球
                left = saks.tactrow.is_on(0)
                right = saks.tactrow.is_on(1)

                if ball_pos <= 1.0:
                    if left:
                        ball_dir = 1
                        rally_count += 1
                        speed = max(MAX_SPEED, INITIAL_SPEED - rally_count * SPEED_INCREASE)
                        hit_animation(saks)
                    elif ball_pos <= 0:
                        # 左方失分
                        score_right += 1
                        score_animation(saks)
                        print(f"  比分: {score_left}:{score_right}")
                        serve_ball("right")
                        time.sleep(0.5)
                elif ball_pos >= 7.0:
                    if right:
                        ball_dir = -1
                        rally_count += 1
                        speed = max(MAX_SPEED, INITIAL_SPEED - rally_count * SPEED_INCREASE)
                        hit_animation(saks)
                    elif ball_pos >= 7.5:
                        # 右方失分
                        score_left += 1
                        score_animation(saks)
                        print(f"  比分: {score_left}:{score_right}")
                        serve_ball("left")
                        time.sleep(0.5)

                # 显示球
                pos_int = int(ball_pos)
                pos_int = max(0, min(7, pos_int))
                row = [False] * 8
                row[pos_int] = True
                saks.ledrow.set_row(row)

            time.sleep(0.01)

    except KeyboardInterrupt:
        print(f"\n\n  游戏结束。比分: {score_left}:{score_right}")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()