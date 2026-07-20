#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 03: 温度监控.

展示 DS18B20 温度传感器的使用方法：读取温度、数码管实时显示、高温报警。

硬件要求: 树莓派 + SAKS 扩展板 + DS18B20 温度传感器
运行方式: python3 examples/03_temperature_monitor.py
"""

import time
import sys
import signal

from sakshat import SAKSHAT

HIGH_TEMP_THRESHOLD: float = 40.0


def main() -> None:
    """主函数."""
    print("=" * 50)
    print("  SAKS SDK 示例 03: 温度监控")
    print("=" * 50)

    saks = SAKSHAT()

    print("\n检查 DS18B20 传感器...")
    if not saks.ds18b20.is_exist:
        print("  [错误] 未检测到 DS18B20 温度传感器！")
        saks.cleanup()
        return

    print("  传感器已连接，开始监控 (按 Ctrl+C 退出)...\n")

    last_temp: float = 0.0
    update_count: int = 0

    try:
        while True:
            temp = saks.ds18b20.temperature

            if temp == -128.0:
                print("  [警告] 温度读取失败")
                saks.digital_display.show("----")
                saks.ledrow.off()
                time.sleep(2)
                continue

            saks.digital_display.show(f"{temp:.1f}")
            update_count += 1

            if update_count % 10 == 0:
                print(f"  当前温度: {temp:.1f}°C", end="")
                if temp >= HIGH_TEMP_THRESHOLD:
                    print(" [高温警报!]", end="")
                    saks.ledrow.set_row([True] * 8)
                    saks.buzzer.beep(0.2)
                    time.sleep(0.1)
                    saks.ledrow.off()
                print()

                if last_temp != 0:
                    diff = temp - last_temp
                    if abs(diff) > 0.5:
                        direction = "上升" if diff > 0 else "下降"
                        print(f"  温度变化: {diff:+.1f}°C ({direction})")

            last_temp = temp
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n\n监控已停止。")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("资源已清理。")
        print("=" * 50)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()