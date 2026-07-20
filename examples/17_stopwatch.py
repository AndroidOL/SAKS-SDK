#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 17: 秒表计时器.

在 4 位数码管上实现一个高精度秒表，支持开始/停止/重置操作，
LED 进度条指示当前秒数，蜂鸣器提供操作反馈。

操作说明:
    - 左键 (TACT_LEFT):  开始/停止秒表
    - 右键 (TACT_RIGHT): 重置 (仅在停止状态下有效)

显示格式:
    - 运行中: "MM.SS" (小数点在第二位，作为冒号分隔符)
      例: "01.23" 表示 1 分 23 秒
    - 停止后: "MM.SS" (末位显示十分之一秒精度)
      例: "01.24" 表示 1 分 23.4 秒 (末位为十分位)

LED 进度:
    - 0-60 秒对应 8 个 LED 依次亮起

蜂鸣器反馈:
    - 开始时: 短哔一声
    - 停止时: 短哔两声

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/17_stopwatch.py
"""

import time
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# =============================================================================
# 配置常量
# =============================================================================
REFRESH_INTERVAL: float = 0.1          # 显示刷新间隔 (秒)，约 10Hz
FLASH_COUNT: int = 3                   # 停止后闪烁次数
FLASH_ON_DURATION: float = 0.3         # 闪烁时亮起持续 (秒)
FLASH_OFF_DURATION: float = 0.2        # 闪烁时熄灭持续 (秒)
LED_COUNT: int = 8                     # LED 总数量
MAX_SECONDS_FOR_LEDS: float = 60.0     # LED 全亮对应的秒数
BEEP_SHORT: float = 0.08               # 短哔时长 (秒)
BEEP_PAUSE: float = 0.08               # 双哔之间的间隔 (秒)

# =============================================================================
# 秒表状态常量
# =============================================================================
STATE_STOPPED: int = 0   # 已停止 (初始状态)
STATE_RUNNING: int = 1   # 计时中

# =============================================================================
# 全局状态变量
# 用于在 GPIO 中断回调函数和主循环之间传递信息
# =============================================================================
left_pressed: bool = False     # 左键是否被按下
right_pressed: bool = False    # 右键是否被按下


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
    global left_pressed, right_pressed
    if status:  # 仅处理按下事件
        if pin == SAKSPins.TACT_LEFT:
            left_pressed = True
        elif pin == SAKSPins.TACT_RIGHT:
            right_pressed = True


# =============================================================================
# 显示辅助函数
# =============================================================================

def format_time_display(total_seconds: float, show_tenths: bool = False) -> str:
    """将总秒数格式化为 4 位显示字符串.

    格式为 "MM.SS"，小数点在第二位作为冒号分隔符。

    Args:
        total_seconds: 总秒数 (浮点数).
        show_tenths: 是否在末位显示十分之一秒精度.

    Returns:
        4 位显示字符串，如 "01.23" 或 "01.24".

    Example:
        >>> format_time_display(83.0, False)
        '01.23'
        >>> format_time_display(83.4, True)
        '01.24'
    """
    # 限制最大显示为 99 分 59.9 秒 (约 99 分钟)
    clamped = max(0.0, min(total_seconds, 99.0 * 60.0 + 59.9))

    minutes = int(clamped / 60.0)
    seconds = clamped - minutes * 60.0

    if show_tenths:
        # 停止时显示十分位精度: MM.SS 格式，末位为十分位
        ss_tens = int(seconds) // 10
        tenths = int(seconds * 10.0) % 10
        return f"{minutes:02d}.{ss_tens}{tenths}"
    else:
        # 运行中显示整数秒: MM.SS 格式
        ss = int(seconds)
        return f"{minutes:02d}.{ss:02d}"


def update_led_progress(saks: SAKSHAT, total_seconds: float) -> None:
    """根据当前秒数更新 LED 进度条.

    0-60 秒对应 0-8 个 LED 依次亮起。
    超过 60 秒后所有 LED 保持全亮。

    Args:
        saks: SAKSHAT 主控制器实例.
        total_seconds: 总秒数.
    """
    seconds_in_cycle = total_seconds % 60.0
    # 将 0-60 秒映射到 0-8 个 LED
    leds_on = int(seconds_in_cycle / MAX_SECONDS_FOR_LEDS * LED_COUNT)
    leds_on = max(0, min(leds_on, LED_COUNT))

    for i in range(LED_COUNT):
        if i < leds_on:
            saks.ledrow.on_for_index(i)
        else:
            saks.ledrow.off_for_index(i)


def double_beep(saks: SAKSHAT) -> None:
    """蜂鸣器发出双短哔声.

    Args:
        saks: SAKSHAT 主控制器实例.
    """
    saks.buzzer.beep(BEEP_SHORT)
    time.sleep(BEEP_PAUSE)
    saks.buzzer.beep(BEEP_SHORT)


def flash_display(saks: SAKSHAT, display_text: str) -> None:
    """闪烁显示最终时间.

    将停止后的最终时间闪烁若干次，以便用户看清结果。

    Args:
        saks: SAKSHAT 主控制器实例.
        display_text: 要闪烁显示的字符串.
    """
    for i in range(FLASH_COUNT):
        saks.digital_display.show(display_text)
        time.sleep(FLASH_ON_DURATION)
        saks.digital_display.off()
        time.sleep(FLASH_OFF_DURATION)
    # 最后恢复显示
    saks.digital_display.show(display_text)


# =============================================================================
# 主函数
# =============================================================================

def main() -> None:
    """主函数：运行秒表计时器.

    秒表流程：
    1. 初始状态为「已停止」，显示 "00.00"
    2. 按下左键 (开始) → 秒表开始计时，显示实时时间
    3. 按下左键 (停止) → 秒表停止，显示最终时间并闪烁
    4. 按下右键 (重置) → 秒表归零 (仅在停止状态下有效)
    5. Ctrl+C 退出
    """
    global left_pressed, right_pressed

    # ---- 打印欢迎信息 ----
    print("=" * 55)
    print("  SAKS SDK 示例 17: 秒表计时器")
    print("=" * 55)
    print()
    print("  操作说明:")
    print("    左键 (TACT_LEFT)  : 开始 / 停止")
    print("    右键 (TACT_RIGHT) : 重置 (仅停止时有效)")
    print()
    print("  显示格式:")
    print("    运行中: MM.SS  (小数点为冒号分隔符)")
    print("    停止后: MM.SS  (末位为十分之一秒)")
    print()
    print("  LED 进度: 0-60 秒对应 8 个 LED 依次亮起")
    print("  蜂鸣器: 开始短哔一声，停止短哔两声")
    print("  按 Ctrl+C 退出")
    print()

    # ---- 初始化 SAKS 扩展板 ----
    with SAKSHAT() as saks:
        # 注册 GPIO 事件回调函数
        saks.tact_event_handler = on_tact_event

        # 初始状态
        state = STATE_STOPPED
        elapsed = 0.0          # 累计计时 (秒)
        start_time = 0.0       # 开始计时的时间戳 (perf_counter)

        # 显示初始时间
        saks.digital_display.show("00.00")
        saks.ledrow.off()

        try:
            while True:
                # ---- 处理按键事件 ----
                if left_pressed:
                    left_pressed = False  # 清除标志

                    if state == STATE_STOPPED:
                        # ---- 开始计时 ----
                        state = STATE_RUNNING
                        start_time = time.perf_counter()
                        saks.buzzer.beep(BEEP_SHORT)  # 开始短哔
                        print(f"  [开始] 计时中...")

                    elif state == STATE_RUNNING:
                        # ---- 停止计时 ----
                        state = STATE_STOPPED
                        # 记录最终时间
                        elapsed = time.perf_counter() - start_time
                        double_beep(saks)  # 停止双哔
                        print(f"  [停止] 计时结束: {elapsed:.1f} 秒")

                        # 闪烁显示最终时间 (含十分位精度)
                        display_text = format_time_display(elapsed, show_tenths=True)
                        flash_display(saks, display_text)

                        # 显示最终时间的 LED 进度
                        update_led_progress(saks, elapsed)

                if right_pressed:
                    right_pressed = False  # 清除标志

                    if state == STATE_STOPPED:
                        # ---- 重置 ----
                        elapsed = 0.0
                        saks.digital_display.show("00.00")
                        saks.ledrow.off()
                        print(f"  [重置] 秒表已归零")

                # ---- 更新运行中的显示 ----
                if state == STATE_RUNNING:
                    current_elapsed = time.perf_counter() - start_time
                    display_text = format_time_display(current_elapsed, show_tenths=False)
                    saks.digital_display.show(display_text)
                    update_led_progress(saks, current_elapsed)

                time.sleep(REFRESH_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n秒表已停止。")

    # with 语句退出时自动调用 saks.cleanup()
    print("资源已清理。")
    print("=" * 55)


# =============================================================================
# 程序入口
# =============================================================================

if __name__ == "__main__":
    # 注册 SIGINT 信号处理器，确保 Ctrl+C 时能干净退出
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()