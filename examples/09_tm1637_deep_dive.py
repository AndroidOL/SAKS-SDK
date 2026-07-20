#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 09: TM1637 芯片深度解析.

本示例深入讲解 TM1637 数码管驱动芯片的工作原理、通信协议、命令码体系，
以及 ICTM1637 类的底层控制方法。

TM1637 是天微电子 (Titan Micro) 生产的 LED 驱动控制专用芯片，
通过两线 (DIO/CLK) I2C-like 协议与主控通信，驱动 4 位共阳极数码管。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/09_tm1637_deep_dive.py
"""

import time
import sys
import signal

from sakshat import ICTM1637, SAKSValidationError


# ============================================================================
# 第一部分: TM1637 芯片原理说明
# ============================================================================

def print_chip_theory() -> None:
    """打印 TM1637 芯片原理说明."""
    print("=" * 66)
    print("  TM1637 数码管驱动芯片 - 深度解析")
    print("=" * 66)

    print("""
[1] 芯片概述
    TM1637 是天微电子 (Titan Micro) 生产的 LED 驱动控制专用芯片。
    它采用两线串行接口 (DIO/CLK)，与 I2C 协议类似但并非标准 I2C，
    专用于驱动 4 位 8 段共阳极数码管。

    核心特性:
    - 两线通信接口 (DIO: 数据输入/输出, CLK: 时钟)
    - 8 级亮度调节 (通过命令码的低 3 位控制)
    - 支持自动地址增加和固定地址两种数据写入模式
    - 内置 RC 振荡器，无需外部时钟
    - 内置上电复位电路
    - 段驱动电流可达 25mA，位驱动电流可达 150mA

[2] 引脚说明
    +------+------+-----------------------------------------------+
    | 引脚 | 名称 | 功能说明                                       |
    +------+------+-----------------------------------------------+
    | DIO  | 数据 | 双向数据线，开漏输出，需外接上拉电阻            |
    | CLK  | 时钟 | 时钟输入线，上升沿采样数据                      |
    | VDD  | 电源 | 5V 供电                                        |
    | GND  | 地   | 电源地                                         |
    | SEG1-8| 段  | 段输出，接数码管 A-G + DP 各段                  |
    | GRID1-4| 位 | 位选输出，接 4 个数码管的共阳极                  |
    +------+------+-----------------------------------------------+

[3] 通信时序图 (ASCII)

    起始条件 (Start): CLK 为高时，DIO 从高变低
    停止条件 (Stop):  CLK 为高时，DIO 从低变高

    完整数据帧: Start -> 命令字节 -> Stop -> Start -> 数据字节(s) -> Stop

    Write Byte 时序 (LSB 优先):

    CLK  ____|^^|_|^^|_|^^|_|^^|_|^^|_|^^|_|^^|_|^^|_______|^^|_______
             |  | |  | |  | |  | |  | |  | |  | |  | |  |    |  | |
    DIO  ----X__X_X__X_X__X_X__X_X__X_X__X_X__X_X__X_X__X----X__X-------
             B0  B1  B2  B3  B4  B5  B6  B7  ACK
             |                                      |
             |<---------- 8 data bits ------------>|<- ACK bit

    说明:
    - 数据在 CLK 上升沿被采样
    - 数据格式: LSB 优先 (低位先发)
    - 每字节后跟一个 ACK 时钟位 (主控释放 DIO，从机拉低应答)
    - 在 SAKS SDK 的 GPIO 模拟实现中，ACK 位由主控主动释放处理

    完整通信流程示例:

    Start -> 0x40 (数据命令) -> Stop -> Start -> 0xC0 (地址) -> 0x3F (数据) -> Stop
    |      |                 |      |      |               |              |
    |      +-- 命令字节      |      |      +-- 地址字节    +-- 数据字节  |
    +-- 起始               +-- 停止    +-- 起始                        +-- 停止

