#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 15: LED 二进制计数器 + 数码管显示.

8 个 LED 作为 8-bit 二进制计数器，数码管实时显示十进制数值 (0-255)。
通过拨码开关控制计数速度，通过轻触开关控制重置和跳转。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/15_binary_counter.py
"""

import time
import sys
import signal

from sakshat import SAKSHAT, SAKSPins


# ==============================================================================
# 二进制计数器原理说明
# ==============================================================================
COUNTER_PRINCIPLE = r"""
  8-bit 二进制计数器原理说明
  =============================================

  1. 二进制表示
  ─────────────
  8 位二进制数可以表示 0 到 255 (2^8 = 256 个值)。

    十进制  十六进制  二进制 (bit7..bit0)
    ──────  ────────  ──────────────────
       0      0x00    00000000
       1      0x01    00000001
       2      0x02    00000010
       3      0x03    00000011
      ...
     127      0x7F    01111111
     128      0x80    10000000
      ...
     254      0xFE    11111110
     255      0xFF    11111111

  2. SAKS 扩展板 LED 与二进制位的映射
  ─────────────────────────────────────
  8 颗 LED 通过 74HC595 移位寄存器驱动，对应 8 个二进制位:

    ┌──────────────────────────────────────────────────┐
    │  bit 7  bit 6  bit 5  bit 4  bit 3  bit 2  bit 1  bit 0 │
    │  LED7   LED6   LED5   LED4   LED3   LED2   LED1   LED0  │
    │  MSB                                     LSB  │
    │  (128)  (64)   (32)   (16)   (8)    (4)    (2)    (1)   │
    └──────────────────────────────────────────────────┘

  3. 位运算提取二进制位
  ─────────────────────
  通过右移 (>>) 和按位与 (&) 操作提取每一位:

    bit0 = (counter >> 0) & 1   # 最低位, 权重 1
    bit1 = (counter >> 1) & 1   # 权重 2
    bit2 = (counter >> 2) & 1   # 权重 4
    bit3 = (counter >> 3) & 1   # 权重 8
    bit4 = (counter >> 4) & 1   # 权重 16
    bit5 = (counter >> 5) & 1   # 权重 32
    bit6 = (counter >> 6) & 1   # 权重 64
    bit7 = (counter >> 7) & 1   # 最高位, 权重 128

  4. 74HC595 移位寄存器
  ──────────────────────
  74HC595 通过 3 根信号线 (DS/SHCP/STCP) 控制 8 路并行输出。
  SAKS SDK 的 Led74HC595 封装了底层通信细节，
  直接通过 set_row() 方法设置 8 颗 LED 的状态。

  set_row([bit0, bit1, bit2, bit3, bit4, bit5, bit6, bit7])
          LED0  LED1  LED2  LED3  LED4  LED5  LED6  LED7

  5. 拨码开关速度控制
  ───────────────────
  SAKS 扩展板有 2 位拨码开关，可产生 4 种组合:

    S1  S2  |  模式  |  速度        |  间隔
    ────────┼────────┼─────────────┼────────
    OFF OFF |  00    |  快 (FAST)   |  0.05s
    OFF ON  |  01    |  中 (MEDIUM) |  0.10s
    ON  OFF |  10    |  慢 (SLOW)   |  0.30s
    ON  ON  |  11    |  暂停 (PAUSE)|  ∞

  6. 轻触开关交互
  ───────────────
  左键 (TACT_LEFT):  重置计数器归零
  右键 (TACT_RIGHT): 跳转 +16 (饱和到 255)
