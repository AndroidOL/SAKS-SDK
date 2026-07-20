#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 19: 倒计时器.

使用 SAKS 扩展板实现一个功能完整的倒计时器：
- 拨码开关设置倒计时时长 (30/60/90/120 秒)
- 左键: 启动/暂停倒计时
- 右键: 暂停或结束时重置
- 4 位数码管显示 "MM:SS" 格式，冒号 (小数点) 闪烁
- 8 颗 LED 作为进度条，随剩余时间逐渐熄灭
- 倒计时结束: 蜂鸣器报警 3 次 + LED 全闪 + 数码管闪烁

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/19_countdown_timer.py
"""

import math
import time
import sys
import signal
from enum import Enum, auto

from sakshat import SAKSHAT, SAKSPins


# =============================================================================
# 倒计时器状态枚举
# =============================================================================

class TimerState(Enum):
    """倒计时器状态."""
    IDLE = auto()       # 等待启动
    RUNNING = auto()    # 正在倒计时
    PAUSED = auto()     # 已暂停
    FINISHED = auto()   # 倒计时结束


# =============================================================================
# 配置常量
# =============================================================================

# 拨码开关对应的倒计时时长 (秒)
# 编码: (S1, S2) -> 秒数
#   S1=OFF, S2=OFF -> 30 秒
#   S1=ON,  S2=OFF -> 60 秒
#   S1=OFF, S2=ON  -> 90 秒
#   S1=ON,  S2=ON  -> 120 秒
DIP_DURATION_MAP: dict[tuple[bool, bool], int] = {
    (False, False): 30,
    (True,  False): 60,
    (False, True):  90,
    (True,  True):  120,
}

# 冒号闪烁间隔 (秒)
COLON_BLINK_INTERVAL: float = 0.5

# LED 数量
LED_COUNT: int = 8

# 倒计时结束报警参数
ALARM_BEEP_ON: float = 0.1       # 每次蜂鸣持续时间 (秒)
ALARM_BEEP_OFF: float = 0.1      # 每次蜂鸣间隔时间 (秒)
ALARM_BEEP_COUNT: int = 3        # 蜂鸣次数

# 结束状态闪烁参数
FINISHED_FLASH_ON: float = 0.3   # 亮起持续时间 (秒)
FINISHED_FLASH_OFF: float = 0.3  # 熄灭持续时间 (秒)

# 主循环轮询间隔 (秒)
POLL_INTERVAL: float = 0.05


# =============================================================================
# 全局状态 (用于中断回调与主循环之间通信)
# =============================================================================

# 标记左键是否被按下 (GPIO 中断回调中设置)
_left_pressed: bool = False

# 标记右键是否被按下 (GPIO 中断回调中设置)
_right_pressed: bool = False


# =============================================================================
# GPIO 事件回调函数
# =============================================================================

def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关事件回调函数.

    当用户按下或释放 SAKS 扩展板上的轻触开关时，由 Tact 模块通过
    GPIO 中断自动调用此函数。仅处理「按下」事件 (status == True)。

    Args:
        pin: 触发事件的 GPIO 引脚编号 (BCM 编号).
        status: 当前状态，True 表示按下，False 表示释放.
    """
    global _left_pressed, _right_pressed
    if status:
        if pin == SAKSPins.TACT_LEFT:
            _left_pressed = True
        elif pin == SAKSPins.TACT_RIGHT:
            _right_pressed = True


# =============================================================================
# 辅助函数: 读取拨码开关并获取对应时长
# =============================================================================

def read_duration(saks: SAKSHAT) -> tuple[int, str]:
    """读取拨码开关状态并返回对应的倒计时时长.

    拨码开关组合:
        S1=OFF, S2=OFF -> 30 秒
        S1=ON,  S2=OFF -> 60 秒
        S1=OFF, S2=ON  -> 90 秒
        S1=ON,  S2=ON  -> 120 秒

    Args:
        saks: SAKSHAT 主控制器实例.

    Returns:
        (duration_seconds, description) 元组:
            - duration_seconds: 倒计时时长 (秒).
            - description: 人类可读的描述字符串.
    """
    status = saks.dip_switch.is_on
    s1, s2 = status[0], status[1]
    duration = DIP_DURATION_MAP.get((s1, s2), 30)
    desc = (
        f"S1={'ON' if s1 else 'OFF'}, S2={'ON' if s2 else 'OFF'}"
        f" -> {duration} 秒"
    )
    return duration, desc


