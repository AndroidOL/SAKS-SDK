#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 10: 蜂鸣器深度解析.

深入探索蜂鸣器的原理和控制，包括:
  - 蜂鸣器原理说明 (有源/无源、电平触发)
  - beep() 演示: 不同时长
  - beep_pattern() 演示: 不同节奏 (SOS, 莫尔斯码等)
  - 节奏表: 快节奏(0.02/0.02)、中速(0.1/0.1)、慢速(0.5/0.2)
  - 参数说明: on_time, off_time, repeat
  - 异常处理: 无效参数
  - GPIO 电平说明 (HIGH/LOW 触发)

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/10_buzzer_deep_dive.py
"""

import time
import sys
import signal

from sakshat import Buzzer, SAKSPins
from sakshat._gpio import GPIO


# ==============================================================================
#  蜂鸣器原理说明
# ==============================================================================
BUZZER_PRINCIPLE = r"""
  蜂鸣器原理说明
  =============================================

  1. 蜂鸣器类型
  ─────────────
  有源蜂鸣器 (Active Buzzer):
    - 内置振荡电路，通电即响
    - 只需提供直流电平 (HIGH 或 LOW)
    - 频率固定，不可调音
    - SAKS 扩展板使用有源蜂鸣器

  无源蜂鸣器 (Passive Buzzer):
    - 无内置振荡电路，需要外部 PWM 信号
    - 可通过改变 PWM 频率调节音调
    - 适合播放音乐旋律

  2. 电平触发方式
  ────────────────
  HIGH 电平触发 (active_level=GPIO.HIGH):
    - GPIO 输出 HIGH 时蜂鸣器响
    - GPIO 输出 LOW 时蜂鸣器停
    - 默认模式

  LOW 电平触发 (active_level=GPIO.LOW):
    - GPIO 输出 LOW 时蜂鸣器响
    - GPIO 输出 HIGH 时蜂鸣器停
    - SAKS 扩展板默认使用此模式

  3. SAKS 扩展板蜂鸣器
  ─────────────────────
  - 引脚: SAKSPins.BUZZER (BCM 12)
  - 类型: 有源蜂鸣器
  - 触发: 低电平触发 (active_level=GPIO.LOW)
  - 控制: on() 开启, off() 关闭, beep() 单次, beep_pattern() 节奏

  4. 控制方法
  ───────────
  on()              -- 开启蜂鸣器 (持续响，需手动关闭)
  off()             -- 关闭蜂鸣器
  beep(seconds)     -- 蜂鸣指定时长后自动关闭
  beep_pattern(on, off, repeat) -- 按节奏重复蜂鸣
