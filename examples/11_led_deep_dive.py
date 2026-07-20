#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 11: LED 深度解析.

深入探索 LED 的控制原理，包括:
  - LED 原理说明
  - LedRow 和 Led74HC595 的区别
  - set_row() 演示: 不同模式 (流水灯、二分频、全亮)
  - on_for_index()/off_for_index() 逐个控制
  - flash() 和 flash_pattern() 演示
  - 74HC595 移位寄存器原理简要说明
  - 数据格式: 0x00-0xFF 二进制对应 LED
  - 异常处理: 索引越界

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/11_led_deep_dive.py
"""

import time
import sys
import signal

from sakshat import Led, LedRow, Led74HC595, SAKSPins
from sakshat._gpio import GPIO


# ==============================================================================
#  LED 原理说明
# ==============================================================================
LED_PRINCIPLE = r"""
  LED 原理说明
  =============================================

  1. LED 基本电路
  ────────────────
  LED (Light Emitting Diode, 发光二极管) 是一种半导体器件，
  正向偏置时发光。基本控制方式:

    GPIO HIGH -> 限流电阻 -> LED 阳极 -> LED 阴极 -> GND
    (高电平触发, active_level=GPIO.HIGH)

    VCC -> LED 阳极 -> LED 阴极 -> 限流电阻 -> GPIO LOW
    (低电平触发, active_level=GPIO.LOW)

  2. SAKS 扩展板 LED 架构
  ─────────────────────────
  SAKS 扩展板上有 8 颗 LED，通过 74HC595 移位寄存器驱动。
  每颗 LED 对应一个 GPIO 输出位，由 74HC595 的 8 位并行输出控制。

  3. 控制方式对比
  ────────────────
  | 特性         | Led (单颗)      | LedRow (多颗)   | Led74HC595 (8颗)  |
  |-------------|----------------|----------------|-------------------|
  | 引脚数       | 1 个 GPIO       | N 个 GPIO       | 3 个 GPIO (DS/SHCP/STCP) |
  | 最大 LED 数  | 1              | 不限 (受 GPIO 限制) | 固定 8 路          |
  | 控制方式     | 直接 GPIO       | 直接 GPIO       | 移位寄存器 (串行)     |
  | 闪烁/呼吸灯  | flash/pulse    | 无 (由 Led 实现) | 无                |
  | 使用场景     | 状态指示灯       | 少量 LED 阵列   | 大量 LED 阵列       |
  | SAKS 使用    | 不直接使用       | 不直接使用       | 扩展板默认方案       |

  4. SAKS 扩展板 LED 引脚映射
  ─────────────────────────────
  74HC595 的 8 个输出 Q0-Q7 对应 8 颗 LED (索引 0-7):
    - 索引 0: 74HC595 Q0 (数据 bit 0)
    - 索引 1: 74HC595 Q1 (数据 bit 1)
    - 索引 2: 74HC595 Q2 (数据 bit 2)
    - 索引 3: 74HC595 Q3 (数据 bit 3)
    - 索引 4: 74HC595 Q4 (数据 bit 4)
    - 索引 5: 74HC595 Q5 (数据 bit 5)
    - 索引 6: 74HC595 Q6 (数据 bit 6)
    - 索引 7: 74HC595 Q7 (数据 bit 7)
"""


# ==============================================================================
#  74HC595 移位寄存器原理
# ==============================================================================
HC595_PRINCIPLE = r"""
  74HC595 移位寄存器原理简要说明
  =============================================

  74HC595 是一个 8 位串行输入、并行/串行输出的移位寄存器。
  通过 3 根信号线即可控制 8 路输出，极大节省 GPIO 引脚。

  引脚说明:
    DS   (SER, 数据输入)  -- 串行数据输入，每次送入 1 bit
    SHCP (SRCLK, 移位时钟) -- 上升沿将 DS 上的数据移入移位寄存器
    STCP (RCLK, 存储时钟)  -- 上升沿将移位寄存器的数据锁存到输出寄存器

  工作流程:
    1. 将 8 bit 数据逐位从 DS 送入 (每 bit 配合 SHCP 上升沿)
    2. 8 位数据全部送入后，触发 STCP 上升沿
    3. 输出寄存器更新，Q0-Q7 输出对应 bit 值

  数据格式 (0x00-0xFF):
    ┌──────────────────────────────────────────────────┐
    │  bit 7  bit 6  bit 5  bit 4  bit 3  bit 2  bit 1  bit 0 │
    │   Q7     Q6     Q5     Q4     Q3     Q2     Q1     Q0   │
    │  LED7   LED6   LED5   LED4   LED3   LED2   LED1   LED0  │
    └──────────────────────────────────────────────────┘

  示例:
    0x01 = 0b00000001 -> 仅 LED0 亮
    0x80 = 0b10000000 -> 仅 LED7 亮
    0xFF = 0b11111111 -> 全部 8 颗 LED 亮
    0xAA = 0b10101010 -> LED7,5,3,1 亮 (交替模式)
    0x55 = 0b01010101 -> LED6,4,2,0 亮 (交替模式)
    0x00 = 0b00000000 -> 全部熄灭
