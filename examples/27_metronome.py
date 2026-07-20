#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 27: 节拍器.

蜂鸣器打节拍，LED 视觉指示当前拍子。
按键调整速度，拨码开关切换拍号。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/27_metronome.py
"""

import time
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 节拍器常量 ----
DEFAULT_BPM: int = 120
MIN_BPM: int = 40
MAX_BPM: int = 240
BPM_STEP: int = 10

# 拍号: (拍数, 简称)
TIME_SIGNATURES: list[tuple[int, str]] = [
    (2, "2/4"),
    (3, "3/4"),
    (4, "4/4"),
    (6, "6/8"),
]

current_bpm: int = DEFAULT_BPM
current_ts_idx: int = 2  # 默认 4/4
beep_requested: bool = False


def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关调整速度."""
    global current_bpm, beep_requested
    if not status:
        return
    if pin == SAKSPins.TACT_RIGHT:
        current_bpm = min(MAX_BPM, current_bpm + BPM_STEP)
    elif pin == SAKSPins.TACT_LEFT:
        current_bpm = max(MIN_BPM, current_bpm - BPM_STEP)
    beep_requested = True


def main() -> None:
    """主函数."""
    global current_bpm, current_ts_idx, beep_requested

    print("=" * 58)
    print("  SAKS SDK 示例 27: 节拍器")
    print("=" * 58)
    print()
    print("  操作说明:")
    print("    右键 (TACT_RIGHT): 加速 (+10 BPM)")
    print("    左键 (TACT_LEFT):  减速 (-10 BPM)")
    print("    拨码开关: 切换拍号 (2/4, 3/4, 4/4, 6/8)")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()
    saks.tact_event_handler = on_tact_event

    # 拍号数组
    ts_names = [ts[1] for ts in TIME_SIGNATURES]

    try:
        while True:
            if beep_requested:
                beep_requested = False

            # 读取拍号
            dip = saks.dip_switch.is_on
            if dip[0] and dip[1]:
                current_ts_idx = 3
            elif dip[0]:
                current_ts_idx = 1
            elif dip[1]:
                current_ts_idx = 2
            else:
                current_ts_idx = 0

            beats, ts_name = TIME_SIGNATURES[current_ts_idx]
            beat_interval = 60.0 / current_bpm

            # 数码管显示 BPM
            saks.digital_display.show(f"{current_bpm:3d} ")
            time.sleep(0.4)
            saks.digital_display.show(ts_name.replace("/", ""))
            time.sleep(0.4)

            # 开始打拍
            print(f"  BPM={current_bpm}  拍号={ts_name}  按 Ctrl+C 退出")
            print("  1 2 3 4 ...", end="", flush=True)

            # 每拍一行
            beat_count = 0
            for _ in range(beats * 4):  # 打 4 个小节
                beat_count += 1
                beat_pos = (beat_count - 1) % beats + 1

                # 显示当前拍
                saks.digital_display.show(f"b{beat_pos}{current_bpm:3d}"[-4:])

                # LED 指示: 第一拍最亮
                if beat_pos == 1:
                    # 重拍: 全部 LED 闪一下
                    saks.ledrow.on()
                else:
                    # 轻拍: 只亮对应位置的 LED
                    row = [False] * 8
                    row[beat_pos - 1] = True
                    saks.ledrow.set_row(row)

                # 蜂鸣: 第一拍音调高
                saks.buzzer.beep(0.05 if beat_pos == 1 else 0.03)

                # 打印拍子
                if beat_pos == 1:
                    print(f"\n  {beat_pos}", end="", flush=True)
                else:
                    print(f" {beat_pos}", end="", flush=True)

                saks.ledrow.off()
                time.sleep(beat_interval * 0.7)

                # 检查是否调整了
                if beep_requested:
                    beep_requested = False
                    break

            print()
            saks.ledrow.off()

    except KeyboardInterrupt:
        print("\n\n  节拍器已停止。")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()