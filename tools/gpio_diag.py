#!/usr/bin/env python3
"""GPIO 边沿检测诊断工具.

检测当前 Raspberry Pi 环境中的 GPIO 边沿检测支持情况，
帮助诊断 RPi.GPIO / lgpio 兼容性问题。

用法:
    python tools/gpio_diag.py

输出:
    - 系统信息 (内核版本、Raspberry Pi 型号)
    - GPIO 后端可用性 (lgpio / RPi.GPIO)
    - 各引脚的边沿检测测试结果
    - 建议的修复方案
"""

from __future__ import annotations

import sys
import subprocess
import time


def run_cmd(cmd: list[str]) -> str:
    """运行命令并返回输出."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() + result.stderr.strip()
    except Exception as e:
        return f"(失败: {e})"


def check_system() -> dict[str, str]:
    """检查系统信息."""
    info: dict[str, str] = {}
    info["kernel"] = run_cmd(["uname", "-r"])
    info["model"] = run_cmd(["cat", "/proc/device-tree/model"])
    # 检查 sysfs GPIO 是否已弃用
    info["sysfs_gpio"] = (
        "可用" if run_cmd(["ls", "/sys/class/gpio"]) else "不可用"
    )
    # 检查 gpiochip 是否可用
    info["gpiochip"] = (
        "可用" if run_cmd(["ls", "/dev/gpiochip0"]) else "不可用"
    )
    return info


def test_lgpio_edge_detection(pins: list[int]) -> dict[str, bool | str]:
    """使用 lgpio 测试边沿检测."""
    result: dict[str, bool | str] = {}
    try:
        import lgpio
        result["available"] = True
        h = lgpio.gpiochip_open(0)

        for pin in pins:
            try:
                # 设置为输入上拉
                lgpio.gpio_claim_input(h, pin, lgpio.SET_PULL_UP)
                lgpio.gpio_free(h, pin)

                # 尝试边沿检测
                events: list[int] = []

                def _cb(chip: int, gpio: int, level: int, timestamp: int) -> None:
                    events.append(level)

                lgpio.gpio_claim_alert(h, pin, lgpio.BOTH_EDGES, lgpio.SET_PULL_UP)
                cb = lgpio.callback(h, pin, lgpio.BOTH_EDGES, _cb)
                time.sleep(0.01)
                cb.cancel()
                lgpio.gpio_free(h, pin)
                result[f"pin_{pin}"] = True
            except Exception as e:
                result[f"pin_{pin}"] = str(e)

        lgpio.gpiochip_close(h)
    except ImportError:
        result["available"] = False
        result["error"] = "lgpio 未安装 (apt install python3-lgpio)"
    except Exception as e:
        result["available"] = False
        result["error"] = str(e)

    return result


def test_rpi_gpio_edge_detection(pins: list[int]) -> dict[str, bool | str]:
    """使用 RPi.GPIO 测试边沿检测."""
    result: dict[str, bool | str] = {}
    try:
        import RPi.GPIO as GPIO
        result["available"] = True
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        for pin in pins:
            try:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                events: list[int] = []

                def _cb(channel: int) -> None:
                    events.append(channel)

                GPIO.add_event_detect(pin, GPIO.BOTH, callback=_cb, bouncetime=50)
                time.sleep(0.01)
                GPIO.remove_event_detect(pin)
                result[f"pin_{pin}"] = True
            except Exception as e:
                result[f"pin_{pin}"] = str(e)

        GPIO.cleanup()
    except ImportError:
        result["available"] = False
        result["error"] = "RPi.GPIO 未安装"
    except Exception as e:
        result["available"] = False
        result["error"] = str(e)

    return result


def test_sakshat_backend() -> dict[str, str]:
    """检查 sakshat 当前使用的 GPIO 后端."""
    result: dict[str, str] = {}
    try:
        from sakshat._gpio import GPIO
        gpio_type = type(GPIO).__name__
        gpio_module = type(GPIO).__module__
        result["backend"] = f"{gpio_module}.{gpio_type}"

        if gpio_type == "_LgpioBackend":
            result["recommendation"] = "lgpio 后端已激活，边沿检测应正常工作"
        elif gpio_type == "RPiOSInfo":
            # RPi.GPIO module type
            result["recommendation"] = (
                "RPi.GPIO 后端 (sysfs 接口)，边沿检测可能不可用。"
                "建议: apt install python3-lgpio"
            )
        else:
            result["recommendation"] = f"未知后端: {gpio_type}"
    except Exception as e:
        result["error"] = str(e)

    return result


def main() -> None:
    """运行诊断."""
    pins = [21, 26, 16, 20]  # SAKS 扩展板开关引脚

    print("=" * 60)
    print("  SAKS SDK GPIO 边沿检测诊断工具")
    print("=" * 60)

    # 1. 系统信息
    print("\n── 系统信息 ──")
    sys_info = check_system()
    print(f"  内核版本:    {sys_info['kernel']}")
    print(f"  树莓派型号:  {sys_info['model']}")
    print(f"  sysfs GPIO:  {sys_info['sysfs_gpio']}")
    print(f"  gpiochip:    {sys_info['gpiochip']}")

    # 2. lgpio 测试
    print(f"\n── lgpio 边沿检测 (引脚: {pins}) ──")
    lgpio_result = test_lgpio_edge_detection(pins)
    if lgpio_result.get("available"):
        for pin in pins:
            key = f"pin_{pin}"
            status = lgpio_result.get(key, "未测试")
            if status is True:
                print(f"  引脚 {pin}: ✅ 正常")
            else:
                print(f"  引脚 {pin}: ❌ {status}")
    else:
        print(f"  ❌ {lgpio_result.get('error', '不可用')}")

    # 3. RPi.GPIO 测试
    print(f"\n── RPi.GPIO 边沿检测 (引脚: {pins}) ──")
    rpi_result = test_rpi_gpio_edge_detection(pins)
    if rpi_result.get("available"):
        for pin in pins:
            key = f"pin_{pin}"
            status = rpi_result.get(key, "未测试")
            if status is True:
                print(f"  引脚 {pin}: ✅ 正常")
            else:
                print(f"  引脚 {pin}: ❌ {status}")
    else:
        print(f"  ❌ {rpi_result.get('error', '不可用')}")

    # 4. sakshat 后端
    print("\n── sakshat 当前后端 ──")
    sakshat_info = test_sakshat_backend()
    if "error" in sakshat_info:
        print(f"  ❌ 错误: {sakshat_info['error']}")
    else:
        print(f"  后端: {sakshat_info['backend']}")
        print(f"  建议: {sakshat_info.get('recommendation', '无')}")

    # 5. 总结
    print("\n── 总结 ──")
    lgpio_ok = all(
        lgpio_result.get(f"pin_{p}") is True for p in pins
    )
    rpi_ok = all(
        rpi_result.get(f"pin_{p}") is True for p in pins
    )

    if lgpio_ok:
        print("  ✅ lgpio 边沿检测全部正常")
        print("  安装 lgpio 后 sakshat 将自动使用 lgpio 后端")
        print("  操作: sudo apt install python3-lgpio")
    elif rpi_ok:
        print("  ⚠️  RPi.GPIO 边沿检测正常，lgpio 不可用")
        print("  当前 RPi.GPIO 后端可正常工作，无需额外操作")
    else:
        print("  ❌ 两个后端均不支持边沿检测")
        print("  SDK 将自动降级为轮询模式，程序仍可正常运行")
        print("  建议: 检查内核版本和 GPIO 权限")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()