# =============================================================================
# 辅助函数: 数码管显示
# =============================================================================

def format_time_display(total_seconds: float, show_colon: bool) -> str:
    """将秒数格式化为数码管显示字符串.

    显示格式为 "MM.SS"，其中小数点作为冒号分隔符。
    例如 90 秒 -> "01.30"，45 秒 -> "00.45"。

    Args:
        total_seconds: 总秒数 (非负数).
        show_colon: 是否显示冒号 (小数点). False 时不显示小数点.

    Returns:
        格式化后的显示字符串，如 "01.30" 或 "0130".
    """
    clamped = max(0.0, total_seconds)
    minutes = int(clamped) // 60
    seconds = int(clamped) % 60
    if show_colon:
        return f"{minutes:02d}.{seconds:02d}"
    else:
        return f"{minutes:02d}{seconds:02d}"


def show_countdown(saks: SAKSHAT, remaining: float, show_colon: bool) -> None:
    """在数码管上显示倒计时时间.

    Args:
        saks: SAKSHAT 主控制器实例.
        remaining: 剩余秒数.
        show_colon: 是否显示冒号 (小数点).
    """
    saks.digital_display.show(format_time_display(remaining, show_colon))


# =============================================================================
# 辅助函数: LED 进度条
# =============================================================================

def update_led_progress(saks: SAKSHAT, remaining: float, total: float) -> None:
    """根据剩余时间比例更新 8 颗 LED 的进度条显示.

    LED 从全亮 (100% 剩余) 逐渐熄灭到全灭 (0% 剩余)。
    使用 math.ceil 确保只要还有时间剩余，至少有一颗 LED 亮着。

    Args:
        saks: SAKSHAT 主控制器实例.
        remaining: 剩余秒数.
        total: 总秒数.
    """
    if total <= 0:
        saks.ledrow.off()
        return

    ratio = max(0.0, min(1.0, remaining / total))
    # 向上取整: ratio=0.99 -> 8 颗全亮; ratio=0.001 -> 1 颗亮; ratio=0 -> 0 颗亮
    led_on_count = max(0, math.ceil(ratio * LED_COUNT))

    # 构建 LED 状态列表: 前 led_on_count 颗亮，其余灭
    status = [True] * led_on_count + [False] * (LED_COUNT - led_on_count)
    saks.ledrow.set_row(status)


# =============================================================================
# 辅助函数: 倒计时结束动画
# =============================================================================

def play_finished_alarm(saks: SAKSHAT) -> None:
    """播放倒计时结束的报警效果.

    执行以下动作序列:
        1. 蜂鸣器: beep_pattern 3 次 (0.1s 响, 0.1s 停) -- 阻塞
        2. LED 全闪: 全部 LED 闪烁 3 次，同时数码管显示 "00.00" 闪烁

    注意: 此函数会阻塞直到动画完成。

    Args:
        saks: SAKSHAT 主控制器实例.
    """
    # ---- 蜂鸣器报警: 3 次短哔 ----
    saks.buzzer.beep_pattern(ALARM_BEEP_ON, ALARM_BEEP_OFF, ALARM_BEEP_COUNT)

    # ---- LED 和数码管交替闪烁 3 次 ----
    for _ in range(ALARM_BEEP_COUNT):
        # 亮起阶段: 所有 LED 全亮 + 数码管显示 "00.00"
        saks.ledrow.on()
        saks.digital_display.show("00.00")
        time.sleep(FINISHED_FLASH_ON)

        # 熄灭阶段: 所有 LED 全灭 + 数码管熄灭
        saks.ledrow.off()
        saks.digital_display.off()
        time.sleep(FINISHED_FLASH_OFF)

    # 最终保持显示 "00.00"
    saks.digital_display.show("00.00")
    saks.ledrow.off()


# =============================================================================
# 辅助函数: 消费按键事件
# =============================================================================

def consume_left_press() -> bool:
    """消费并返回左键是否被按下.

    读取全局标志后将其重置为 False，实现 "边沿触发" 语义，
    避免同一次按键被重复处理。

    Returns:
        True 如果左键被按下过，否则 False.
    """
    global _left_pressed
    if _left_pressed:
        _left_pressed = False
        return True
    return False


