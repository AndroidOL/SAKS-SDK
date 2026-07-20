#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 08: 74HC595 移位寄存器深度解析.

本示例深入讲解 74HC595 芯片的工作原理、时序控制、数据格式，
以及 IC74HC595 和 Led74HC595 两个类的使用方法。

74HC595 是一款 8 位串行输入、并行输出（SIPO）移位寄存器芯片。
它通过仅 3 根 GPIO 引脚即可控制 8 路并行输出，极大节省 GPIO 资源。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/08_74hc595_deep_dive.py
"""

import time
import sys
import signal

from sakshat import IC74HC595, Led74HC595, SAKSValidationError


# ============================================================================
# 第一部分: 74HC595 芯片原理说明
# ============================================================================

def print_chip_theory() -> None:
    """打印 74HC595 芯片原理说明."""
    print("=" * 66)
    print("  74HC595 移位寄存器 - 芯片原理深度解析")
    print("=" * 66)

    print("""
[1] 芯片概述
    74HC595 是一款 8 位串入并出（SIPO: Serial-In, Parallel-Out）移位寄存器。
    它内部包含一个 8 位移位寄存器和一个 8 位存储寄存器，通过三线接口控制。

    核心原理:
    - 串行数据通过 DS 引脚逐位输入
    - SHCP 时钟信号驱动数据在移位寄存器中逐位移动
    - STCP 锁存信号将移位寄存器的数据一次性输出到并行输出端

    优点: 仅需 3 根 GPIO 线即可控制 8 路输出，支持级联扩展更多输出。

[2] 三线控制接口
    +--------+---------+------------------------------------------+
    | 引脚名 | 别名    | 功能                                     |
    +--------+---------+------------------------------------------+
    | DS     | SER     | 串行数据输入 (Serial Data Input)          |
    | SHCP   | SRCLK   | 移位寄存器时钟 (Shift Register Clock)     |
    | STCP   | RCLK    | 存储寄存器时钟 / 锁存 (Register Clock)    |
    +--------+---------+------------------------------------------+

    工作流程:
    1. 将 1 bit 数据放到 DS 引脚
    2. 给 SHCP 一个上升沿脉冲，数据被移入移位寄存器
    3. 重复 8 次，8 位数据全部进入移位寄存器
    4. 给 STCP 一个上升沿脉冲，数据被锁存到并行输出

[3] 时序图 (ASCII)

    DS   ----X________X________X________X________X________X________X________X----
             D7       D6       D5       D4       D3       D2       D1       D0
             |        |        |        |        |        |        |        |
    SHCP ____|^^|_____|^^|_____|^^|_____|^^|_____|^^|_____|^^|_____|^^|_____|^^|____
             |  |     |  |     |  |     |  |     |  |     |  |     |  |     |  |
             |  +-----+  |     |  |     |  |     |  |     |  |     |  |     |  |
             |  移位脉冲  |     |  |     |  |     |  |     |  |     |  |     |  |
             |           +-----+  |     |  |     |  |     |  |     |  |     |  |
             |           数据移入 |     |  |     |  |     |  |     |  |     |  |
             |                   +-----+  |     |  |     |  |     |  |     |  |
             |                   ... 重复 8 次 ...  |     |  |     |  |     |  |
             |                                      +-----+  |     |  |     |  |
             |                                      最后一位  |     |  |     |  |
             |                                                +-----+  |     |  |
             |                                                锁存准备  |     |  |
             |                                                         +-----+  |
             |                                                         全部完成  |
             |                                                                   |
    STCP ____|___________________________________________________________|^^|________
                                                                          |
                                                                      锁存脉冲
                                                                      输出更新

    说明:
    - 数据在 SHCP 上升沿被采样并移入移位寄存器
    - 数据以 MSB 优先（高位先入）或 LSB 优先（低位先入，SAKS SDK 采用此方式）
    - STCP 上升沿将移位寄存器内容锁存到并行输出寄存器
    - 在 STCP 脉冲之前，并行输出保持不变（不会出现中间状态的闪烁）