"""


# ==============================================================================
# 全局共享状态 (用于主循环与中断回调之间通信)
# ==============================================================================
# counter: 当前计数值 (0-255)
# dip_mode: 拨码开关当前组合，用于速度控制
# 这两个变量在主循环和 GPIO 中断回调之间共享，
# 由于 CPython 的 GIL 保护，简单的整数读写是安全的。
counter: int = 0
dip_mode: int = 0  # 0=快, 1=中, 2=慢, 3=暂停


# ==============================================================================
# 拨码开关状态变更回调
# ==============================================================================
def on_dip_switch_changed(status: list[bool]) -> None:
    """拨码开关状态变更回调函数.

    当用户拨动拨码开关时，GPIO 中断触发此回调。
    将两位开关状态编码为模式值 (0-3)，用于主循环的速度控制。

    Args:
        status: 两位开关状态 [S1, S2], True=ON, False=OFF.

    编码规则:
        S1=OFF, S2=OFF -> mode=0 -> 快
        S1=OFF, S2=ON  -> mode=1 -> 中
        S1=ON,  S2=OFF -> mode=2 -> 慢
        S1=ON,  S2=ON  -> mode=3 -> 暂停
    """
    global dip_mode
    # 编码: S1 为高位, S2 为低位
    # 即 S1=OFF,S2=OFF -> 0; S1=OFF,S2=ON -> 1; S1=ON,S2=OFF -> 2; S1=ON,S2=ON -> 3
    s1, s2 = status[0], status[1]

    if not s1 and not s2:
        dip_mode = 0
        mode_name = "快 (0.05s)"
    elif not s1 and s2:
        dip_mode = 1
        mode_name = "中 (0.10s)"
    elif s1 and not s2:
        dip_mode = 2
        mode_name = "慢 (0.30s)"
    else:
        dip_mode = 3
        mode_name = "暂停"

    print(f"  [拨码开关] S1={'ON' if s1 else 'OFF'}, S2={'ON' if s2 else 'OFF'} -> {mode_name}")


# ==============================================================================
# 轻触开关事件回调
# ==============================================================================
def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关事件回调函数.

    当用户按下或释放轻触开关时，GPIO 中断触发此回调。
    仅在按下时 (status=True) 执行操作。

    Args:
        pin: 触发事件的 GPIO 引脚编号.
        status: True=按下, False=释放.

    操作:
        左键 (TACT_LEFT):  重置计数器归零
        右键 (TACT_RIGHT): 跳转 +16 (饱和到 255)
    """
    global counter
    if not status:
        return  # 仅响应按下事件，忽略释放

    if pin == SAKSPins.TACT_LEFT:
        old = counter
        counter = 0
        print(f"  [左键按下] 重置归零: {old} -> 0")
    elif pin == SAKSPins.TACT_RIGHT:
        old = counter
        counter = min(255, counter + 16)
        print(f"  [右键按下] 跳转 +16: {old} -> {counter}")
    else:
        # 未知引脚，忽略 (防御性编程)
        pass


# ==============================================================================
# 速度获取函数
# ==============================================================================
def get_speed(mode: int) -> tuple[float | None, str]:
    """根据拨码开关模式获取计数速度和名称.

    Args:
        mode: 拨码开关模式 (0-3).

    Returns:
        (speed, name) 元组。
        speed 为 None 表示暂停模式。
    """
    speed_map: dict[int, tuple[float | None, str]] = {
        0: (0.05, "快 (FAST)"),
        1: (0.10, "中 (MEDIUM)"),
        2: (0.30, "慢 (SLOW)"),
        3: (None, "暂停 (PAUSE)"),
    }
    return speed_map.get(mode, (0.10, "默认"))


# ==============================================================================
# LED 二进制更新函数
# ==============================================================================
def update_leds_binary(saks: SAKSHAT, value: int) -> None:
    """将计数值以二进制形式显示在 8 颗 LED 上.

    LED 映射:
        LED0 = bit 0 (LSB, 权重 1)
        LED1 = bit 1 (权重 2)
        LED2 = bit 2 (权重 4)
        LED3 = bit 3 (权重 8)
        LED4 = bit 4 (权重 16)
        LED5 = bit 5 (权重 32)
        LED6 = bit 6 (权重 64)
        LED7 = bit 7 (MSB, 权重 128)

    Args:
        saks: SAKSHAT 实例.
        value: 计数值 (0-255).
    """
    # 通过位运算提取每一位的值
    status = [(value >> i) & 1 == 1 for i in range(8)]
    saks.ledrow.set_row(status)


# ==============================================================================
# 数码管十进制更新函数
# ==============================================================================
def update_display_decimal(saks: SAKSHAT, value: int) -> None:
    """在 4 位数码管上显示十进制数值.

    使用 show() 方法，格式化为 4 位数字 (前导零补齐)。
    例如: 0 -> "0000", 1 -> "0001", 255 -> "0255"

    Args:
        saks: SAKSHAT 实例.
        value: 要显示的数值 (0-255).
    """
    saks.digital_display.show(f"{value:04d}")


