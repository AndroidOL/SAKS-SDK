#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例启动器.

启动时自动检查运行环境，确保依赖已安装。

运行方式: python3 examples/main.py
"""

import subprocess
import sys
import os
import platform


# ---- 环境检查 ----
def check_environment() -> dict[str, bool]:
    """检查当前环境是否满足 SAKS SDK 运行要求.

    Returns:
        检查结果字典，键为检查项，值为是否通过.
    """
    results: dict[str, bool] = {}

    # 1. Python 版本
    py_ver = sys.version_info
    results["Python >= 3.10"] = py_ver >= (3, 10)

    # 2. 操作系统
    system = platform.system()
    results["操作系统为 Linux"] = system == "Linux"

    # 3. RPi.GPIO
    try:
        import RPi.GPIO  # noqa: F401
        results["RPi.GPIO 已安装"] = True
    except ImportError:
        results["RPi.GPIO 已安装"] = False

    # 4. sakshat 包可导入
    try:
        import sakshat  # noqa: F401
        results["sakshat 包可导入"] = True
    except ImportError:
        results["sakshat 包可导入"] = False

    # 5. 树莓派检测
    try:
        with open("/proc/device-tree/model") as f:
            model = f.read().strip()
        results["树莓派型号"] = "Raspberry Pi" in model
    except (OSError, FileNotFoundError):
        results["树莓派型号"] = False

    return results


def print_env_report(results: dict[str, bool]) -> None:
    """打印环境检查报告.

    Args:
        results: check_environment() 的返回结果.
    """
    print("=" * 50)
    print("  SAKS SDK 环境检查")
    print("=" * 50)
    print(f"  Python 版本: {sys.version.split()[0]}")
    print(f"  操作系统: {platform.system()} {platform.release()}")
    print(f"  架构: {platform.machine()}")
    print()

    all_ok = True
    for item, passed in results.items():
        if isinstance(passed, bool):
            status = "[OK]" if passed else "[FAIL]"
            if not passed:
                all_ok = False
        else:
            status = passed  # 树莓派型号直接显示
        print(f"  {status} {item}")

    print()
    if not all_ok:
        print("  [警告] 部分检查未通过，某些示例可能无法正常运行。")
        if not results["RPi.GPIO 已安装"]:
            print("         安装方法: sudo apt-get install python3-rpi.gpio")
        if not results["操作系统为 Linux"]:
            print("         当前非 Linux 系统，将使用模拟 GPIO 模式运行示例。")
    else:
        print("  [OK] 所有检查通过，环境就绪。")
    print("=" * 50)


# ---- 示例菜单 ----
EXAMPLES: dict[str, tuple[str, str]] = {
    "1":  ("01_hello_saks.py",              "基础入门 - LED 流水灯 + 蜂鸣器"),
    "2":  ("02_digital_display.py",         "数码管显示 - 数字、小数点、倒计时"),
    "3":  ("03_temperature_monitor.py",     "温度监控 - DS18B20 实时显示"),
    "4":  ("04_button_interaction.py",      "按键与开关交互 - 轻触开关 + 拨码开关"),
    "5":  ("05_cpu_temperature_alarm.py",   "CPU 温度监控与报警"),
    "6":  ("06_full_demo.py",               "综合演示 - 所有功能一次体验"),
    "7":  ("07_segment_deep_dive.py",       "数码管段码深度解析 - 段码控制与字母显示"),
    "8":  ("08_74hc595_deep_dive.py",       "74HC595 芯片深度解析 - 移位寄存器原理"),
    "9":  ("09_tm1637_deep_dive.py",        "TM1637 芯片深度解析 - 通信协议与原始数据"),
    "10": ("10_buzzer_deep_dive.py",        "蜂鸣器深度解析 - PWM 与节奏控制"),
    "11": ("11_led_deep_dive.py",           "LED 深度解析 - 扫描、PWM 与呼吸灯"),
    "12": ("12_ds18b20_deep_dive.py",       "DS18B20 深度解析 - OneWire 协议与 CRC 校验"),
    "13": ("13_temp_dual_display.py",       "温度双通道交替显示 - C/U 格式轮流展示"),
    "14": ("14_scrolling_text.py",          "滚动文字显示 - 数码管跑马灯"),
    "15": ("15_binary_counter.py",          "二进制计数器 - LED 二进制 + 数码管十进制"),
    "16": ("16_reaction_game.py",           "反应速度测试 - 按键反应小游戏"),
    "17": ("17_stopwatch.py",              "秒表计时器 - 按键启停、LED 进度条"),
    "18": ("18_led_scanner.py",            "LED 扫描灯 - 骑士灯/波浪/乒乓/填充排空"),
    "19": ("19_countdown_timer.py",        "倒计时闹钟 - 拨码设时、蜂鸣报警"),
    "20": ("20_temp_alarm.py",             "温度阈值报警 - CPU/环境温度分区指示"),
    "21": ("21_music_box.py",              "音乐盒 - 蜂鸣器演奏旋律 + LED 律动"),
    "22": ("22_electronic_dice.py",        "电子骰子 - 按键摇骰子，LED 点数显示"),
    "23": ("23_breathing_led.py",          "呼吸灯 - 锥形/波浪/交替/心跳多模式"),
    "24": ("24_morse_code.py",             "莫尔斯电码 - 蜂鸣器 + LED 发送电码"),
    "25": ("25_password_lock.py",          "电子密码锁 - 拨码设密码，按键验证"),
    "26": ("26_snake_game.py",             "贪吃蛇 - 8 LED 经典游戏"),
    "27": ("27_metronome.py",              "节拍器 - 可调速/调拍号，LED 视觉节拍"),
    "28": ("28_digital_clock.py",          "数字时钟 - 数码管 HH:MM，LED 秒指示"),
    "29": ("29_guess_number.py",           "猜数字 - 拨码设目标，LED 提示大小"),
    "30": ("30_alarm_siren.py",            "警报器 - 警笛/火警/救护/门铃/倒计时"),
    "31": ("31_lucky_wheel.py",            "幸运大转盘 - LED 旋转，按键停止"),
    "32": ("32_dashboard.py",              "环境仪表盘 - 温度+CPU 综合监测"),
}


def main() -> None:
    """主函数."""
    # 环境检查
    results = check_environment()
    print_env_report(results)
    print()

    # 显示菜单
    print("  请选择要运行的示例:\n")
    for key, (_filename, desc) in EXAMPLES.items():
        print(f"  {key:>2}. {desc}")
    print(f"\n  {'0':>2}. 退出\n")

    try:
        choice = input("  请输入选项 (0-32): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  已取消。")
        return

    if choice == "0" or choice == "":
        print("  再见！")
        return

    if choice not in EXAMPLES:
        print(f"  无效选项: {choice}")
        return

    filename, desc = EXAMPLES[choice]
    script_path = os.path.join(os.path.dirname(__file__), filename)

    if not os.path.exists(script_path):
        print(f"  [错误] 找不到示例文件: {script_path}")
        return

    print(f"\n  启动: {desc}")
    print("  " + "-" * 48)
    subprocess.run([sys.executable, script_path], check=False)


if __name__ == "__main__":
    main()