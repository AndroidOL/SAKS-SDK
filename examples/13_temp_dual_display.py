#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 13: 温度双通道交替显示.

在 4 位数码管上交替显示 DS18B20 环境温度和 CPU 温度，
每 5 秒切换一次，切换时 LED 闪烁两次提示。

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

    # 第 1 位: 十位数字
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


def flash_leds(saks: SAKSHAT, count: int, delay: float = 0.15) -> None:
    """LED 闪烁提示.

    Args:
        saks: SAKS 实例.
        count: 闪烁次数.
        delay: 每次亮/灭的持续时间 (秒).
    """
    for _ in range(count):
        saks.ledrow.on()
        time.sleep(delay)
        saks.ledrow.off()
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

            # 判断是否需要切换
            if elapsed >= SWITCH_INTERVAL:
                # 闪烁提示
                flash_leds(saks, FLASH_COUNT)
                # 切换模式
                current_mode = MODE_CPU if current_mode == MODE_AMBIENT else MODE_AMBIENT
                last_switch = now

            # 读取并显示温度
            if current_mode == MODE_AMBIENT:
                if has_ds18b20:
                    temp = saks.ds18b20.temperature
                    if temp != -128.0:
                        codes = build_temp_display("C", temp)
                        # LED 指示: 第 1 个 LED 亮表示环境温度
                        saks.ledrow.on_for_index(0)
                    else:
                        codes = [0x00, 0x00, 0x00, 0x00]  # 全灭
                        saks.ledrow.off()
                else:
                    # 无传感器时显示 "----"
                    saks.digital_display.show("----")
                    saks.ledrow.off()
                    time.sleep(0.5)
                    continue

                saks.digital_display.show_raw(codes)

            else:
                temp = get_cpu_temperature()
                if temp > 0:
                    codes = build_temp_display("U", temp)
                    # LED 指示: 第 8 个 LED 亮表示 CPU 温度
                    saks.ledrow.on_for_index(7)
                else:
                    codes = [0x00, 0x00, 0x00, 0x00]
                    saks.ledrow.off()

                saks.digital_display.show_raw(codes)

            # 进度条 LED (显示剩余时间)
            progress = int(elapsed / SWITCH_INTERVAL * 6)  # 0-6 个 LED
            for i in range(1, 7):
                if i <= progress:
                    saks.ledrow.on_for_index(i)
                else:
                    saks.ledrow.off_for_index(i)

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