"""


# ==============================================================================
#  set_row() 演示: 不同模式
# ==============================================================================
def demo_set_row(leds: Led74HC595) -> None:
    """演示 set_row() 方法: 按状态列表设置 8 路 LED.

    set_row() 接受一个布尔值列表，True=亮, False=灭, None=不变。
    最多接受 8 个元素 (对应 8 路 LED)。
    """
    print("\n" + "=" * 65)
    print("  演示: set_row(status) -- 批量设置 LED 状态")
    print("=" * 65)

    # 演示 1: 流水灯 (逐个点亮后逐个熄灭)
    print("\n  [1] 流水灯: 从左到右逐个点亮")
    # 逐个点亮
    for i in range(8):
        status = [True if j <= i else False for j in range(8)]
        leds.set_row(status)
        print(f"      set_row({status})")
        time.sleep(0.15)
    # 逐个熄灭
    print("      从左到右逐个熄灭")
    for i in range(8):
        status = [False if j <= i else True for j in range(8)]
        leds.set_row(status)
        print(f"      set_row({status})")
        time.sleep(0.15)

    time.sleep(0.3)

    # 演示 2: 二分频模式 (交替闪烁)
    print("\n  [2] 二分频模式: 交替闪烁")
    for _ in range(3):
        leds.set_row([True, False, True, False, True, False, True, False])
        print("      set_row([T,F,T,F,T,F,T,F]) -- 0xAA")
        time.sleep(0.3)
        leds.set_row([False, True, False, True, False, True, False, True])
        print("      set_row([F,T,F,T,F,T,F,T]) -- 0x55")
        time.sleep(0.3)

    time.sleep(0.3)

    # 演示 3: 累加点亮 (二进制计数)
    print("\n  [3] 累加点亮: 二进制计数 0-7")
    for n in range(8):
        status = [(n >> i) & 1 == 1 for i in range(8)]
        value = sum((1 << i) for i, s in enumerate(status) if s)
        leds.set_row(status)
        print(f"      计数 {n}: set_row({status}) -> 0x{value:02X}")
        time.sleep(0.3)

    time.sleep(0.3)

    # 演示 4: 全亮 -> 全灭
    print("\n  [4] 全亮和全灭")
    leds.set_row([True] * 8)
    print("      set_row([T,T,T,T,T,T,T,T]) -- 全亮 (0xFF)")
    time.sleep(1)
    leds.set_row([False] * 8)
    print("      set_row([F,F,F,F,F,F,F,F]) -- 全灭 (0x00)")
    time.sleep(0.5)

    # 演示 5: None 保持当前状态不变
    print("\n  [5] None 保持状态不变")
    leds.set_row([True, False, False, False, False, False, False, False])
    print("      初始: [T,F,F,F,F,F,F,F]")
    time.sleep(0.5)
    leds.set_row([None, True, None, True, None, True, None, True])
    print("      更新: [None,T,None,T,None,T,None,T] -> 仅改变索引 1,3,5,7")
    print(f"      结果: {leds.row_status}")
    time.sleep(1)

    leds.off()
    print("  演示完成!")


# ==============================================================================
#  on_for_index() / off_for_index() 逐个控制
# ==============================================================================
def demo_index_control(leds: Led74HC595) -> None:
    """演示 on_for_index() 和 off_for_index() 逐个控制.

    on_for_index(index):  打开指定索引的 LED (0-7)
    off_for_index(index): 关闭指定索引的 LED (0-7)
    """
    print("\n" + "=" * 65)
    print("  演示: on_for_index() / off_for_index() -- 逐个控制")
    print("=" * 65)

    # 演示 1: 逐个点亮
    print("\n  [1] 逐个点亮 (索引 0-7)")
    for i in range(8):
        leds.on_for_index(i)
        print(f"      on_for_index({i}) -> row_status={leds.row_status}")
        time.sleep(0.2)

    time.sleep(0.3)

    # 演示 2: 逐个熄灭 (反向)
    print("\n  [2] 逐个熄灭 (索引 7-0)")
    for i in range(7, -1, -1):
        leds.off_for_index(i)
        print(f"      off_for_index({i}) -> row_status={leds.row_status}")
        time.sleep(0.2)

    time.sleep(0.3)

    # 演示 3: 跳变控制 (索引 0,2,4,6 亮, 1,3,5,7 灭)
    print("\n  [3] 跳变控制: 偶数索引亮, 奇数索引灭")
    for i in range(8):
        if i % 2 == 0:
            leds.on_for_index(i)
        else:
            leds.off_for_index(i)
    print(f"      结果: {leds.row_status}")
    time.sleep(1)

    # 交换: 奇数亮, 偶数灭
    print("      交换: 奇数索引亮, 偶数索引灭")
    for i in range(8):
        if i % 2 == 1:
            leds.on_for_index(i)
        else:
            leds.off_for_index(i)
    print(f"      结果: {leds.row_status}")
    time.sleep(1)

    # 演示 4: 逐位翻转
    print("\n  [4] 逐位翻转: 每次翻转一个 LED")
    leds.off()
    for i in range(8):
        leds.on_for_index(i)
        time.sleep(0.1)
        leds.off_for_index(i)
        time.sleep(0.05)
        leds.on_for_index(i)
        time.sleep(0.1)
        leds.off_for_index(i)
    # 再来一次反向
    for i in range(6, -1, -1):
        leds.on_for_index(i)
        time.sleep(0.1)
        leds.off_for_index(i)
        time.sleep(0.05)

    leds.off()
    print("  演示完成!")


# ==============================================================================
#  flash() 和 flash_pattern() 演示 (使用单颗 Led)
# ==============================================================================
def demo_flash_and_pattern() -> None:
    """演示单颗 LED 的 flash() 和 flash_pattern() 方法.

    这些方法仅在 Led 类上可用，不在 Led74HC595 上。
    因此需要使用独立的 Led 实例来演示。

    flash(seconds):       LED 亮起指定时间后自动熄灭
    flash_pattern(on, off, repeat): 按节奏重复闪烁
    """
    print("\n" + "=" * 65)
    print("  演示: flash() 和 flash_pattern() -- 单颗 LED 闪烁")
    print("=" * 65)
    print("  注意: flash()/flash_pattern() 仅在 Led 类上可用")
    print("        Led74HC595 不支持这些方法 (使用 beep_pattern 替代逻辑)")

    # 使用单颗 Led 演示 (使用任意 GPIO 引脚)
    # 此演示仅用于展示 API，在实际树莓派上会真实控制 LED
    try:
        led = Led(SAKSPins.IC_74HC595_DS, active_level=GPIO.HIGH)
    except Exception:
        print("  [提示] 无法创建 Led 实例，仅展示 API 用法")
        print("\n  flash() 用法:")
        print("    led = Led(pin=6)")
        print("    led.flash(0.5)      # LED 亮 0.5 秒后熄灭")
        print("    led.flash(1.0)      # LED 亮 1.0 秒后熄灭")
        print("    led.flash(0.1)      # LED 短暂闪烁")
        print("\n  flash_pattern() 用法:")
        print("    led.flash_pattern(0.1, 0.1, 5)  # 快闪 5 次")
        print("    led.flash_pattern(0.5, 0.2, 3)  # 慢闪 3 次")
        print("    led.flash_pattern(0.02, 0.02, 10)  # 极快闪 10 次")
        return

    try:
        # 演示 1: flash() 不同时长
        print("\n  [1] flash() 不同时长:")
        for duration in [0.05, 0.1, 0.2, 0.5]:
            print(f"      flash({duration})")
            led.flash(duration)
            time.sleep(0.2)

        # 演示 2: flash_pattern() 不同节奏
        print("\n  [2] flash_pattern() 不同节奏:")
        print("      快闪: flash_pattern(0.05, 0.05, 5)")
        led.flash_pattern(0.05, 0.05, 5)
        time.sleep(0.5)

        print("      中速: flash_pattern(0.2, 0.2, 3)")
        led.flash_pattern(0.2, 0.2, 3)
        time.sleep(0.5)

        print("      慢闪: flash_pattern(0.5, 0.3, 3)")
        led.flash_pattern(0.5, 0.3, 3)

        # 演示 3: 异常处理
        print("\n  [3] 异常处理:")
        try:
            led.flash(0)
        except Exception as e:
            print(f"      flash(0) -> {type(e).__name__}: {e}")

        try:
            led.flash_pattern(0, 0.1, 3)
        except Exception as e:
            print(f"      flash_pattern(0, 0.1, 3) -> {type(e).__name__}: {e}")

    finally:
        led.off()

    print("  演示完成!")


# ==============================================================================
#  数据格式: 0x00-0xFF 二进制对应 LED
# ==============================================================================
def print_data_format_table() -> None:
    """打印数据格式表: 0x00-0xFF 二进制对应 LED."""
    print("\n" + "=" * 65)
    print("  数据格式: 0x00-0xFF 二进制对应 LED (Led74HC595)")
    print("=" * 65)
    print(f"  {'Hex':<8} {'二进制 (Q7-Q0)':<24} {'点亮 LED 索引'}")
    print("  " + "-" * 55)

    examples = [
        (0x00, "全部熄灭"),
        (0x01, "仅 LED0"),
        (0x02, "仅 LED1"),
        (0x04, "仅 LED2"),
        (0x08, "仅 LED3"),
        (0x10, "仅 LED4"),
        (0x20, "仅 LED5"),
        (0x40, "仅 LED6"),
        (0x80, "仅 LED7"),
        (0x03, "LED0, LED1"),
        (0x0F, "LED0-LED3"),
        (0xF0, "LED4-LED7"),
        (0x55, "LED0,2,4,6 (偶数)"),
        (0xAA, "LED1,3,5,7 (奇数)"),
        (0xFF, "全部 8 颗 LED"),
    ]

    for hex_val, desc in examples:
        bin_str = f"0b{hex_val:08b}"
        # 找出所有点亮的 LED 索引
        lit_indices = [str(i) for i in range(8) if (hex_val >> i) & 1]
        indices_str = ", ".join(lit_indices) if lit_indices else "(无)"
        print(f"  0x{hex_val:02X}    {bin_str:<24} {indices_str:<20} ({desc})")

    print("  " + "-" * 55)
    print("  位映射: bit 0 = Q0 = LED0, bit 1 = Q1 = LED1, ...")
    print("  注意: 74HC595 的 Q0-Q7 对应 SAKS 板的 LED 索引 0-7")


# ==============================================================================
#  异常处理: 索引越界
# ==============================================================================
def demo_error_handling_led(leds: Led74HC595) -> None:
    """演示 LED 控制的异常处理: 索引越界.

    on_for_index() 和 off_for_index() 会验证索引范围:
      - Led74HC595: 索引必须在 0-7 范围内
      - LedRow: 索引必须在 0-len(leds)-1 范围内
    """
    print("\n" + "=" * 65)
    print("  异常处理: 索引越界")
    print("=" * 65)

    print("\n  Led74HC595 索引范围: 0-7")
    error_cases = [-1, 8, 100, -100]
    for idx in error_cases:
        try:
            leds.on_for_index(idx)
            print(f"  on_for_index({idx}) -- 未抛出异常 (意外)")
        except Exception as e:
            print(f"  on_for_index({idx}) -- 抛出异常: {type(e).__name__}: {e}")

    print("\n  is_on() 索引越界返回 False (不抛异常):")
    for idx in [-1, 8, 100]:
        result = leds.is_on(idx)
        print(f"  is_on({idx}) = {result}")

    print("\n  set_row() 超出部分自动忽略 (不抛异常):")
    print("  set_row([T,F,T,F,T,F,T,F,T,F]) -> 只取前 8 个")
    leds.set_row([True, False, True, False, True, False, True, False, True, False])
    print(f"  结果: {leds.row_status}")

    print("  演示完成!")


# ==============================================================================
#  LedRow 演示 (对比 Led74HC595)
# ==============================================================================
def demo_ledrow_comparison() -> None:
    """演示 LedRow 与 Led74HC595 的区别.

    LedRow 直接使用 GPIO 控制多个 LED，每个 LED 占用一个 GPIO 引脚。
    Led74HC595 通过移位寄存器，仅需 3 个 GPIO 引脚控制 8 个 LED。
    """
    print("\n" + "=" * 65)
    print("  LedRow vs Led74HC595 对比演示")
    print("=" * 65)

    print("""
  LedRow:
    - 直接 GPIO 控制，每个 LED 一个引脚
    - 初始化: LedRow([pin1, pin2, ...])
    - 支持任意数量 LED (受 GPIO 限制)
    - 每个 LED 是 Led 实例，支持 flash()/flash_pattern()/pulse()
    - 通过 items 属性访问单个 Led

  Led74HC595:
    - 通过 74HC595 移位寄存器控制
    - 初始化: Led74HC595(ds=pin, shcp=pin, stcp=pin)
    - 固定 8 路 LED
    - 不支持 flash()/flash_pattern()/pulse()
    - 通过 ic.data 属性查看/设置原始数据

  SAKS 扩展板使用 Led74HC595 作为默认方案。
