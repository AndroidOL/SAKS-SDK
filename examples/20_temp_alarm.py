#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 20: 温度阈值报警器.

通过拨码开关设置温度报警阈值，在 4 位数码管上实时显示 CPU 或 DS18B20
温度。温度超过阈值时 LED 报警灯闪烁、蜂鸣器报警、数码管交替显示温度
和 "AL" 报警标志。

左键切换温度来源 (CPU / DS18B20)，右键静音/取消静音蜂鸣器。

硬件要求: 树莓派 + SAKS 扩展板 + DS18B20 (可选)
运行方式: python3 examples/20_temp_alarm.py
"""

import time
import sys
import signal

from sakshat import SAKSHAT, DigitalDisplay

# =============================================================================
# 配置常量
# =============================================================================
UPDATE_INTERVAL: float = 0.5          # 显示更新间隔 (秒)
LOOP_INTERVAL: float = 0.05           # 主循环轮询间隔 (秒)
ALARM_BEEP_INTERVAL: float = 2.0      # 报警蜂鸣间隔 (秒)
ALARM_DISPLAY_INTERVAL: float = 1.0   # 报警时显示切换间隔 (秒)
BUTTON_DEBOUNCE: float = 0.3          # 按键消抖时间 (秒)
LED_FLASH_RATE: float = 0.1           # LED 报警闪烁速度 (秒/周期)

# 拨码开关 -> 温度阈值映射
#  (Dip1, Dip2) -> 阈值 °C
THRESHOLD_MAP: dict[tuple[bool, bool], float] = {
    (False, False): 50.0,   # 拨码 1 OFF, 拨码 2 OFF
    (True,  False): 60.0,   # 拨码 1 ON,  拨码 2 OFF
    (False, True):  70.0,   # 拨码 1 OFF, 拨码 2 ON
    (True,  True):  80.0,   # 拨码 1 ON,  拨码 2 ON
}

# 报警区域划分 (相对于阈值的偏移)
ZONE_GREEN_OFFSET: float = 10.0   # 安全区: 阈值 - 10°C 以下
ZONE_YELLOW_OFFSET: float = 5.0   # 警告区: 阈值 - 10°C 到阈值 - 5°C

# 温度来源
SOURCE_CPU: int = 0
SOURCE_DS18B20: int = 1

# 数字 0-9 段码 (不含小数点)
DIGIT_CODES: dict[int, int] = {
    0: 0x3F, 1: 0x06, 2: 0x5B, 3: 0x4F, 4: 0x66,
    5: 0x6D, 6: 0x7D, 7: 0x07, 8: 0x7F, 9: 0x6F,
}


# =============================================================================
# 辅助函数
# =============================================================================

def get_cpu_temperature() -> float:
    """读取树莓派 CPU 温度.

    从 /sys/class/thermal/thermal_zone0/temp 读取原始值 (毫摄氏度)，
    转换为摄氏度后返回。

    Returns:
        CPU 温度 (摄氏度)，读取失败返回 -1.0.
    """
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return float(f.read().strip()) / 1000.0
    except (OSError, ValueError):
        return -1.0


def get_threshold(dip: list[bool]) -> float:
    """根据拨码开关状态获取报警阈值.

    Args:
        dip: 两位拨码开关状态 [dip1, dip2].

    Returns:
        对应的温度阈值 (摄氏度).
    """
    key = (dip[0], dip[1]) if len(dip) >= 2 else (False, False)
    return THRESHOLD_MAP.get(key, 50.0)


def build_temp_display(prefix: str, temperature: float) -> list[int]:
    """构造温度显示段码数组.

    将温度格式化为 "X12.3" 形式 (前缀字母 + 数字部分含小数点)。
    当温度超过 99.9 时显示 "Hi"，低于 -9.9 时显示 "Lo"。

    Args:
        prefix: 前缀字母，如 "C" (CPU) 或 "U" (DS18B20/环境).
        temperature: 温度值 (摄氏度).

    Returns:
        4 个段码的列表，对应数码管第 0-3 位.

    Example:
        >>> build_temp_display("C", 45.2)
        [0x39, 0x66, 0xED, 0x5B]  # C 4 5. 2
    """
    # 超范围处理
    if temperature > 99.9:
        # 显示 "Hi  " (H, i, 空白, 空白)
        return [
            DigitalDisplay.CHAR_MAP.get("H", 0x76),
            0x06,  # i = 段码 0x06 (b, c 段)
            0x00,
            0x00,
        ]
    if temperature < -9.9:
        return [
            DigitalDisplay.CHAR_MAP.get("L", 0x38),
            DigitalDisplay.CHAR_MAP.get("o", 0x5C),
            0x00,
            0x00,
        ]

    abs_temp = abs(temperature)
    int_part = int(abs_temp)
    dec_part = int(round(abs_temp - int_part, 1) * 10)

    codes: list[int] = []

    # 第 0 位: 前缀字母
    code = DigitalDisplay.CHAR_MAP.get(prefix.upper(), 0x00)
    codes.append(code)

    # 第 1 位: 十位数字 (或负号)
    if temperature < 0:
        codes.append(0x40)  # 负号 "-"
    elif int_part >= 10:
        codes.append(DIGIT_CODES.get(int_part // 10, 0x00))
    else:
        codes.append(0x00)  # 空白

    # 第 2 位: 个位数字 + 小数点
    ones_code = DIGIT_CODES.get(int_part % 10, 0x00)
    codes.append(ones_code | 0x80)

    # 第 3 位: 小数位
    codes.append(DIGIT_CODES.get(dec_part, 0x00))

    return codes


def build_alarm_display() -> list[int]:
    """构造报警显示段码数组 "AL  ".

    Returns:
        4 个段码的列表: [A, L, 空白, 空白].
    """
    return [
        DigitalDisplay.CHAR_MAP.get("A", 0x77),
        DigitalDisplay.CHAR_MAP.get("L", 0x38),
        0x00,
        0x00,
    ]


def update_led_gauge(saks: SAKSHAT, temperature: float, threshold: float) -> None:
    """根据温度和阈值更新 LED 温度指示条.

    LED 分区:
        - 绿色区 (LED 1-2, 索引 0-1): 温度 < 阈值 - 10°C
        - 黄色区 (LED 3-4, 索引 2-3): 阈值 - 10°C <= 温度 < 阈值 - 5°C
        - 橙色区 (LED 5-6, 索引 4-5): 阈值 - 5°C <= 温度 < 阈值
        - 红色区 (LED 7-8, 索引 6-7): 温度 >= 阈值

    Args:
        saks: SAKSHAT 实例.
        temperature: 当前温度 (摄氏度).
        threshold: 报警阈值 (摄氏度).
    """
    # 确定当前所在区域
    if temperature < threshold - ZONE_GREEN_OFFSET:
        active_zone = 0  # 绿色
    elif temperature < threshold - ZONE_YELLOW_OFFSET:
        active_zone = 1  # 黄色
    elif temperature < threshold:
        active_zone = 2  # 橙色
    else:
        active_zone = 3  # 红色

    # 更新所有 LED
    for i in range(8):
        if i < 2:
            zone = 0  # 绿色区
        elif i < 4:
            zone = 1  # 黄色区
        elif i < 6:
            zone = 2  # 橙色区
        else:
            zone = 3  # 红色区

        if zone <= active_zone:
            saks.ledrow.on_for_index(i)
        else:
            saks.ledrow.off_for_index(i)


# =============================================================================
# 主函数
# =============================================================================

def main() -> None:
    """主函数."""
    print("=" * 58)
    print("  SAKS SDK 示例 20: 温度阈值报警器")
    print("=" * 58)
    print()
    print("  拨码开关设置报警阈值:")
    print("    Dip1 OFF + Dip2 OFF = 50°C")
    print("    Dip1 ON  + Dip2 OFF = 60°C")
    print("    Dip1 OFF + Dip2 ON  = 70°C")
    print("    Dip1 ON  + Dip2 ON  = 80°C")
    print()
    print("  操作说明:")
    print("    左键: 切换温度来源 (CPU / DS18B20)")
    print("    右键: 静音/取消静音蜂鸣器")
    print("    显示格式: C = CPU 温度, U = DS18B20 环境温度")
    print("    按 Ctrl+C 退出")
    print()

    with SAKSHAT() as saks:
        # ---- 状态变量 ----
        temp_source: int = SOURCE_CPU        # 当前温度来源
        buzzer_muted: bool = False           # 蜂鸣器是否静音
        show_alarm: bool = False             # 是否显示报警标志
        alarm_active: bool = False           # 当前是否处于报警状态

        # 按键消抖状态
        last_left_state: bool = False
        last_right_state: bool = False
        last_left_press: float = 0.0
        last_right_press: float = 0.0

        # 定时器
        last_update: float = 0.0             # 上次显示更新
        last_beep: float = 0.0               # 上次蜂鸣
        last_display_toggle: float = 0.0     # 上次显示切换
        last_led_flash: float = 0.0          # 上次 LED 闪烁切换
        led_flash_on: bool = True            # LED 闪烁当前状态

        # 检查 DS18B20 传感器
        has_ds18b20: bool = saks.ds18b20.is_exist
        if not has_ds18b20:
            print("  [提示] 未检测到 DS18B20，仅支持 CPU 温度监控")
            print()

        try:
            while True:
                now = time.time()

                # ---- 读取温度 ----
                if temp_source == SOURCE_CPU:
                    temperature = get_cpu_temperature()
                    prefix = "C"
                else:
                    if has_ds18b20:
                        temperature = saks.ds18b20.temperature
                        if temperature == -128.0:
                            temperature = -1.0  # 读取失败
                    else:
                        temperature = -1.0
                    prefix = "U"

                # ---- 读取拨码开关，获取阈值 ----
                dip_status = saks.dip_switch.is_on
                threshold = get_threshold(dip_status)

                # ---- 检测左键 (切换温度来源) ----
                left_state = saks.tactrow.is_on(0)
                if left_state and not last_left_state:
                    if now - last_left_press > BUTTON_DEBOUNCE:
                        temp_source = SOURCE_DS18B20 if temp_source == SOURCE_CPU else SOURCE_CPU
                        new_label = "DS18B20" if temp_source == SOURCE_DS18B20 else "CPU"
                        print(f"  [切换] 温度来源 -> {new_label}")
                        last_left_press = now
                        # 切换来源时退出报警状态，避免显示混乱
                        show_alarm = False
                        alarm_active = False
                last_left_state = left_state

                # ---- 检测右键 (静音/取消静音) ----
                right_state = saks.tactrow.is_on(1)
                if right_state and not last_right_state:
                    if now - last_right_press > BUTTON_DEBOUNCE:
                        buzzer_muted = not buzzer_muted
                        status = "静音" if buzzer_muted else "取消静音"
                        print(f"  [蜂鸣器] {status}")
                        last_right_press = now
                last_right_state = right_state

                # ---- 判断报警状态 ----
                is_alarm = temperature >= threshold and temperature > 0

                if is_alarm:
                    # 进入报警状态
                    if not alarm_active:
                        alarm_active = True
                        show_alarm = False
                        last_display_toggle = now
                        last_beep = now
                        last_led_flash = now
                        led_flash_on = True

                    # 显示切换: 温度和 "AL" 交替，每 1 秒切换
                    if now - last_display_toggle >= ALARM_DISPLAY_INTERVAL:
                        show_alarm = not show_alarm
                        last_display_toggle = now

                    # 蜂鸣器: 每 2 秒响一次
                    if not buzzer_muted and now - last_beep >= ALARM_BEEP_INTERVAL:
                        saks.buzzer.beep(0.1)
                        last_beep = now

                    # LED 红色区域 (索引 6-7) 亮起，LED 8 (索引 7) 快速闪烁
                    saks.ledrow.on_for_index(6)  # LED 7 常亮
                    if now - last_led_flash >= LED_FLASH_RATE:
                        led_flash_on = not led_flash_on
                        last_led_flash = now
                    if led_flash_on:
                        saks.ledrow.on_for_index(7)
                    else:
                        saks.ledrow.off_for_index(7)

                    # 关闭非红色区 LED
                    for i in range(6):
                        saks.ledrow.off_for_index(i)

                else:
                    # 退出报警状态
                    if alarm_active:
                        alarm_active = False
                        show_alarm = False

                    # 正常 LED 温度指示条
                    update_led_gauge(saks, temperature, threshold)

                # ---- 更新数码管显示 (每 0.5 秒) ----
                if now - last_update >= UPDATE_INTERVAL:
                    last_update = now

                    if temperature < 0:
                        # 温度读取失败，显示 "----"
                        saks.digital_display.show("----")
                    elif is_alarm and show_alarm:
                        # 报警时交替显示 "AL  "
                        codes = build_alarm_display()
                        saks.digital_display.show_raw(codes)
                    else:
                        # 正常显示温度
                        codes = build_temp_display(prefix, temperature)
                        saks.digital_display.show_raw(codes)

                time.sleep(LOOP_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n  监控已停止。")
        finally:
            saks.digital_display.off()
            saks.ledrow.off()
            print("  资源已清理。")
            print("=" * 58)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()