# ==============================================================================
# 计数值格式化输出函数
# ==============================================================================
def format_counter_info(value: int) -> str:
    """格式化计数器的完整信息字符串.

    输出格式: "十进制=XXX  十六进制=0xXX  二进制=XXXXXXXX"

    Args:
        value: 计数值 (0-255).

    Returns:
        格式化后的信息字符串.
    """
    binary_str = f"{value:08b}"
    # 每 4 位加空格以提高可读性
    binary_spaced = f"{binary_str[:4]} {binary_str[4:]}"
    return (
        f"十进制={value:3d}  "
        f"十六进制=0x{value:02X}  "
        f"二进制={binary_spaced}"
    )


# ==============================================================================
# 计数溢出处理函数 (到达 255 时)
# ==============================================================================
def handle_overflow(saks: SAKSHAT) -> None:
    """处理计数器到达 255 时的溢出效果.

    执行以下动画序列:
        1. 全部 8 颗 LED 闪烁 3 次
        2. 数码管显示 "FULL"
        3. 数码管显示十六进制值 "00FF"
        4. 蜂鸣提示

    Args:
        saks: SAKSHAT 实例.
    """
    print("\n  >>> 计数到达 255 (0xFF)! 播放溢出动画...")

    # ---- 步骤 1: 全部 LED 闪烁 3 次 ----
    for i in range(3):
        print(f"      闪烁 {i + 1}/3: 全亮")
        saks.ledrow.on()               # 全部 LED 亮
        time.sleep(0.3)
        print(f"      闪烁 {i + 1}/3: 全灭")
        saks.ledrow.off()              # 全部 LED 灭
        time.sleep(0.2)

    # ---- 步骤 2: 数码管显示 "FULL" ----
    # F=0x71, U=0x3E, L=0x38, L=0x38
    print("      显示: FULL")
    saks.digital_display.show_raw([0x71, 0x3E, 0x38, 0x38])
    time.sleep(1.5)

    # ---- 步骤 3: 数码管显示十六进制 "00FF" ----
    # 0=0x3F, 0=0x3F, F=0x71, F=0x71
    print("      显示: 00FF (十六进制)")
    saks.digital_display.show_raw([0x3F, 0x3F, 0x71, 0x71])
    time.sleep(1.5)

    # ---- 步骤 4: 蜂鸣提示 ----
    print("      蜂鸣提示!")
    saks.buzzer.beep(0.3)
    time.sleep(0.2)

    print("  >>> 溢出动画完成，计数器归零\n")


# ==============================================================================
# 打印二进制位权重表
# ==============================================================================
def print_bit_weight_table() -> None:
    """打印二进制位权重对照表."""
    print("\n" + "=" * 65)
    print("  二进制位权重对照表 (8-bit)")
    print("=" * 65)
    print(f"  {'Bit':<6} {'LED':<6} {'权重':<8} {'2^N':<10} {'说明'}")
    print("  " + "-" * 55)
    bit_info = [
        (0, "LED0", 1, "2^0", "最低位 (LSB)"),
        (1, "LED1", 2, "2^1", ""),
        (2, "LED2", 4, "2^2", ""),
        (3, "LED3", 8, "2^3", "低 4 位"),
        (4, "LED4", 16, "2^4", ""),
        (5, "LED5", 32, "2^5", ""),
        (6, "LED6", 64, "2^6", ""),
        (7, "LED7", 128, "2^7", "最高位 (MSB)"),
    ]
    for bit, led, weight, power, note in bit_info:
        print(f"  {bit:<6} {led:<6} {weight:<8} {power:<10} {note}")
    print("  " + "-" * 55)
    print("  例: 十进制的 100 = 0x64 = 0b01100100")
    print("      点亮 LED2(4) + LED5(32) + LED6(64) = 100")


