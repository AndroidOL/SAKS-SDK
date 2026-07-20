#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 21: 音乐盒 - 蜂鸣器演奏旋律.

使用蜂鸣器演奏经典旋律，LED 随节拍律动，数码管显示当前曲目。
可选曲目: 小星星、欢乐颂、生日快乐。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/21_music_box.py
"""

import time
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# ---- 音符频率表 (Hz) ----
# 第 4 八度: C4=262, D4=294, E4=330, F4=349, G4=392, A4=440, B4=494
# 第 5 八度: C5=523
NOTES: dict[str, int] = {
    "C4": 262, "D4": 294, "E4": 330, "F4": 349,
    "G4": 392, "A4": 440, "B4": 494, "C5": 523,
    "R": 0,  # 休止符
}

# ---- 曲目定义 ----
# 格式: (曲名, [(音符, 时值), ...])
# 时值: 1=四分音符, 0.5=八分音符, 2=二分音符

TWINKLE: list[tuple[str, float]] = [
    ("C4", 0.5), ("C4", 0.5), ("G4", 0.5), ("G4", 0.5),
    ("A4", 0.5), ("A4", 0.5), ("G4", 1.0),
    ("F4", 0.5), ("F4", 0.5), ("E4", 0.5), ("E4", 0.5),
    ("D4", 0.5), ("D4", 0.5), ("C4", 1.0),
    ("G4", 0.5), ("G4", 0.5), ("F4", 0.5), ("F4", 0.5),
    ("E4", 0.5), ("E4", 0.5), ("D4", 1.0),
    ("G4", 0.5), ("G4", 0.5), ("F4", 0.5), ("F4", 0.5),
    ("E4", 0.5), ("E4", 0.5), ("D4", 1.0),
    ("C4", 0.5), ("C4", 0.5), ("G4", 0.5), ("G4", 0.5),
    ("A4", 0.5), ("A4", 0.5), ("G4", 1.0),
    ("F4", 0.5), ("F4", 0.5), ("E4", 0.5), ("E4", 0.5),
    ("D4", 0.5), ("D4", 0.5), ("C4", 1.0),
]

ODE_TO_JOY: list[tuple[str, float]] = [
    ("E4", 0.5), ("E4", 0.5), ("F4", 0.5), ("G4", 0.5),
    ("G4", 0.5), ("F4", 0.5), ("E4", 0.5), ("D4", 0.5),
    ("C4", 0.5), ("C4", 0.5), ("D4", 0.5), ("E4", 0.5),
    ("E4", 0.75), ("D4", 0.25), ("D4", 1.0),
    ("E4", 0.5), ("E4", 0.5), ("F4", 0.5), ("G4", 0.5),
    ("G4", 0.5), ("F4", 0.5), ("E4", 0.5), ("D4", 0.5),
    ("C4", 0.5), ("C4", 0.5), ("D4", 0.5), ("E4", 0.5),
    ("D4", 0.75), ("C4", 0.25), ("C4", 1.0),
]

HAPPY_BIRTHDAY: list[tuple[str, float]] = [
    ("C4", 0.5), ("C4", 0.5), ("D4", 0.5), ("C4", 0.5),
    ("F4", 0.5), ("E4", 1.0),
    ("C4", 0.5), ("C4", 0.5), ("D4", 0.5), ("C4", 0.5),
    ("G4", 0.5), ("F4", 1.0),
    ("C4", 0.5), ("C4", 0.5), ("C5", 0.5), ("A4", 0.5),
    ("F4", 0.5), ("E4", 0.5), ("D4", 1.0),
    ("B4", 0.5), ("B4", 0.5), ("A4", 0.5), ("F4", 0.5),
    ("G4", 0.5), ("F4", 1.0),
]

SONGS: list[tuple[str, str, list[tuple[str, float]]]] = [
    ("S1", "小星星", TWINKLE),
    ("S2", "欢乐颂", ODE_TO_JOY),
    ("S3", "生日快乐", HAPPY_BIRTHDAY),
]

# ---- 全局状态 ----
current_song_idx: int = 0
beep_requested: bool = False


def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关切换曲目."""
    global current_song_idx, beep_requested
    if not status:
        return
    if pin == SAKSPins.TACT_RIGHT:
        current_song_idx = (current_song_idx + 1) % len(SONGS)
    elif pin == SAKSPins.TACT_LEFT:
        current_song_idx = (current_song_idx - 1) % len(SONGS)
    beep_requested = True


def play_note(saks: SAKSHAT, note: str, duration: float, tempo: float) -> None:
    """演奏单个音符.

    Args:
        saks: SAKS 实例.
        note: 音符名称 (如 "C4").
        duration: 时值 (1.0=四分音符).
        tempo: 每分钟节拍数，决定音符实际时长.
    """
    freq = NOTES.get(note, 0)
    if freq > 0:
        # 蜂鸣器 PWM 发声
        from sakshat._gpio import GPIO
        pwm = GPIO.PWM(SAKSPins.BUZZER, freq)
        pwm.start(50)
        time.sleep(60.0 / tempo * duration * 0.9)  # 音符时长
        pwm.stop()
        time.sleep(60.0 / tempo * duration * 0.1)  # 音符间隔
    else:
        time.sleep(60.0 / tempo * duration)


def show_led_beat(saks: SAKSHAT, beat_pos: int) -> None:
    """LED 随节拍律动.

    Args:
        saks: SAKS 实例.
        beat_pos: 当前节拍位置 (0-7).
    """
    row = [False] * 8
    row[beat_pos % 8] = True
    row[(beat_pos + 4) % 8] = True
    saks.ledrow.set_row(row)


def main() -> None:
    """主函数."""
    global current_song_idx, beep_requested

    print("=" * 58)
    print("  SAKS SDK 示例 21: 音乐盒")
    print("=" * 58)
    print()
    print("  操作说明:")
    print("    右键 (TACT_RIGHT): 下一首曲目")
    print("    左键 (TACT_LEFT):  上一首曲目")
    print("    拨码开关 S1: 速度 (ON=快, OFF=慢)")
    print("    拨码开关 S2: 循环播放 (ON=循环, OFF=单次)")
    print("    按 Ctrl+C 退出")
    print()

    saks = SAKSHAT()
    saks.tact_event_handler = on_tact_event

    try:
        while True:
            code, name, melody = SONGS[current_song_idx]
            tempo = 120 if saks.dip_switch.is_on[0] else 80
            loop = saks.dip_switch.is_on[1]

            print(f"\n  正在演奏: {name} ({code})  tempo={tempo}")
            saks.digital_display.show(f"{code}{tempo // 10:2d}")

            beat_idx = 0
            for note, duration in melody:
                # 响应按键切换
                if beep_requested:
                    beep_requested = False
                    break

                show_led_beat(saks, beat_idx)
                play_note(saks, note, duration, tempo)
                beat_idx = (beat_idx + 1) % 8

            saks.ledrow.off()
            saks.buzzer.off()

            if not loop:
                print("  演奏完毕，按右键播放下一首...")
                # 等待按键
                while not beep_requested:
                    time.sleep(0.1)
                beep_requested = False

    except KeyboardInterrupt:
        print("\n\n  音乐盒已停止。")
    finally:
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("  资源已清理。")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()