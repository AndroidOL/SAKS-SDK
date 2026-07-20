#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 04: 按键与开关交互.

展示轻触开关和拨码开关的使用方法：检测按压事件、读取拨码状态、交互控制 LED。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/04_button_interaction.py
"""

import time
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

button_press_count: int = 0
dip_switch_mode: int = 0


def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关事件回调."""
    global button_press_count
    if status:
        button_press_count += 1
        name = "左键" if pin == SAKSPins.TACT_LEFT else "右键"
        print(f"  [{name}] 被按下 (总次数: {button_press_count})")


def on_dip_switch_changed(status: list[bool]) -> None:
    """拨码开关状态变更回调."""
    global dip_switch_mode
    dip_switch_mode = status[0] * 1 + status[1] * 2
    mode_names = {0: "全部关闭", 1: "S1 ON", 2: "S2 ON", 3: "全部开启"}
    print(f"  [拨码开关] 模式 {dip_switch_mode}: {mode_names[dip_switch_mode]}")


def main() -> None:
    """主函数."""
    print("=" * 50)
    print("  SAKS SDK 示例 04: 按键与开关交互")
    print("=" * 50)

    saks = SAKSHAT()
    saks.tact_event_handler = on_tact_event
    saks.dip_switch_status_changed_handler = on_dip_switch_changed

    print("\n操作说明: 按下轻触开关 / 拨动拨码开关 / 按 Ctrl+C 退出\n")

    try:
        while True:
            mode = dip_switch_mode
            if mode == 0:
                for i in range(8):
                    saks.ledrow.on_for_index(i)
                    time.sleep(0.05)
                    saks.ledrow.off_for_index(i)
                saks.digital_display.show("----")
            elif mode == 1:
                saks.ledrow.set_row([True, False, True, False, True, False, True, False])
                saks.digital_display.show(f"{button_press_count:04d}")
            elif mode == 2:
                saks.ledrow.set_row([True, True, True, True, False, False, False, False])
                time.sleep(0.3)
                saks.ledrow.set_row([False, False, False, False, True, True, True, True])
                time.sleep(0.3)
                saks.digital_display.show("----")
            elif mode == 3:
                saks.ledrow.on()
                saks.digital_display.show("FULL")
                saks.buzzer.beep(0.05)
                time.sleep(0.2)
                saks.ledrow.off()
                saks.buzzer.off()
                time.sleep(0.1)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n\n程序已停止。")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("资源已清理。")
        print("=" * 50)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()