def consume_right_press() -> bool:
    """消费并返回右键是否被按下.

    Returns:
        True 如果右键被按下过，否则 False.
    """
    global _right_pressed
    if _right_pressed:
        _right_pressed = False
        return True
    return False


def clear_all_presses() -> None:
    """清除所有按键缓冲."""
    global _left_pressed, _right_pressed
    _left_pressed = False
    _right_pressed = False


# =============================================================================
# 辅助函数: 键盘中断处理
# =============================================================================

def handle_keyboard_interrupt(
    state: TimerState, remaining: float
) -> None:
    """处理 KeyboardInterrupt，打印当前状态并安全退出.

    Args:
        state: 当前倒计时器状态.
        remaining: 当前剩余秒数.
    """
    state_names = {
        TimerState.IDLE: "等待启动",
        TimerState.RUNNING: "运行中",
        TimerState.PAUSED: "已暂停",
        TimerState.FINISHED: "已结束",
    }
    print("\n\n倒计时器已停止。")
    print(f"  退出时状态: {state_names.get(state, '未知')}")
    if state in (TimerState.RUNNING, TimerState.PAUSED):
        mins = int(remaining) // 60
        secs = int(remaining) % 60
        print(f"  剩余时间: {mins:02d}:{secs:02d}")


# =============================================================================
# 主函数
# =============================================================================

