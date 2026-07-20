#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 38: 拆弹专家 (Bomb Defusal).

LED 显示炸弹引线，倒计时滴答声越来越快。
必须在正确的时间剪断正确的线（按键），否则炸弹爆炸！

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/38_bomb_defusal.py
"""

import time
import random
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 游戏常量 ----
BOMB_TIME: int = 30  # 炸弹倒计时 (秒)
WIRES: int = 8       # 8 根引线

time_left: float = BOMB_TIME
cut_wires: list[int] = []
correct_order: list[int] = []
next_wire: int = 0
game_active: bool = False
game_start: float = 0.0
score: int = 0
best: int = 0


def generate_bomb() -> None:
    """生成炸弹 (随机剪线顺序)."""
    global correct_order, next_wire, cut_wires, time_left
    correct_order = list(range(WIRES))
    random.shuffle(correct_order)
    next_wire = 0
    cut_wires = []
    time_left = BOMB_TIME


def show_bomb(saks: SAKSHAT) -> None:
    """显示炸弹状态."""
    row = [False] * 8
    for wire in cut_wires:
        row[wire] = False  # 已剪的线灭
    # 未剪的线亮
    for i in range(WIRES):
        if i not in cut_wires:
            row[i] = True
    # 当前要剪的线闪烁
    if next_wire < WIRES:
        target = correct_order[next_wire]
        if int(time.monotonic() * 4) % 2 == 0:
            row[target] = True
        else:
            row[target] = False
    saks.ledrow.set_row(row)


def explode(saks: SAKSHAT) -> None:
    """爆炸动画."""
    for _ in range(5):
        saks.ledrow.on()
        saks.buzzer.beep(0.1)
        time.sleep(0.08)
        saks.ledrow.off()
        time.sleep(0.08)
    saks.buzzer.beep(0.5)


def defused_animation(saks: SAKSHAT) -> None:
    """拆弹成功动画."""
    for i in range(8):
        row = [False] * 8
        row[i] = True
        saks.ledrow.set_row(row)
        saks.buzzer.beep(0.03)
        time.sleep(0.06)
    saks.ledrow.off()
    saks.buzzer.beep(0.2)


def main() -> None:
    """主函数."""
    global time_left, next_wire, cut_wires, game_active, game_start, score, best

    print("=" * 58)
    print("  SAKS SDK 示例 38: 拆弹专家 (Bomb Defusal)")
    print("=" * 58)
    print()
    print("  规则说明:")
    print("    8 根引线 (LED)，必须按正确顺序剪断")
    print("    闪烁的 LED = 当前要剪的线")
    print("    剪错线 = 炸弹爆炸！")
    print("    倒计时 30 秒内剪完所有线 = 拆弹成功")
    print()
    print("  操作说明:")
    print("    左键 (TACT_LEFT)  = 剪 LED 0-3")
    print("    右键 (TACT_RIGHT) = 剪 LED 4-7")
    print("    拨码切换当前剪线范围")
    print("    拨码 S1: 开始新炸弹")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()

    try:
        generate_bomb()
        saks.digital_display.show("BOMB")

        print("  拨码 S1 开始拆弹！")

        while True:
            if saks.dip_switch.is_on[0] and not game_active:
                game_active = True
                generate_bomb()
                game_start = time.monotonic()
                score = 0
                saks.digital_display.show(" 30")
                print("  炸弹已启动！30 秒倒计时！")
                time.sleep(0.3)

            if not game_active:
                time.sleep(0.1)
                continue

            now = time.monotonic()
            elapsed = now - game_start
            time_left = BOMB_TIME - elapsed

            # 倒计时
            saks.digital_display.show(f" {int(time_left):2d}{score:2d}")

            # 时间到 = 爆炸
            if time_left <= 0:
                explode(saks)
                print(f"  💥 BOOM！炸弹爆炸！")
                game_active = False
                saks.digital_display.show("BOOM")
                time.sleep(2)
                saks.digital_display.show("BOMB")
                continue

            show_bomb(saks)

            # 滴答声
            if time_left < 10:
                if int(time_left * 2) % 2 == 0:
                    saks.buzzer.beep(0.02)

            # 按键剪线
            left = saks.tactrow.is_on(0)
            right = saks.tactrow.is_on(1)

            if left or right:
                # 读取拨码选择具体剪哪根
                dip = saks.dip_switch.is_on
                if left:
                    # 左键: 剪 LED 0-3 中的一根
                    wire_choice = 0 if not dip[1] else 2
                else:
                    # 右键: 剪 LED 4-7 中的一根
                    wire_choice = 4 if not dip[1] else 6

                if wire_choice in cut_wires:
                    continue  # 已剪过

                expected = correct_order[next_wire]
                if wire_choice == expected:
                    # 正确
                    cut_wires.append(wire_choice)
                    next_wire += 1
                    score += 10
                    saks.buzzer.beep(0.03)
                    print(f"  ✅ 剪断线 #{wire_choice}，剩余 {WIRES - next_wire} 根")

                    if next_wire >= WIRES:
                        # 拆弹成功
                        bonus = int(time_left * 5)
                        score += bonus
                        defused_animation(saks)
                        if score > best:
                            best = score
                        print(f"  🎉 拆弹成功！得分: {score} (时间奖励: +{bonus})")
                        game_active = False
                        saks.digital_display.show(f"b{best:3d}")
                        time.sleep(2)
                        saks.digital_display.show("BOMB")
                else:
                    # 剪错 = 爆炸
                    explode(saks)
                    print(f"  💥 剪错线！剪了 #{wire_choice}，应该剪 #{expected}")
                    game_active = False
                    saks.digital_display.show("BOOM")
                    time.sleep(2)
                    saks.digital_display.show("BOMB")

                time.sleep(0.2)

            time.sleep(0.03)

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