[4] 命令码表

    TM1637 的命令分为三大类: 数据命令、地址命令、显示控制命令。

    数据命令 (Data Command) - 设置数据写入模式:
    +----------------+----------+-------------------------------------------+
    | 命令码         | 十六进制 | 说明                                       |
    +----------------+----------+-------------------------------------------+
    | CMD_DATA_AUTO  | 0x40     | 自动地址增加模式，每写完一字节地址自动 +1 |
    | CMD_DATA_FIXED | 0x44     | 固定地址模式，写完数据后地址不自动增加      |
    +----------------+----------+-------------------------------------------+

    地址命令 (Address Command) - 设置要写入的显示地址:
    +----------+----------+-----------------------+
    | 地址     | 十六进制 | 对应数码管位置         |
    +----------+----------+-----------------------+
    | ADDRESS0 | 0xC0     | 第 1 位 (最左)          |
    | ADDRESS1 | 0xC1     | 第 2 位                 |
    | ADDRESS2 | 0xC2     | 第 3 位                 |
    | ADDRESS3 | 0xC3     | 第 4 位 (最右)          |
    +----------+----------+-----------------------+

    显示控制命令 (Display Control) - 控制显示开关和亮度:
    +------------------+-------------------+---------------------------------+
    | 命令码           | 范围              | 说明                            |
    +------------------+-------------------+---------------------------------+
    | CMD_DISPLAY_OFF  | 0x80              | 关闭显示 (脉冲宽度 = 0)          |
    | CMD_DISPLAY_ON   | 0x88 - 0x8F       | 开启显示，低 3 位控制亮度        |
    +------------------+-------------------+---------------------------------+

    亮度级别 (0x88 - 0x8F):
    +----------+----------+----------+----------+----------+----------+----------+----------+
    | 0x88     | 0x89     | 0x8A     | 0x8B     | 0x8C     | 0x8D     | 0x8E     | 0x8F     |
    +----------+----------+----------+----------+----------+----------+----------+----------+
    | 1/8 亮度 | 2/8 亮度 | 3/8 亮度 | 4/8 亮度 | 5/8 亮度 | 6/8 亮度 | 7/8 亮度 | 8/8 亮度 |
    +----------+----------+----------+----------+----------+----------+----------+----------+

    注意: CMD_DISPLAY_ON = 0x8F 为最大亮度 (SAKS SDK 默认值)

[5] 7 段数码管段码

    段码位定义 (bit 7..0 = DP.G.F.E.D.C.B.A):

          a
         ---
       f|   |b
         -g-
       e|   |c
         ---
          d    .dp

    +--------+------+------+------+------+------+------+------+------+
    | 位     | bit7 | bit6 | bit5 | bit4 | bit3 | bit2 | bit1 | bit0 |
    +--------+------+------+------+------+------+------+------+------+
    | 段     |  dp  |  g   |  f   |  e   |  d   |  c   |  b   |  a   |
    +--------+------+------+------+------+------+------+------+------+

    常用数字段码:
    +--------+----------+------+
    | 数字   | 段码     | 亮的段 |
    +--------+----------+------+
    | 0      | 0x3F     | abcdef  |
    | 1      | 0x06     | bc      |
    | 2      | 0x5B     | abdeg   |
    | 3      | 0x4F     | abcdg   |
    | 4      | 0x66     | bcfg    |
    | 5      | 0x6D     | acdfg   |
    | 6      | 0x7D     | acdefg  |
    | 7      | 0x07     | abc     |
    | 8      | 0x7F     | abcdefg |
    | 9      | 0x6F     | abcfg   |
    +--------+----------+------+