"""


# ==============================================================================
#  beep() 演示: 不同时长
# ==============================================================================
def demo_beep(buzzer: Buzzer) -> None:
    """演示 beep() 方法: 蜂鸣器响指定时长后自动关闭.

    beep(seconds) 是最基本的蜂鸣操作:
      - seconds > 0: 蜂鸣器响 seconds 秒后自动关闭
      - seconds <= 0: 抛出 SAKSValidationError 异常
    """
    print("\n" + "=" * 65)
    print("  演示: beep(seconds) -- 不同时长蜂鸣")
    print("=" * 65)

    # 演示 1: 短促蜂鸣 (0.05 秒)
    print("\n  [1] 短促蜂鸣: beep(0.05) -- 类似按键音")
    buzzer.beep(0.05)
    time.sleep(0.3)

    # 演示 2: 中等蜂鸣 (0.2 秒)
    print("  [2] 中等蜂鸣: beep(0.2) -- 提示音")
    buzzer.beep(0.2)
    time.sleep(0.3)

    # 演示 3: 长蜂鸣 (0.5 秒)
    print("  [3] 长蜂鸣: beep(0.5) -- 警告音")
    buzzer.beep(0.5)
    time.sleep(0.3)

    # 演示 4: 超长蜂鸣 (1.0 秒)
    print("  [4] 超长蜂鸣: beep(1.0) -- 持续警报")
    buzzer.beep(1.0)
    time.sleep(0.5)

    # 演示 5: 从短到长的渐变
    print("\n  [5] 时长渐变: 0.03s -> 0.06s -> 0.1s -> 0.2s -> 0.4s -> 0.8s")
    for duration in [0.03, 0.06, 0.1, 0.2, 0.4, 0.8]:
        print(f"      beep({duration})")
        buzzer.beep(duration)
        time.sleep(0.15)

    # 演示 6: 异常处理 -- 无效参数
    print("\n  [6] 异常处理: 无效参数")
    invalid_params = [0, -0.1, -1]
    for val in invalid_params:
        try:
            buzzer.beep(val)
        except Exception as e:
            print(f"      beep({val}) -> 异常: {e}")

    print("  演示完成!")


# ==============================================================================
#  beep_pattern() 演示: 不同节奏
# ==============================================================================
def demo_beep_pattern(buzzer: Buzzer) -> None:
    """演示 beep_pattern() 方法: 按指定节奏重复蜂鸣.

    beep_pattern(on_time, off_time, repeat):
      - on_time: 每次蜂鸣持续时间 (秒), 必须 > 0
      - off_time: 两次蜂鸣之间的间隔 (秒), 必须 > 0
      - repeat: 重复次数, 必须为正整数

    参数说明:
      - 总耗时 ≈ (on_time + off_time) * repeat
      - on_time 和 off_time 共同决定节奏感
      - repeat 控制蜂鸣次数
    """
    print("\n" + "=" * 65)
    print("  演示: beep_pattern(on_time, off_time, repeat) -- 节奏蜂鸣")
    print("=" * 65)

    # 演示 1: 快节奏 (0.02/0.02) -- 类似电子表闹钟
    print("\n  [1] 快节奏: beep_pattern(0.02, 0.02, 10) -- 电子表闹钟")
    print("      on_time=0.02s, off_time=0.02s, repeat=10")
    print("      总耗时约 (0.02+0.02)*10 = 0.4s")
    buzzer.beep_pattern(0.02, 0.02, 10)
    time.sleep(0.5)

    # 演示 2: 中速节奏 (0.1/0.1) -- 设备提示音
    print("\n  [2] 中速节奏: beep_pattern(0.1, 0.1, 5) -- 设备提示音")
    print("      on_time=0.1s, off_time=0.1s, repeat=5")
    print("      总耗时约 (0.1+0.1)*5 = 1.0s")
    buzzer.beep_pattern(0.1, 0.1, 5)
    time.sleep(0.5)

    # 演示 3: 慢速节奏 (0.5/0.2) -- 警告音
    print("\n  [3] 慢速节奏: beep_pattern(0.5, 0.2, 3) -- 警告音")
    print("      on_time=0.5s, off_time=0.2s, repeat=3")
    print("      总耗时约 (0.5+0.2)*3 = 2.1s")
    buzzer.beep_pattern(0.5, 0.2, 3)
    time.sleep(0.5)

    # 演示 4: SOS 莫尔斯码 (三短三长三短)
    print("\n  [4] SOS 莫尔斯码: ... --- ...")
    print("      短: 0.1s, 长: 0.3s, 间隔: 0.1s, 字符间隔: 0.3s")
    # S: 三个短
    for _ in range(3):
        buzzer.beep(0.1)
        time.sleep(0.1)
    time.sleep(0.3)  # 字符间隔
    # O: 三个长
    for _ in range(3):
        buzzer.beep(0.3)
        time.sleep(0.1)
    time.sleep(0.3)  # 字符间隔
    # S: 三个短
    for _ in range(3):
        buzzer.beep(0.1)
        time.sleep(0.1)
    time.sleep(0.5)

    # 演示 5: 自定义莫尔斯码 "SAKS"
    print("\n  [5] 莫尔斯码 'SAKS'")
    print("      S: ...  A: .-  K: -.-  S: ...")
    morse = {
        "S": [(0.1, 1), (0.1, 1), (0.1, 3)],   # 短 短 短
        "A": [(0.1, 1), (0.3, 3)],              # 短 长
        "K": [(0.3, 1), (0.1, 1), (0.3, 3)],   # 长 短 长
    }
    for char in ["S", "A", "K", "S"]:
        print(f"      发送 '{char}': ", end="", flush=True)
        for duration, gap in morse[char]:
            buzzer.beep(duration)
            print("." if duration < 0.2 else "-", end="", flush=True)
            time.sleep(gap * 0.1)
        print()
    time.sleep(0.5)

    # 演示 6: 倒计时结束提示 (3-2-1 然后长响)
    print("\n  [6] 倒计时结束提示: 3-2-1 + 长响")
    for count in [3, 2, 1]:
        print(f"      {count}...")
        buzzer.beep(0.1)
        time.sleep(0.9)
    print("      时间到!")
    buzzer.beep(1.0)
    time.sleep(0.5)

    print("  演示完成!")


# ==============================================================================
#  节奏表
# ==============================================================================
def print_rhythm_table() -> None:
    """打印节奏表: 快节奏、中速、慢速."""
    print("\n" + "=" * 65)
    print("  蜂鸣节奏参考表")
    print("=" * 65)
    print(f"  {'节奏名称':<14} {'on_time':<10} {'off_time':<10} {'repeat':<8} {'总耗时':<10} {'应用场景'}")
    print("  " + "-" * 55)

    rhythms = [
        ("超快", 0.01, 0.01, 20, "按键反馈"),
        ("快节奏", 0.02, 0.02, 10, "电子表闹钟"),
        ("中等偏快", 0.05, 0.05, 5, "通知提示"),
        ("中速", 0.1, 0.1, 3, "设备提示音"),
        ("中等偏慢", 0.2, 0.15, 3, "门铃"),
        ("慢速", 0.5, 0.2, 3, "警告音"),
        ("超慢", 1.0, 0.5, 2, "紧急警报"),
    ]

    for name, on_t, off_t, rep, scene in rhythms:
        total = (on_t + off_t) * rep
        print(f"  {name:<14} {on_t:<10.2f} {off_t:<10.2f} {rep:<8} {total:<10.2f} {scene}")

    print("  " + "-" * 55)
    print("  注: 总耗时 = (on_time + off_time) * repeat，实际可能略有偏差")


# ==============================================================================
#  GPIO 电平说明
# ==============================================================================
def print_gpio_level_info() -> None:
    """打印 GPIO 电平说明 (HIGH/LOW 触发)."""
    print("\n" + "=" * 65)
    print("  GPIO 电平触发说明")
    print("=" * 65)
    print("""
  GPIO.HIGH 触发 (active_level=GPIO.HIGH):
    ┌─────────────────────────────────────┐
    │ GPIO 输出 HIGH (3.3V) -> 蜂鸣器响   │
    │ GPIO 输出 LOW  (0V)   -> 蜂鸣器停   │
    │ 初始化: Buzzer(pin, active_level=GPIO.HIGH) │
    └─────────────────────────────────────┘

  GPIO.LOW 触发 (active_level=GPIO.LOW):
    ┌─────────────────────────────────────┐
    │ GPIO 输出 LOW  (0V)   -> 蜂鸣器响   │
    │ GPIO 输出 HIGH (3.3V) -> 蜂鸣器停   │
    │ 初始化: Buzzer(pin, active_level=GPIO.LOW)  │
    └─────────────────────────────────────┘

  SAKS 扩展板使用 LOW 触发:
    - 蜂鸣器一端接 VCC (3.3V)，另一端接 GPIO
    - GPIO 输出 LOW 时形成回路，电流流过蜂鸣器 -> 发声
    - GPIO 输出 HIGH 时两端等电位，无电流 -> 不发声

  注意: GPIO.HIGH = 1, GPIO.LOW = 0
