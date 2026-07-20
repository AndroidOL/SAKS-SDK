#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 25: 电子密码锁.

用拨码开关设定 2 位密码 (00-11)，按键输入密码。
LED 和蜂鸣器反馈验证结果。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/25_password_lock.py
"""

import time
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 全局状态 ----
locked: bool = True
attempt_count: int = 0
beep_requested: bool = False
user_input: list[bool] = [False, False]


def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关输入密码."""
    global user_input, beep_requested
    if not status:
        return
    if pin == SAKSPins.TACT_LEFT:
        user_input = [True, False]
        beep_requested = True
    elif pin == SAKSPins.TACT_RIGHT:
        user_input = [False, True]
        beep_requested = True


def flash_leds(saks: SAKSHAT, count: int, delay: float = 0.1) -> None:
    """LED 闪烁."""
    for _ in range(count):
        saks.ledrow.on()
        time.sleep(delay)
        saks.ledrow.off()
        time.sleep(delay)


def unlock_animation(saks: SAKSHAT) -> None:
    """解锁动画: LED 从中间向外扩散."""
    for i in range(4):
        row = [False] * 8
        row[3 - i] = True
        row[4 + i] = True
        saks.ledrow.set_row(row)
        time.sleep(0.08)
    saks.ledrow.on()
    time.sleep(0.3)
    saks.ledrow.off()


def lock_animation(saks: SAKSHAT) -> None:
    """锁定动画: LED 从外向内收缩."""
    for i in range(4):
        row = [False] * 8
        row[i] = True
        row[7 - i] = True
        saks.ledrow.set_row(row)
        time.sleep(0.08)
    saks.ledrow.off()


def main() -> None:
    """主函数."""
    global locked, attempt_count, beep_requested, user_input

    print("=" * 58)
    print("  SAKS SDK 示例 25: 电子密码锁")
    print("=" * 58)
    print()
    print("  规则说明:")
    print("    拨码开关设定密码 (2位, 00/01/10/11)")
    print("    左键 (TACT_LEFT)  = 输入 01")
    print("    右键 (TACT_RIGHT) = 输入 10")
    print("    两位同时按下 = 输入 11")
    print("    密码匹配: LED 扩散 + 短哔 → 解锁")
    print("    密码错误: LED 闪烁 + 长哔 → 锁定")
    print("    连续 3 次错误: 锁定 5 秒")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()
    saks.tact_event_handler = on_tact_event

    try:
        # 初始状态
        locked = True
        saks.digital_display.show("LOCK")
        saks.ledrow.off()

        print("  系统已锁定，请输入密码...")

        while True:
            # 读取密码设定
            password = saks.dip_switch.is_on  # [S1, S2]
            pwd_str = f"{'1' if password[0] else '0'}{'1' if password[1] else '0'}"

            # 显示锁定状态
            if locked:
                # 轮询按键
                left = saks.tactrow.is_on(0)
                right = saks.tactrow.is_on(1)

                if left and right:
                    user_input = [True, True]
                elif left:
                    user_input = [True, False]
                elif right:
                    user_input = [False, True]
                else:
                    user_input = [False, False]

                if beep_requested:
                    beep_requested = False

                    if user_input == password:
                        # 密码正确
                        locked = False
                        attempt_count = 0
                        saks.digital_display.show("OPEN")
                        unlock_animation(saks)
                        saks.buzzer.beep(0.05)
                        print(f"  ✅ 密码正确 ({pwd_str})，已解锁！")
                    else:
                        # 密码错误
                        attempt_count += 1
                        saks.digital_display.show("Err")
                        flash_leds(saks, 3, 0.1)
                        saks.buzzer.beep(0.3)
                        user_str = f"{'1' if user_input[0] else '0'}{'1' if user_input[1] else '0'}"
                        print(f"  ❌ 密码错误 (输入: {user_str}, 期望: {pwd_str}) "
                              f"第 {attempt_count} 次")

                        if attempt_count >= 3:
                            print("  ⚠️  连续 3 次错误，锁定 5 秒...")
                            saks.digital_display.show("____")
                            saks.buzzer.beep_pattern(0.1, 0.1, 3)
                            time.sleep(5)
                            attempt_count = 0
                            print("  锁定解除，请重试。")

                        saks.digital_display.show("LOCK")

                    user_input = [False, False]

            else:
                # 已解锁，显示当前密码
                saks.digital_display.show(f"P{pwd_str}")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n  密码锁已停止。")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()