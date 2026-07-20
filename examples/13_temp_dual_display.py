#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 13: 温度双通道交替显示.

在 4 位数码管上交替显示 DS18B20 环境温度和 CPU 温度，
每 5 秒切换一次，切换时 LED 闪烁两次提示。

LED 柱状图指示当前温度等级：
    - 环境温度: 0-50°C 映射到 0-8 个 LED，从 LED 0 开始填充
    - CPU 温度:  30-80°C 映射到 0-8 个 LED，从 LED 0 开始填充

显示格式:
    - 环境温度: "C12.3" (C = Celsius/环境温度, 保留一位小数)
    - CPU 温度:  "U12.3" (U = CPU, 保留一位小数)

硬件要求: 树莓派 + SAKS 扩展板 + DS18B20 (可选)
运行方式: python3 examples/13_temp_dual_display.py
"""

import subprocess
import time
import sys
import signal

from sakshat import SAKSHAT, DigitalDisplay

# ---- 显示模式常量 ----
MODE_AMBIENT: int = 0   # 环境温度 (DS18B20)
MODE_CPU: int = 1       # CPU 温度
SWITCH_INTERVAL: float = 5.0   # 切换间隔 (秒)
FLASH_COUNT: int = 2           # 切换时闪烁次数

# ---- 温度-柱状图映射范围 ----
AMBIENT_TEMP_MIN: float = 0.0   # 环境温度柱状图下限
AMBIENT_TEMP_MAX: float = 50.0  # 环境温度柱状图上限
CPU_TEMP_MIN: float = 30.0      # CPU 温度柱状图下限
CPU_TEMP_MAX: float = 80.0      # CPU 温度柱状图上限

# ---- 段码数据 ----
# 数字 0-9 的段码 (不含小数点)
digit_codes: dict[int, int] = {
    0: 0x3F, 1: 0x06, 2: 0x5B, 3: 0x4F, 4: 0x66,
    5: 0x6D, 6: 0x7D, 7: 0x07, 8: 0x7F, 9: 0x6F,
}


def build_temp_display(prefix: str, temperature: float) -> list[int]:
    """构造温度显示段码数组.

    将温度格式化为 "X12.3" 形式 (前缀字母 + 3位数字含小数点)。

    Args:
        prefix: 前缀字母，如 "C" 或 "U".
        temperature: 温度值 (摄氏度).

    Returns:
        4 个段码的列表，对应数码管第 0-3 位.

    Example:
        >>> build_temp_display("C", 12.3)
        [0x39, 0x06, 0xDB, 0x4F]  # C 1 2. 3
    """
    # 限制显示范围
    if temperature < -9.9:
        temperature = -9.9
    elif temperature > 99.9:
        temperature = 99.9

    # 取绝对值并格式化
    abs_temp = abs(temperature)
    int_part = int(abs_temp)        # 整数部分
    dec_part = int(round(abs_temp - int_part, 1) * 10)  # 小数部分

    codes: list[int] = []

    # 第 0 位: 前缀字母
    if prefix.upper() in DigitalDisplay.CHAR_MAP:
        codes.append(DigitalDisplay.CHAR_MAP[prefix.upper()])
    else:
        codes.append(0x00)  # 未知前缀显示空白

    # 第 1 位: 十位数字 (或负号)
    if temperature < 0:
        codes.append(0x40)  # 负号
    else:
        codes.append(digit_codes.get(int_part // 10, 0x00))

    # 第 2 位: 个位数字 + 小数点
    ones_code = digit_codes.get(int_part % 10, 0x00)
    codes.append(ones_code | 0x80)  # 加小数点

    # 第 3 位: 小数位
    codes.append(digit_codes.get(dec_part, 0x00))

    return codes


def get_cpu_temperature() -> float:
    """读取树莓派 CPU 温度.

    Returns:
        CPU 温度 (摄氏度)，读取失败返回 -1.0.
    """
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return float(f.read().strip()) / 1000.0
    except (OSError, ValueError):
        return -1.0


def temp_to_bar(temp: float, t_min: float, t_max: float) -> list[bool | None]:
    """将温度映射为 8 路 LED 柱状图.

    温度在 [t_min, t_max] 范围内线性映射到 0-8 个 LED。
    超出范围的值会被钳制。

    Args:
        temp: 当前温度 (°C).
        t_min: 温度下限.
        t_max: 温度上限.

    Returns:
        8 个元素的列表，True=亮，False=灭，None=不变.
        从 LED 0 开始填充，温度越高亮得越多。

    Example:
        >>> temp_to_bar(25.0, 0.0, 50.0)
        [True, True, True, True, False, False, False, False]  # 4/8 = 50%
    """
    # 钳制到有效范围
    clamped = max(t_min, min(t_max, temp))

    # 线性映射: 0-8 个 LED
    ratio = (clamped - t_min) / (t_max - t_min) if t_max > t_min else 0.0
    lit_count = int(round(ratio * 8))

    # 构造 LED 状态: 从 LED 0 开始逐一点亮
    return [True if i < lit_count else False for i in range(8)]


def flash_leds(saks: SAKSHAT, count: int, delay: float = 0.15) -> None:
    """LED 闪烁提示.

    使用 set_row 一次性设置全部 LED，避免逐个操作导致的闪烁。

    Args:
        saks: SAKS 实例.
        count: 闪烁次数.
        delay: 每次亮/灭的持续时间 (秒).
    """
    all_on: list[bool | None] = [True] * 8
    all_off: list[bool | None] = [False] * 8
    for _ in range(count):
        saks.ledrow.set_row(all_on)
        time.sleep(delay)
        saks.ledrow.set_row(all_off)
        time.sleep(delay)


def main() -> None:
    """主函数."""
    print("=" * 58)
    print("  SAKS SDK 示例 13: 温度双通道交替显示")
    print("=" * 58)
    print()
    print("  显示格式:")
    print("    C12.3 = 环境温度 (DS18B20) 12.3°C")
    print("    U12.3 = CPU 温度 12.3°C")
    print(f"  每 {SWITCH_INTERVAL:.0f} 秒切换一次，切换时 LED 闪烁 {FLASH_COUNT} 次")
    print("  LED 柱状图: 温度越高，亮灯越多")
    print("  按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()

    # 检查传感器
    has_ds18b20 = saks.ds18b20.is_exist
    if not has_ds18b20:
        print("  [提示] 未检测到 DS18B20，环境温度通道将显示 '----'")
        print()

    current_mode = MODE_AMBIENT
    last_switch = time.time()

    try:
        while True:
            now = time.time()
            elapsed = now - last_switch

            # 判断是否需要切换通道
            if elapsed >= SWITCH_INTERVAL:
                # 闪烁提示
                flash_leds(saks, FLASH_COUNT)
                # 切换模式
                current_mode = MODE_CPU if current_mode == MODE_AMBIENT else MODE_AMBIENT
                last_switch = now
                elapsed = 0.0  # 重置计时

            # 读取并显示温度
            if current_mode == MODE_AMBIENT:
                if has_ds18b20:
                    temp = saks.ds18b20.temperature
                    if temp != -128.0:
                        codes = build_temp_display("C", temp)
                        # LED 柱状图: 环境温度 0-50°C → 0-8 LEDs
                        led_bar = temp_to_bar(temp, AMBIENT_TEMP_MIN, AMBIENT_TEMP_MAX)
                    else:
                        codes = [0x00, 0x00, 0x00, 0x00]
                        led_bar = [False] * 8
                else:
                    # 无传感器时显示 "----"
                    saks.digital_display.show("----")
                    saks.ledrow.set_row([False] * 8)
                    time.sleep(0.5)
                    continue

                saks.digital_display.show_raw(codes)
                saks.ledrow.set_row(led_bar)

            else:
                temp = get_cpu_temperature()
                if temp > 0:
                    codes = build_temp_display("U", temp)
                    # LED 柱状图: CPU 温度 30-80°C → 0-8 LEDs
                    led_bar = temp_to_bar(temp, CPU_TEMP_MIN, CPU_TEMP_MAX)
                else:
                    codes = [0x00, 0x00, 0x00, 0x00]
                    led_bar = [False] * 8

                saks.digital_display.show_raw(codes)
                saks.ledrow.set_row(led_bar)

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n  监控已停止。")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")
        print("=" * 58)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()