def main() -> None:
    """主函数: 运行倒计时器.

    状态机流程:
        IDLE  --[左键]-->  RUNNING  --[左键]-->  PAUSED
         ^                  |  ^                    |
         |                  |  +----[左键]----------+
         |                  v
         |              FINISHED
         |                  |
         +----[右键]--------+
         +----[右键]--------+

    计时原理:
        使用 time.perf_counter() 作为高精度时钟源。
        在 RUNNING 状态下，remaining 通过以下公式实时计算:
            remaining = remaining_at_run_start - (now - run_start)
        其中 run_start 是倒计时开始 (或暂停后恢复) 时的 perf_counter 值。
    """
    global _left_pressed, _right_pressed

    # ---- 打印欢迎信息 ----
    print("=" * 55)
    print("  SAKS SDK 示例 19: 倒计时器")
    print("=" * 55)
    print()
    print("  操作说明:")
    print("    拨码开关 S1, S2: 设置倒计时时长")
    print("      OFF OFF -> 30 秒")
    print("      ON  OFF -> 60 秒")
    print("      OFF ON  -> 90 秒")
    print("      ON  ON  -> 120 秒")
    print("    左键 (TACT_LEFT):  启动 / 暂停 / 继续")
    print("    右键 (TACT_RIGHT): 重置 (暂停或结束时)")
    print("    按 Ctrl+C 退出程序")
    print()

    # ---- 使用 context manager 初始化 SAKS 扩展板 ----
    with SAKSHAT() as saks:
        # 注册 GPIO 事件回调
        saks.tact_event_handler = on_tact_event

        # 确保所有外设初始状态为关闭
        saks.ledrow.off()
        saks.digital_display.off()
        saks.buzzer.off()

        # ---- 读取初始拨码开关设置 ----
        total_duration, dip_desc = read_duration(saks)
        print(f"  当前拨码开关: {dip_desc}")
        print()

        # ---- 状态变量初始化 ----
        state: TimerState = TimerState.IDLE
        total_set: float = float(total_duration)       # 本次倒计时总时长
        remaining: float = float(total_duration)        # 当前剩余秒数
        run_start: float = 0.0                          # 倒计时开始时刻 (perf_counter)
        remaining_at_run_start: float = 0.0             # 倒计时开始时的剩余秒数
        last_colon_toggle: float = 0.0                  # 上次冒号闪烁切换时刻
        show_colon: bool = True                         # 当前是否显示冒号

        # 初始显示: 全量时间，冒号亮，LED 全亮
        show_countdown(saks, remaining, show_colon=True)
        update_led_progress(saks, remaining, total_set)

        print("  倒计时器就绪，按下左键启动...")
        print(f"  初始时长: {format_time_display(remaining, True)}")
        print()

        try:
            # =========================================================
            # 主循环
            # =========================================================
            while True:
                now = time.perf_counter()

                # ---- 读取拨码开关 (仅在 IDLE 状态生效) ----
                if state == TimerState.IDLE:
                    new_duration, _new_desc = read_duration(saks)
                    if new_duration != total_duration:
                        total_duration = new_duration
                        total_set = float(new_duration)
                        remaining = float(new_duration)
                        show_colon = True
                        show_countdown(saks, remaining, show_colon=True)
                        update_led_progress(saks, remaining, total_set)
                        print(f"  时长已更改: {new_duration} 秒")

                # ---- 处理按键事件 ----
                left_pressed = consume_left_press()
                right_pressed = consume_right_press()

                # ---- 状态机逻辑 ----
                if state == TimerState.IDLE:
                    if left_pressed:
                        # 启动倒计时: 记录开始时刻和初始剩余秒数
                        state = TimerState.RUNNING
                        run_start = now
                        remaining_at_run_start = total_set
                        last_colon_toggle = now
                        show_colon = True
                        print(f"  倒计时开始! 时长: {int(total_set)} 秒")
                        clear_all_presses()

                elif state == TimerState.RUNNING:
                    if left_pressed:
                        # 暂停: 先计算当前剩余时间，再切换状态
                        elapsed = now - run_start
                        remaining = max(0.0, remaining_at_run_start - elapsed)
                        state = TimerState.PAUSED
                        print(f"  倒计时暂停。剩余: {format_time_display(remaining, True)}")
                        clear_all_presses()

                elif state == TimerState.PAUSED:
                    if left_pressed:
                        # 继续: 重置 run_start 和 remaining_at_run_start
                        state = TimerState.RUNNING
                        run_start = now
                        remaining_at_run_start = remaining
                        last_colon_toggle = now
                        show_colon = True
                        print(f"  倒计时继续。剩余: {format_time_display(remaining, True)}")
                        clear_all_presses()
                    elif right_pressed:
                        # 重置
                        remaining = total_set
                        state = TimerState.IDLE
                        show_colon = True
                        show_countdown(saks, remaining, show_colon=True)
                        update_led_progress(saks, remaining, total_set)
                        print(f"  倒计时已重置。时长: {int(total_set)} 秒")
                        clear_all_presses()

                elif state == TimerState.FINISHED:
                    if right_pressed:
                        # 重置
                        remaining = total_set
                        state = TimerState.IDLE
                        show_colon = True
                        show_countdown(saks, remaining, show_colon=True)
                        update_led_progress(saks, remaining, total_set)
                        print(f"  倒计时已重置。时长: {int(total_set)} 秒")
                        clear_all_presses()

                # ---- RUNNING 状态: 使用 perf_counter 计算剩余时间 ----
                if state == TimerState.RUNNING:
                    elapsed = now - run_start
                    remaining = remaining_at_run_start - elapsed

                # ---- 冒号闪烁逻辑 (RUNNING 状态) ----
                if state == TimerState.RUNNING:
                    if now - last_colon_toggle >= COLON_BLINK_INTERVAL:
                        show_colon = not show_colon
                        last_colon_toggle = now

                # ---- 更新数码管和 LED 显示 ----
                if state == TimerState.RUNNING:
                    show_countdown(saks, remaining, show_colon)
                    update_led_progress(saks, remaining, total_set)
                elif state == TimerState.PAUSED:
                    # 暂停时显示稳定，冒号始终亮，LED 保持当前位置
                    show_countdown(saks, remaining, show_colon=True)
                    update_led_progress(saks, remaining, total_set)

                # ---- 检查是否倒计时结束 ----
                if state == TimerState.RUNNING and remaining <= 0:
                    state = TimerState.FINISHED
                    remaining = 0.0
                    print("\n  >>> 倒计时结束! <<<\n")
                    # 显示最终状态
                    show_countdown(saks, 0.0, show_colon=True)
                    update_led_progress(saks, 0.0, total_set)
                    # 播放结束报警动画 (阻塞)
                    play_finished_alarm(saks)
                    # 清除动画期间可能积累的按键事件
                    clear_all_presses()

                # ---- 主循环休眠 ----
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            handle_keyboard_interrupt(state, remaining)
        finally:
            # ---- 清理: 关闭所有外设 ----
            # with 语句的 __exit__ 会自动调用 saks.cleanup()，
            # 这里额外确保外设显示关闭
            try:
                saks.digital_display.off()
                saks.ledrow.off()
                saks.buzzer.off()
            except Exception:
                pass
            print("资源已清理。")
            print("=" * 55)


# =============================================================================
# 程序入口
# =============================================================================

if __name__ == "__main__":
    # 注册 SIGINT 信号处理器，确保 Ctrl+C 时能干净退出
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()