""")


# ==============================================================================
#  on()/off() 手动控制演示
# ==============================================================================
def demo_on_off_manual(buzzer: Buzzer) -> None:
    """演示 on() 和 off() 手动控制.

    与 beep() 不同，on() 不会自动关闭，需要手动调用 off()。
    """
    print("\n" + "=" * 65)
    print("  演示: on() / off() -- 手动控制")
    print("=" * 65)

    # 演示 1: 手动开关
    print("\n  [1] 手动开关: on() 2 秒后 off()")
    print("      buzzer.on()")
    buzzer.on()
    print(f"      is_on={buzzer.is_on}")
    time.sleep(2)
    print("      buzzer.off()")
    buzzer.off()
    print(f"      is_on={buzzer.is_on}")
    time.sleep(0.5)

    # 演示 2: 快速切换
    print("\n  [2] 快速切换: on/off 交替 5 次")
    for i in range(5):
        buzzer.on()
        time.sleep(0.05)
        buzzer.off()
        time.sleep(0.05)
        print(f"      切换 {i + 1}/5", end="\r")
    print()

    # 演示 3: 与 beep() 的区别
    print("\n  [3] on() 与 beep() 的区别:")
    print("      on()  : 开启后持续响，需手动 off() 关闭")
    print("      beep(): 响指定时长后自动关闭")
    print("      beep(0.5) 等价于: on(); sleep(0.5); off()")

    print("  演示完成!")


# ==============================================================================
#  异常处理汇总
# ==============================================================================
def demo_error_handling(buzzer: Buzzer) -> None:
    """演示蜂鸣器的异常处理: 无效参数.

    beep() 和 beep_pattern() 都会对参数进行验证:
      - beep(seconds): seconds 必须 > 0
      - beep_pattern(on_time, off_time, repeat): 所有参数必须 > 0
    """
    print("\n" + "=" * 65)
    print("  异常处理汇总")
    print("=" * 65)

    print("\n  beep() 异常处理:")
    error_cases_beep = [
        ("beep(0)", 0),
        ("beep(-0.5)", -0.5),
        ("beep(-1)", -1),
    ]
    for desc, val in error_cases_beep:
        try:
            buzzer.beep(val)
            print(f"  {desc} -- 未抛出异常 (意外)")
        except Exception as e:
            print(f"  {desc} -- 抛出异常: {type(e).__name__}: {e}")

    print("\n  beep_pattern() 异常处理:")
    error_cases_pattern = [
        ("beep_pattern(0, 0.1, 3)", 0, 0.1, 3),
        ("beep_pattern(0.1, 0, 3)", 0.1, 0, 3),
        ("beep_pattern(0.1, 0.1, 0)", 0.1, 0.1, 0),
        ("beep_pattern(-0.1, 0.1, 3)", -0.1, 0.1, 3),
        ("beep_pattern(0.1, -0.1, 3)", 0.1, -0.1, 3),
        ("beep_pattern(0.1, 0.1, -1)", 0.1, 0.1, -1),
    ]
    for desc, on_t, off_t, rep in error_cases_pattern:
        try:
            buzzer.beep_pattern(on_t, off_t, rep)
            print(f"  {desc} -- 未抛出异常 (意外)")
        except Exception as e:
            print(f"  {desc} -- 抛出异常: {type(e).__name__}: {e}")

    print("  演示完成!")


# ==============================================================================
#  主函数
# ==============================================================================
def main() -> None:
    """主函数."""
    print("=" * 65)
    print("  SAKS SDK 示例 10: 蜂鸣器深度解析")
    print("=" * 65)

    # ---- 第一部分: 知识讲解 (无需硬件) ----
    print(BUZZER_PRINCIPLE)
    input("\n按 Enter 继续查看 GPIO 电平说明...")
    print_gpio_level_info()

    input("\n按 Enter 继续查看节奏表...")
    print_rhythm_table()

    # ---- 第二部分: 硬件演示 (需要树莓派 + SAKS 扩展板) ----
    print("\n" + "=" * 65)
    print("  以下演示需要硬件支持 (树莓派 + SAKS 扩展板)")
    print("=" * 65)

    # 初始化蜂鸣器 (SAKS 扩展板使用 LOW 电平触发)
    buzzer = Buzzer(SAKSPins.BUZZER, active_level=GPIO.LOW)

    try:
        input("\n按 Enter 开始 on()/off() 手动控制演示...")
        demo_on_off_manual(buzzer)

        input("\n按 Enter 开始 beep() 不同时长演示...")
        demo_beep(buzzer)

        input("\n按 Enter 开始 beep_pattern() 节奏蜂鸣演示...")
        demo_beep_pattern(buzzer)

        input("\n按 Enter 开始异常处理演示...")
        demo_error_handling(buzzer)

    except KeyboardInterrupt:
        print("\n\n演示被中断。")
    finally:
        buzzer.off()

    print("\n" + "=" * 65)
    print("  示例 10 完成!")
    print("=" * 65)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()