# ==============================================================================
# 打印拨码开关速度对照表
# ==============================================================================
def print_speed_table() -> None:
    """打印拨码开关速度对照表."""
    print("\n" + "=" * 65)
    print("  拨码开关速度控制对照表")
    print("=" * 65)
    print(f"  {'S1':<6} {'S2':<6} {'模式':<6} {'速度':<12} {'间隔':<8} {'说明'}")
    print("  " + "-" * 55)
    speeds = [
        ("OFF", "OFF", "00", "快 (FAST)", "0.05s", "适合快速浏览"),
        ("OFF", "ON", "01", "中 (MEDIUM)", "0.10s", "默认速度"),
        ("ON", "OFF", "10", "慢 (SLOW)", "0.30s", "适合仔细观察"),
        ("ON", "ON", "11", "暂停 (PAUSE)", "--", "停止计数"),
    ]
    for s1, s2, mode, speed, interval, note in speeds:
        print(f"  {s1:<6} {s2:<6} {mode:<6} {speed:<12} {interval:<8} {note}")
    print("  " + "-" * 55)


# ==============================================================================
# 主函数
# ==============================================================================
def main() -> None:
    """主函数."""
    global counter, dip_mode

    print("=" * 65)
    print("  SAKS SDK 示例 15: LED 二进制计数器 + 数码管显示")
    print("=" * 65)

    # ---- 第一部分: 知识讲解 (无需硬件) ----
    print(COUNTER_PRINCIPLE)
    print_bit_weight_table()
    print_speed_table()

    print("\n" + "=" * 65)
    print("  操作说明")
    print("=" * 65)
    print("""
  拨码开关 S1, S2: 控制计数速度
    00 = 快 (0.05s)    01 = 中 (0.10s)
    10 = 慢 (0.30s)    11 = 暂停

  轻触开关:
    左键 = 重置计数器归零
    右键 = 跳转 +16 (饱和到 255)

  按 Ctrl+C 退出程序
""")

    # ---- 第二部分: 硬件演示 (需要树莓派 + SAKS 扩展板) ----
    print("=" * 65)
    print("  以下演示需要硬件支持 (树莓派 + SAKS 扩展板)")
    print("=" * 65)

    # 初始化 SAKS 扩展板
    saks = SAKSHAT()

    # 注册回调函数
    saks.dip_switch_status_changed_handler = on_dip_switch_changed
    saks.tact_event_handler = on_tact_event

    # 读取拨码开关初始状态 (用于初始化 dip_mode)
    init_status = saks.dip_switch.is_on
    if init_status[0] or init_status[1]:
        # 手动调用一次回调以同步初始状态
        on_dip_switch_changed(init_status)

    print("\n  初始化完成!")
    print("  按 Ctrl+C 可随时退出\n")

    try:
        # 确保设备初始状态
        saks.ledrow.off()
        saks.digital_display.off()
        saks.buzzer.off()

        # 初始显示: 计数器为 0
        update_leds_binary(saks, 0)
        update_display_decimal(saks, 0)
        print(f"  初始状态: {format_counter_info(0)}")

        time.sleep(0.5)

        # 获取初始速度
        speed, speed_name = get_speed(dip_mode)
        print(f"  当前速度: {speed_name}")

        # ---- 主计数循环 ----
        while True:
            # 读取当前拨码开关速度
            speed, speed_name = get_speed(dip_mode)

            if speed is None:
                # 暂停模式: 保持当前显示，短暂休眠后继续检查
                time.sleep(0.1)
                continue

            # 更新 LED 二进制显示
            update_leds_binary(saks, counter)

            # 更新数码管十进制显示
            update_display_decimal(saks, counter)

            # 每 16 步蜂鸣一次作为进度提示
            if counter > 0 and counter % 16 == 0:
                saks.buzzer.beep(0.03)
                # 打印进度信息
                print(f"  [{format_counter_info(counter)}]  速度: {speed_name}")

            # 计数器递增
            counter += 1

            # 检查是否到达 255
            if counter > 255:
                counter = 255
                # 最后一次更新显示
                update_leds_binary(saks, counter)
                update_display_decimal(saks, counter)
                print(f"  [{format_counter_info(counter)}]  到达最大值!")

                # 处理溢出动画
                handle_overflow(saks)

                # 重置计数器归零，继续循环
                counter = 0
                update_leds_binary(saks, counter)
                update_display_decimal(saks, counter)
                print(f"  计数器归零: {format_counter_info(counter)}")
                continue

            # 计数间隔
            time.sleep(speed)

    except KeyboardInterrupt:
        print("\n\n  程序被用户中断。")

    finally:
        # 清理资源
        saks.digital_display.off()
        saks.ledrow.off()
        saks.buzzer.off()
        saks.cleanup()
        print("  资源已清理。")
        print("=" * 65)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()