[4] 数据与 LED 对应关系

    一个字节 (8 bits) 对应 8 个 LED 输出:

    +--------+-----+-----+-----+-----+-----+-----+-----+-----+
    | 数据位 | bit7| bit6| bit5| bit4| bit3| bit2| bit1| bit0|
    +--------+-----+-----+-----+-----+-----+-----+-----+-----+
    | LED    | LED7| LED6| LED5| LED4| LED3| LED2| LED1| LED0|
    +--------+-----+-----+-----+-----+-----+-----+-----+-----+
    | 十六进制示例:                                           |
    | 0x01   |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  1  |  -> 仅 LED0 亮
    | 0x80   |  1  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  -> 仅 LED7 亮
    | 0xAA   |  1  |  0  |  1  |  0  |  1  |  0  |  1  |  0  |  -> LED0,2,4,6 亮
    | 0x55   |  0  |  1  |  0  |  1  |  0  |  1  |  0  |  1  |  -> LED1,3,5,7 亮
    | 0xFF   |  1  |  1  |  1  |  1  |  1  |  1  |  1  |  1  |  -> 全部 LED 亮
    | 0x00   |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  -> 全部 LED 灭
    +--------+-----+-----+-----+-----+-----+-----+-----+-----+

    二进制直观表示:
    bit7 bit6 bit5 bit4 bit3 bit2 bit1 bit0
    LED7 LED6 LED5 LED4 LED3 LED2 LED1 LED0

    0x00 = 0b00000000  全部 LED 关闭
    0x01 = 0b00000001  LED0 亮
    0x02 = 0b00000010  LED1 亮
    0x04 = 0b00000100  LED2 亮
    0x08 = 0b00001000  LED3 亮
    0x10 = 0b00010000  LED4 亮
    0x20 = 0b00100000  LED5 亮
    0x40 = 0b01000000  LED6 亮
    0x80 = 0b10000000  LED7 亮
    0xFF = 0b11111111  全部 LED 亮

[5] 移位寄存器写入过程逐步演示 (以 0xAA = 0b10101010 为例)

    写入 0xAA (LSB 优先，即从 bit0 开始写入):

    初始状态: 移位寄存器 = ????????  (未知)
    并行输出  = ????????  (上一次锁存的值)

    步骤 1: DS=0 (bit0), SHCP 脉冲 -> 移位寄存器 = ???????0
    步骤 2: DS=1 (bit1), SHCP 脉冲 -> 移位寄存器 = ??????01
    步骤 3: DS=0 (bit2), SHCP 脉冲 -> 移位寄存器 = ??????010
    步骤 4: DS=1 (bit3), SHCP 脉冲 -> 移位寄存器 = ???? 0101
    步骤 5: DS=0 (bit4), SHCP 脉冲 -> 移位寄存器 = ??? 01010
    步骤 6: DS=1 (bit5), SHCP 脉冲 -> 移位寄存器 = ?? 010101
    步骤 7: DS=0 (bit6), SHCP 脉冲 -> 移位寄存器 = ? 0101010
    步骤 8: DS=1 (bit7), SHCP 脉冲 -> 移位寄存器 = 10101010

    完成后: STCP 脉冲 -> 并行输出 = 10101010 (LED0,2,4,6 亮)