""")

    # 尝试创建 LedRow 示例 (仅展示 API)
    print("  LedRow API 示例 (仅展示，不执行):")
    print("    from sakshat import LedRow, Led")
    print("    row = LedRow([6, 19, 13, 26])  # 4 颗 LED")
    print("    row.on()                         # 全部点亮")
    print("    row.off()                        # 全部熄灭")
    print("    row.on_for_index(0)              # 点亮第 0 颗")
    print("    row.off_for_index(2)             # 熄灭第 2 颗")
    print("    row.set_row([True, False, True, False])")
    print("    row.items[0].flash(0.5)          # 第 0 颗闪烁 0.5s")
    print("    row.items[1].flash_pattern(0.1, 0.1, 5)")
    print("    row.items[2].pulse()             # 第 2 颗呼吸灯")

    print("  演示完成!")


# ==============================================================================
#  主函数
# ==============================================================================
def main() -> None:
    """主函数."""
    print("=" * 65)
    print("  SAKS SDK 示例 11: LED 深度解析")
    print("=" * 65)

    # ---- 第一部分: 知识讲解 (无需硬件) ----
    print(LED_PRINCIPLE)
    input("\n按 Enter 继续查看 74HC595 移位寄存器原理...")
    print(HC595_PRINCIPLE)

    input("\n按 Enter 继续查看数据格式表...")
    print_data_format_table()

    input("\n按 Enter 继续查看 LedRow vs Led74HC595 对比...")
    demo_ledrow_comparison()

    # ---- 第二部分: 硬件演示 (需要树莓派 + SAKS 扩展板) ----
    print("\n" + "=" * 65)
    print("  以下演示需要硬件支持 (树莓派 + SAKS 扩展板)")
    print("=" * 65)

    # 初始化 74HC595 LED 阵列 (SAKS 扩展板默认方案)
    leds = Led74HC595(
        ds=SAKSPins.IC_74HC595_DS,
        shcp=SAKSPins.IC_74HC595_SHCP,
        stcp=SAKSPins.IC_74HC595_STCP,
        active_level=GPIO.HIGH,
    )

    try:
        input("\n按 Enter 开始 set_row() 演示...")
        demo_set_row(leds)

        input("\n按 Enter 开始 on_for_index()/off_for_index() 演示...")
        demo_index_control(leds)

        input("\n按 Enter 开始 flash() 和 flash_pattern() 演示...")
        demo_flash_and_pattern()

        input("\n按 Enter 开始异常处理演示...")
        demo_error_handling_led(leds)

    except KeyboardInterrupt:
        print("\n\n演示被中断。")
    finally:
        leds.off()

    print("\n" + "=" * 65)
    print("  示例 11 完成!")
    print("=" * 65)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()