""")


# ============================================================================
# 第二部分: ICTM1637 类演示 - 基础操作
# ============================================================================

def demo_ictm1637_basic() -> None:
    """演示 ICTM1637 类的基本操作."""
    print("=" * 66)
    print("  ICTM1637 类 - 基础操作演示")
    print("=" * 66)

    # 创建 ICTM1637 实例 (使用 SAKS 扩展板默认引脚)
    ic = ICTM1637(di=25, clk=5)
    print(f"\n创建芯片实例: {ic!r}")

    # 显示命令常量
    print("\n[1] 命令常量一览:")
    print(f"  CMD_DATA_AUTO  = 0x{ic.CMD_DATA_AUTO:02X}  (自动地址增加)")
    print(f"  CMD_DATA_FIXED = 0x{ic.CMD_DATA_FIXED:02X}  (固定地址)")
    print(f"  CMD_DISPLAY_ON = 0x{ic.CMD_DISPLAY_ON:02X}  (开启显示, 最大亮度)")
    print(f"  CMD_DISPLAY_OFF= 0x{ic.CMD_DISPLAY_OFF:02X}  (关闭显示)")
    print(f"  ADDRESSES      = {[hex(a) for a in ic.ADDRESSES]}")

    # 演示 send_command()
    print("\n[2] send_command() 演示:")
    print("  >>> ic.send_command(0x8F)   # 开启显示, 最大亮度")
    ic.send_command(0x8F)
    print("  命令已发送: 开启显示 (亮度 8/8)")
    time.sleep(0.3)

    print("  >>> ic.send_command(0x80)   # 关闭显示")
    ic.send_command(0x80)
    print("  命令已发送: 关闭显示")
    time.sleep(0.3)

    # 演示 write_data()
    print("\n[3] write_data() 演示 - 写入段码数据:")

    ic.send_command(0x8F)  # 先开启显示

    # 在第 0 位显示数字 0 (段码 0x3F)
    print("  >>> ic.write_data(0xC0, 0x3F)   # 第 1 位显示 '0'")
    ic.write_data(0xC0, 0x3F)
    time.sleep(0.5)

    # 在第 1 位显示数字 1 (段码 0x06)
    print("  >>> ic.write_data(0xC1, 0x06)   # 第 2 位显示 '1'")
    ic.write_data(0xC1, 0x06)
    time.sleep(0.5)

    # 在第 2 位显示数字 2 (段码 0x5B)
    print("  >>> ic.write_data(0xC2, 0x5B)   # 第 3 位显示 '2'")
    ic.write_data(0xC2, 0x5B)
    time.sleep(0.5)

    # 在第 3 位显示数字 3 (段码 0x4F)
    print("  >>> ic.write_data(0xC3, 0x4F)   # 第 4 位显示 '3'")
    ic.write_data(0xC3, 0x4F)
    time.sleep(0.5)

    # 显示 "1234" 完成
    print("  数码管现在显示: 1 2 3 4")
    time.sleep(1.0)

    # clear() 演示
    print("\n[4] clear() 演示:")
    print("  >>> ic.clear()   # 关闭显示")
    ic.clear()
    print("  显示已关闭")


# ============================================================================
# 第三部分: 原始数据写入演示
# ============================================================================

def demo_raw_data_write() -> None:
    """演示手动构造命令->地址->数据序列的原始写入."""
    print("\n" + "=" * 66)
    print("  原始数据写入演示 - 手动构造命令序列")
    print("=" * 66)

    ic = ICTM1637(di=25, clk=5)

    print("\n[1] 完整写入流程 (手动模拟):")
    print("""
    完整的数据写入需要以下步骤:
    1. 发送起始条件 (start_bus)
    2. 写入命令字节 (write_byte)
    3. 发送停止条件 (stop_bus)
    4. 再次发送起始条件
    5. 写入地址字节
    6. 写入数据字节
    7. 发送停止条件

    序列示例: 在第 0 位显示数字 5
    """)

    # 演示: 在第 0 位显示数字 5
    print("  >>> ic.start_bus()")
    print("  >>> ic.write_byte(0x44)        # CMD_DATA_FIXED")
    print("  >>> ic.stop_bus()")
    print("  >>> ic.start_bus()")
    print("  >>> ic.write_byte(0xC0)        # 地址 0xC0 (第 1 位)")
    print("  >>> ic.write_byte(0x6D)        # 数字 5 的段码")
    print("  >>> ic.stop_bus()")

    ic.start_bus()
    ic.write_byte(0x44)   # CMD_DATA_FIXED
    ic.stop_bus()
    ic.start_bus()
    ic.write_byte(0xC0)   # 地址 0xC0
    ic.write_byte(0x6D)   # 数字 5
    ic.stop_bus()

    # 开启显示
    ic.send_command(0x8F)
    print("  第 1 位显示: 5")
    time.sleep(1.0)

    # 逐个写入 4 位数字
    print("\n[2] 逐个写入 4 位数字 (手动方式):")
    digits = [
        (0xC0, 0x3F, "0"),  # 地址 0xC0, 段码 0x3F -> 数字 0
        (0xC1, 0x06, "1"),  # 地址 0xC1, 段码 0x06 -> 数字 1
        (0xC2, 0x5B, "2"),  # 地址 0xC2, 段码 0x5B -> 数字 2
        (0xC3, 0x4F, "3"),  # 地址 0xC3, 段码 0x4F -> 数字 3
    ]
    for addr, code, digit in digits:
        ic.start_bus()
        ic.write_byte(0x44)   # 固定地址模式
        ic.stop_bus()
        ic.start_bus()
        ic.write_byte(addr)
        ic.write_byte(code)
        ic.stop_bus()
        print(f"  地址 0x{addr:02X} <- 0x{code:02X} (数字 '{digit}')")
        time.sleep(0.4)

    ic.send_command(0x8F)
    print("  数码管显示: 0 1 2 3")
    time.sleep(1.0)

    # 显示数字 0-9 的所有段码
    print("\n[3] 数字 0-9 段码对照表:")
    SEGMENTS = [
        (0, 0x3F), (1, 0x06), (2, 0x5B), (3, 0x4F), (4, 0x66),
        (5, 0x6D), (6, 0x7D), (7, 0x07), (8, 0x7F), (9, 0x6F),
    ]
    print("  +--------+----------+----------------+")
    print("  | 数字   | 段码     | 二进制         |")
    print("  +--------+----------+----------------+")
    for digit, code in SEGMENTS:
        print(f"  | {digit:^6} | 0x{code:02X}    | {code:08b}       |")
    print("  +--------+----------+----------------+")

    # 循环显示 0-9
    print("\n[4] 循环显示 0-9 在第 0 位:")
    for digit, code in SEGMENTS:
        ic.start_bus()
        ic.write_byte(0x44)
        ic.stop_bus()
        ic.start_bus()
        ic.write_byte(0xC0)
        ic.write_byte(code)
        ic.stop_bus()
        ic.send_command(0x8F)
        print(f"  数字 '{digit}' -> 段码 0x{code:02X} ({code:08b})")
        time.sleep(0.3)

    ic.clear()


# ============================================================================
# 第四部分: 亮度控制演示
# ============================================================================

def demo_brightness_control() -> None:
    """演示 TM1637 的亮度控制功能."""
    print("\n" + "=" * 66)
    print("  亮度控制演示 - 0x88 到 0x8F")
    print("=" * 66)

    ic = ICTM1637(di=25, clk=5)

    # 先写入数据
    print("\n[1] 写入显示数据 '8888':")
    for addr in ic.ADDRESSES:
        ic.write_data(addr, 0x7F)  # 数字 8 的段码
    print("  数码管显示: 8 8 8 8")

    # 演示不同亮度级别
    print("\n[2] 亮度级别演示 (0x88 - 0x8F):")
    print("  +--------+----------+----------+")
    print("  | 亮度码 | 十六进制 | 亮度级别 |")
    print("  +--------+----------+----------+")

    brightness_levels = list(range(0x88, 0x90))  # 0x88 to 0x8F
    for cmd in brightness_levels:
        level = cmd - 0x87  # 1-8
        fraction = f"{level}/8"
        print(f"  | 0x{cmd:02X}   | {cmd}    | {fraction:^8} |")
        ic.send_command(cmd)
        time.sleep(0.4)

    print("  +--------+----------+----------+")

    # 循环亮度
    print("\n[3] 亮度循环演示:")
    for _ in range(2):  # 循环两次
        for cmd in brightness_levels:
            ic.send_command(cmd)
            time.sleep(0.15)
        for cmd in reversed(brightness_levels):
            ic.send_command(cmd)
            time.sleep(0.15)

    # 恢复最大亮度
    ic.send_command(0x8F)
    print("  恢复最大亮度 0x8F")

    ic.clear()


# ============================================================================
# 第五部分: 自动地址增加模式演示
# ============================================================================

def demo_auto_increment() -> None:
    """演示自动地址增加模式."""
    print("\n" + "=" * 66)
    print("  自动地址增加模式演示 (CMD_DATA_AUTO)")
    print("=" * 66)

    ic = ICTM1637(di=25, clk=5)

    print("\n[1] 自动地址增加模式说明:")
    print("""
    在自动地址增加模式下:
    1. 发送 CMD_DATA_AUTO (0x40)
    2. 发送起始地址 (如 0xC0)
    3. 连续写入多个数据字节
    4. 每写入一个字节，地址自动 +1

    示例: 写入 4 个数据到地址 0xC0-0xC3
    """)

    print("  >>> ic.start_bus()")
    print("  >>> ic.write_byte(0x40)        # CMD_DATA_AUTO")
    print("  >>> ic.stop_bus()")
    print("  >>> ic.start_bus()")
    print("  >>> ic.write_byte(0xC0)        # 起始地址")
    print("  >>> ic.write_byte(0x3F)        # 写入 0xC0: '0'")
    print("  >>> ic.write_byte(0x06)        # 写入 0xC1: '1'")
    print("  >>> ic.write_byte(0x5B)        # 写入 0xC2: '2'")
    print("  >>> ic.write_byte(0x4F)        # 写入 0xC3: '3'")
    print("  >>> ic.stop_bus()")

    ic.start_bus()
    ic.write_byte(0x40)   # CMD_DATA_AUTO
    ic.stop_bus()
    ic.start_bus()
    ic.write_byte(0xC0)   # 起始地址 0xC0
    ic.write_byte(0x3F)   # 写入 0xC0: 数字 0
    ic.write_byte(0x06)   # 写入 0xC1: 数字 1
    ic.write_byte(0x5B)   # 写入 0xC2: 数字 2
    ic.write_byte(0x4F)   # 写入 0xC3: 数字 3
    ic.stop_bus()

    ic.send_command(0x8F)
    print("  数码管显示: 0 1 2 3")
    time.sleep(1.0)

    # 对比固定地址模式
    print("\n[2] 固定地址模式 vs 自动地址增加模式:")
    print("""
    +---------------------+------------------------------------------+--------------------------------------------+
    | 特性                 | 固定地址模式 (CMD_DATA_FIXED)             | 自动地址增加模式 (CMD_DATA_AUTO)           |
    +---------------------+------------------------------------------+--------------------------------------------+
    | 命令码               | 0x44                                     | 0x40                                       |
    | 写入方式             | 每次 Start->Addr->Data->Stop              | Start->Addr->Data1->Data2->...->Stop       |
    | 地址变化             | 不自动增加                                | 每写一字节地址自动 +1                       |
    | 适用场景             | 更新单个位                                | 批量更新全部 4 位                           |
    | 效率                 | 单次更新快                                | 批量更新快                                  |
    +---------------------+------------------------------------------+--------------------------------------------+
    """)

    # 使用自动模式写入 "HELO"
    print("\n[3] 使用自动地址模式写入 'HELO':")
    # H=0x76, E=0x79, L=0x38, O=0x3F(用0代替)
    hello_codes = [0x76, 0x79, 0x38, 0x3F]
    hello_chars = ["H", "E", "L", "O"]
    ic.start_bus()
    ic.write_byte(0x40)   # 自动地址增加
    ic.stop_bus()
    ic.start_bus()
    ic.write_byte(0xC0)   # 起始地址
    for i, code in enumerate(hello_codes):
        ic.write_byte(code)
        print(f"  地址 0x{0xC0 + i:02X} <- 0x{code:02X} (字符 '{hello_chars[i]}')")
    ic.stop_bus()
    ic.send_command(0x8F)
    print("  数码管显示: H E L O")
    time.sleep(1.0)

    ic.clear()


# ============================================================================
# 第六部分: 异常处理演示
# ============================================================================

def demo_error_handling() -> None:
    """演示异常处理."""
    print("\n" + "=" * 66)
    print("  异常处理演示")
    print("=" * 66)

    ic = ICTM1637(di=25, clk=5)

    # 地址越界
    print("\n[1] 地址越界:")
    print("  >>> try:")
    print("  ...     ic.write_data(0xC4, 0x3F)  # 0xC4 超出 0xC0-0xC3")
    try:
        ic.write_data(0xC4, 0x3F)
    except SAKSValidationError as e:
        print(f"  捕获到 SAKSValidationError: {e}")

    print("\n  >>> try:")
    print("  ...     ic.write_data(0xBF, 0x3F)  # 0xBF 小于 0xC0")
    try:
        ic.write_data(0xBF, 0x3F)
    except SAKSValidationError as e:
        print(f"  捕获到 SAKSValidationError: {e}")

    # 数据越界
    print("\n[2] 数据越界:")
    print("  >>> try:")
    print("  ...     ic.write_data(0xC0, 0x100)  # 数据超出 0xFF")
    try:
        ic.write_data(0xC0, 0x100)
    except SAKSValidationError as e:
        print(f"  捕获到 SAKSValidationError: {e}")

    print("\n  >>> try:")
    print("  ...     ic.write_byte(-1)            # 负数")
    try:
        ic.write_byte(-1)
    except SAKSValidationError as e:
        print(f"  捕获到 SAKSValidationError: {e}")

    # write_data 同时验证地址和数据
    print("\n[3] write_data 同时验证地址和数据:")
    print("  >>> try:")
    print("  ...     ic.write_data(0xC4, 0x100)  # 地址和数据都越界")
    try:
        ic.write_data(0xC4, 0x100)
    except SAKSValidationError as e:
        print(f"  捕获到 SAKSValidationError: {e}")


# ============================================================================
# 主函数
# ============================================================================

def main() -> None:
    """主函数."""
    print_chip_theory()
    demo_ictm1637_basic()
    demo_raw_data_write()
    demo_brightness_control()
    demo_auto_increment()
    demo_error_handling()

    print("\n" + "=" * 66)
    print("  TM1637 深度解析示例完成!")
    print("=" * 66)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()