""")


# ============================================================================
# 第二部分: IC74HC595 类演示
# ============================================================================

def demo_ic74hc595() -> None:
    """演示 IC74HC595 类的各种功能."""
    print("=" * 66)
    print("  IC74HC595 类 - 底层芯片控制演示")
    print("=" * 66)

    # 创建 IC74HC595 实例 (使用 SAKS 扩展板默认引脚)
    ic = IC74HC595(ds=6, shcp=19, stcp=13)
    print(f"\n创建芯片实例: {ic!r}")

    # 演示 set_data() 各种值
    print("\n[1] set_data() 各种值演示:")

    # 全部点亮
    print("\n  >>> ic.set_data(0xFF)   # 全部 LED 亮")
    ic.set_data(0xFF)
    print(f"  当前数据: 0x{ic.data:02X} = 0b{ic.data:08b}")
    time.sleep(0.5)

    # 全部熄灭
    print("\n  >>> ic.set_data(0x00)   # 全部 LED 灭")
    ic.set_data(0x00)
    print(f"  当前数据: 0x{ic.data:02X} = 0b{ic.data:08b}")
    time.sleep(0.3)

    # 交替模式 0xAA
    print("\n  >>> ic.set_data(0xAA)   # 交替模式 (LED0,2,4,6 亮)")
    ic.set_data(0xAA)
    print(f"  当前数据: 0x{ic.data:02X} = 0b{ic.data:08b}")
    time.sleep(0.5)

    # 交替模式 0x55
    print("\n  >>> ic.set_data(0x55)   # 互补交替模式 (LED1,3,5,7 亮)")
    ic.set_data(0x55)
    print(f"  当前数据: 0x{ic.data:02X} = 0b{ic.data:08b}")
    time.sleep(0.5)

    # 单个 LED 演示
    print("\n[2] 逐个 LED 点亮演示 (二进制位对应关系):")
    single_leds = [
        (0x01, 0, "0b00000001"),
        (0x02, 1, "0b00000010"),
        (0x04, 2, "0b00000100"),
        (0x08, 3, "0b00001000"),
        (0x10, 4, "0b00010000"),
        (0x20, 5, "0b00100000"),
        (0x40, 6, "0b01000000"),
        (0x80, 7, "0b10000000"),
    ]
    for value, led_idx, binary in single_leds:
        print(f"  >>> ic.set_data(0x{value:02X})  # {binary} -> LED{led_idx} 亮")
        ic.set_data(value)
        print(f"  当前数据: 0x{ic.data:02X} = 0b{ic.data:08b}")
        time.sleep(0.3)

    # clear() 方法
    print("\n[3] clear() 方法:")
    print("  >>> ic.clear()   # 所有输出清零")
    ic.clear()
    print(f"  当前数据: 0x{ic.data:02X} = 0b{ic.data:08b}")
    time.sleep(0.3)

    # 数据格式对照表
    print("\n[4] 数据格式对照表 (0x00 - 0xFF 二进制对应 LED):")
    print("  +--------+----------+------------------------------+")
    print("  | 十六进制 | 二进制    | LED 状态                      |")
    print("  +--------+----------+------------------------------+")
    test_values = [0x00, 0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF]
    for val in test_values:
        leds_on = [i for i in range(8) if (val >> i) & 1]
        led_str = ",".join(str(l) for l in leds_on) if leds_on else "无"
        print(f"  | 0x{val:02X}   | 0b{val:08b} | LED [{led_str}] 亮              |")
    print("  +--------+----------+------------------------------+")

    # 异常处理演示
    print("\n[5] 异常处理: 数据越界")
    print("  >>> try:")
    print("  ...     ic.set_data(0x100)  # 超出 0x00-0xFF 范围")
    try:
        ic.set_data(0x100)
    except SAKSValidationError as e:
        print(f"  捕获到 SAKSValidationError: {e}")

    print("  >>> try:")
    print("  ...     ic.set_data(-1)     # 负数")
    try:
        ic.set_data(-1)
    except SAKSValidationError as e:
        print(f"  捕获到 SAKSValidationError: {e}")

    # 最终清理
    ic.clear()
    print(f"\n  最终状态: {ic!r}")


# ============================================================================
# 第三部分: Led74HC595 类演示
# ============================================================================

def demo_led74hc595() -> None:
    """演示 Led74HC595 类的各种功能."""
    print("\n" + "=" * 66)
    print("  Led74HC595 类 - LED 阵列高层控制演示")
    print("=" * 66)

    # 创建 Led74HC595 实例
    leds = Led74HC595(ds=6, shcp=19, stcp=13)
    print(f"\n创建 LED 阵列实例: {leds!r}")

    # 演示 on() / off()
    print("\n[1] on() / off() 全亮全灭:")
    print("  >>> leds.on()    # 全部 LED 亮")
    leds.on()
    print(f"  状态: {leds!r}, row_status={leds.row_status}")
    time.sleep(0.5)

    print("  >>> leds.off()   # 全部 LED 灭")
    leds.off()
    print(f"  状态: {leds!r}, row_status={leds.row_status}")
    time.sleep(0.3)

    # 演示 on_for_index() / off_for_index()
    print("\n[2] on_for_index() / off_for_index() 单个 LED 控制:")
    for i in range(8):
        print(f"  >>> leds.on_for_index({i})   # 点亮 LED{i}")
        leds.on_for_index(i)
        print(f"  row_status={leds.row_status}")
        time.sleep(0.2)
        print(f"  >>> leds.off_for_index({i})  # 熄灭 LED{i}")
        leds.off_for_index(i)
        print(f"  row_status={leds.row_status}")
        time.sleep(0.1)

    # 演示 is_on()
    print("\n[3] is_on() 查询 LED 状态:")
    leds.on_for_index(0)
    leds.on_for_index(3)
    leds.on_for_index(7)
    for i in range(8):
        print(f"  leds.is_on({i}) = {leds.is_on(i)}")
    leds.off()

    # 演示 set_row()
    print("\n[4] set_row() 批量设置 LED 状态:")
    patterns = [
        ([True, False, True, False, True, False, True, False], "交替模式"),
        ([False, True, False, True, False, True, False, True], "互补交替"),
        ([True, True, True, True, False, False, False, False], "左4亮右4灭"),
        ([False, False, False, False, True, True, True, True], "左4灭右4亮"),
        ([True, False, False, False, False, False, False, True], "首尾亮"),
    ]
    for pattern, desc in patterns:
        print(f"  >>> leds.set_row({pattern})  # {desc}")
        leds.set_row(pattern)
        print(f"  row_status={leds.row_status}")
        time.sleep(0.4)

    # 演示 set_row() 的 None 行为
    print("\n[5] set_row() 中 None 值 (保持当前状态不变):")
    leds.set_row([True, False, True, False, True, False, True, False])
    print(f"  初始状态:    {leds.row_status}")
    leds.set_row([None, True, None, True, None, True, None, True])
    print(f"  None 更新后: {leds.row_status}")
    time.sleep(0.3)

    # 异常处理
    print("\n[6] 异常处理: 索引越界")
    print("  >>> try:")
    print("  ...     leds.on_for_index(8)   # 索引 8 超出 0-7")
    try:
        leds.on_for_index(8)
    except SAKSValidationError as e:
        print(f"  捕获到 SAKSValidationError: {e}")

    print("  >>> try:")
    print("  ...     leds.off_for_index(-1)  # 负数索引")
    try:
        leds.off_for_index(-1)
    except SAKSValidationError as e:
        print(f"  捕获到 SAKSValidationError: {e}")

    # 最终清理
    leds.off()
    print(f"\n  最终状态: {leds!r}")


# ============================================================================
# 第四部分: 移位寄存器写入过程逐步演示
# ============================================================================

def demo_shift_register_steps() -> None:
    """逐步演示移位寄存器写入过程."""
    print("\n" + "=" * 66)
    print("  移位寄存器写入过程逐步演示 (0xAA = 0b10101010)")
    print("=" * 66)

    ic = IC74HC595(ds=6, shcp=19, stcp=13)
    ic.clear()

    data = 0xAA  # 0b10101010
    print(f"\n写入数据: 0x{data:02X} = 0b{data:08b}")
    print(f"目标 LED 状态: LED0,2,4,6 亮, LED1,3,5,7 灭\n")

    # SAKS SDK 内部使用 LSB 优先方式写入
    print("LSB 优先写入过程 (从 bit0 开始):")
    print("+" + "-" * 62 + "+")
    print(f"| {'步骤':^6} | {'DS 值':^6} | {'移位后状态':^42} |")
    print("+" + "-" * 62 + "+")

    shift_register = 0
    for i in range(8):
        bit = (data >> i) & 0x01
        shift_register = (shift_register >> 1) | (bit << 7)
        # 构建显示: 仅显示当前已写入的位
        mask = (1 << (i + 1)) - 1
        visible = data & mask
        visible_bin = f"0b{visible:08b}"
        ds_bit = "1 (HIGH)" if bit else "0 (LOW)"
        print(f"| {i+1:^6} | {ds_bit:^6} | {visible_bin:^42} |")

    print("+" + "-" * 62 + "+")
    print(f"\n8 次移位完成后，STCP 锁存脉冲 -> 并行输出 = 0b{data:08b}")
    print(f"LED0,2,4,6 点亮")

    # 实际写入
    ic.set_data(data)
    print(f"\n实际写入后: ic.data = 0x{ic.data:02X} = 0b{ic.data:08b}")
    time.sleep(0.5)
    ic.clear()


# ============================================================================
# 第五部分: 综合演示
# ============================================================================

def demo_comprehensive() -> None:
    """综合演示: 使用 Led74HC595 实现流水灯效果."""
    print("\n" + "=" * 66)
    print("  综合演示: LED 流水灯效果")
    print("=" * 66)

    leds = Led74HC595(ds=6, shcp=19, stcp=13)

    print("\n[1] 从左到右流水灯:")
    for i in range(8):
        leds.off()
        leds.on_for_index(i)
        print(f"  LED{i} 亮 -> row_status={leds.row_status}")
        time.sleep(0.2)

    print("\n[2] 从右到左流水灯:")
    for i in range(7, -1, -1):
        leds.off()
        leds.on_for_index(i)
        print(f"  LED{i} 亮 -> row_status={leds.row_status}")
        time.sleep(0.2)

    print("\n[3] 累加点亮 (二进制计数):")
    for val in [0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF]:
        leds.ic.set_data(val)
        print(f"  0x{val:02X} = 0b{val:08b} -> row_status={leds.row_status}")
        time.sleep(0.3)

    print("\n[4] 逐个熄灭:")
    for val in [0x7F, 0x3F, 0x1F, 0x0F, 0x07, 0x03, 0x01, 0x00]:
        leds.ic.set_data(val)
        print(f"  0x{val:02X} = 0b{val:08b} -> row_status={leds.row_status}")
        time.sleep(0.3)

    print("\n[5] 蛇形闪烁:")
    for i in range(8):
        leds.off()
        leds.on_for_index(i)
        time.sleep(0.15)
        leds.off_for_index(i)
        if i < 7:
            leds.on_for_index(i + 1)
        time.sleep(0.15)

    leds.off()
    print(f"\n最终状态: {leds!r}")


# ============================================================================
# 主函数
# ============================================================================

def main() -> None:
    """主函数."""
    print_chip_theory()
    demo_ic74hc595()
    demo_led74hc595()
    demo_shift_register_steps()
    demo_comprehensive()

    print("\n" + "=" * 66)
    print("  74HC595 深度解析示例完成!")
    print("=" * 66)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()