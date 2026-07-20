#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 16: 反应速度测试游戏.

反应速度测试游戏：8 个 LED 中随机亮起一个，用户需要尽快按下对应的轻触开关。
左键对应 LED 0-3，右键对应 LED 4-7。数码管显示反应时间。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/16_reaction_game.py
"""

import time
import random
import sys
import signal

from sakshat import SAKSHAT, SAKSPins

# =============================================================================
# 游戏配置常量
# =============================================================================
TOTAL_ROUNDS: int = 5               # 每局游戏的总轮数
TIMEOUT_SECONDS: float = 3.0        # 单轮超时时间 (秒)
LED_COUNT: int = 8                  # LED 总数量
POLL_INTERVAL: float = 0.001        # 按键轮询间隔 (秒)，1ms 保证计时精度
ROUND_PAUSE: float = 0.5            # 轮次开始前的停顿时间 (秒)
RESULT_DISPLAY_DURATION: float = 1.5  # 每轮结果显示的持续时间 (秒)

# =============================================================================
# 全局状态变量
# 用于在 GPIO 中断回调函数和主游戏循环之间传递信息
# =============================================================================
pressed_button: str | None = None   # 当前按下的按键: 'left', 'right', 或 None
press_time: float = 0.0             # 按键按下时 perf_counter 时间戳
reset_requested: bool = False       # 是否请求重置游戏 (由拨码开关触发)


# =============================================================================
# GPIO 事件回调函数
# =============================================================================

def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关事件回调函数.

    当用户按下或释放 SAKS 扩展板上的轻触开关时，由 Tact 模块通过
    GPIO 中断自动调用此函数。仅处理「按下」事件 (status == True)，
    并记录是左侧还是右侧按键被按下。

    Args:
        pin: 触发事件的 GPIO 引脚编号 (BCM 编号).
        status: 当前状态，True 表示按下，False 表示释放.
    """
    global pressed_button, press_time
    if status:  # 仅处理按下事件，忽略释放事件
        press_time = time.perf_counter()
        if pin == SAKSPins.TACT_LEFT:
            pressed_button = 'left'
        elif pin == SAKSPins.TACT_RIGHT:
            pressed_button = 'right'


def on_dip_switch_changed(status: list[bool]) -> None:
    """拨码开关状态变更回调函数.

    当用户拨动 SAKS 扩展板上的 2 位拨码开关时，由 DipSwitch2Bit 模块
    通过 GPIO 中断自动调用此函数。任意一位开关状态变化均触发游戏重置。

    Args:
        status: 两位拨码开关的当前状态列表 [bit1, bit2]，
                True 表示 ON，False 表示 OFF.
    """
    global reset_requested
    reset_requested = True


# =============================================================================
# 数码管显示辅助函数
# =============================================================================

def show_reaction_time(saks: SAKSHAT, ms: int) -> None:
    """在 4 位数码管上显示反应时间 (毫秒).

    显示格式为右对齐的 4 位数字，如 " 123" 表示 123 毫秒。
    最高显示 999ms，超过则显示 "999"。

    Args:
        saks: SAKSHAT 主控制器实例.
        ms: 反应时间，单位毫秒 (0-999).
    """
    clamped = max(0, min(ms, 999))
    # 使用 f"{value:4d}" 产生右对齐的 4 字符字符串，如 " 123"
    saks.digital_display.show(f"{clamped:4d}")


def show_fail(saks: SAKSHAT) -> None:
    """在数码管上显示 "FAIL" 字样，表示本轮失败.

    使用 show_char 方法逐位显示字符。
    由于 7 段数码管限制，字母 'I' 使用段码 0x06 (b, c 段点亮)，
    视觉效果与数字 '1' 相同，是数码管显示 'I' 的常规做法。

    Args:
        saks: SAKSHAT 主控制器实例.
    """
    saks.digital_display.show_char(0, 'F')
    saks.digital_display.show_char(1, 'A')
    # 'I' = b, c 段点亮 (0x02 | 0x04 = 0x06)
    saks.digital_display.show_segment(2, 0x06)
    saks.digital_display.show_char(3, 'L')


def show_timeout(saks: SAKSHAT) -> None:
    """在数码管上显示超时标记 "----".

    Args:
        saks: SAKSHAT 主控制器实例.
    """
    saks.digital_display.show("----")


def show_average(saks: SAKSHAT, avg_ms: int) -> None:
    """在数码管上显示平均反应时间.

    显示格式为 'A' + 3 位数字，例如平均 215ms 显示为 "A215"。
    第一位显示字母 'A' (表示 Average)，后三位显示毫秒数。

    Args:
        saks: SAKSHAT 主控制器实例.
        avg_ms: 平均反应时间，单位毫秒 (0-999).
    """
    clamped = max(0, min(avg_ms, 999))
    # 第一位显示 'A'
    saks.digital_display.show_char(0, 'A')
    # 后三位显示数字
    hundreds = clamped // 100
    tens = (clamped // 10) % 10
    ones = clamped % 10
    saks.digital_display.show_char(1, str(hundreds))
    saks.digital_display.show_char(2, str(tens))
    saks.digital_display.show_char(3, str(ones))


# =============================================================================
# LED 控制辅助函数
# =============================================================================

def flash_all_leds(
    saks: SAKSHAT,
    times: int,
    on_duration: float = 0.15,
    off_duration: float = 0.15,
) -> None:
    """让全部 8 个 LED 同步闪烁指定次数.

    用于错误反馈：全部 LED 同时亮起再熄灭，重复指定次数。

    Args:
        saks: SAKSHAT 主控制器实例.
        times: 闪烁次数，必须为正整数.
        on_duration: 每次亮起持续的时间 (秒).
        off_duration: 两次亮起之间的间隔时间 (秒).
    """
    for _ in range(times):
        saks.ledrow.on()                  # 全部 LED 亮起
        time.sleep(on_duration)
        saks.ledrow.off()                 # 全部 LED 熄灭
        time.sleep(off_duration)


# =============================================================================
# 核心游戏逻辑
# =============================================================================

def wait_for_press_or_timeout(timeout: float) -> tuple[str | None, float]:
    """等待用户按下轻触开关，或超时.

    在循环中不断轮询全局变量 pressed_button，直到检测到按键按下
    或等待时间超过 timeout 限制。

    使用 time.perf_counter() 实现高精度计时 (微秒级)，
    轮询间隔为 POLL_INTERVAL (1ms)，确保毫秒级计时精度。

    Args:
        timeout: 超时时间 (秒)，超过此时间仍未按下则返回超时.

    Returns:
        (button, elapsed_time) 元组:
            - button: 'left' 或 'right' 表示按下的按键，None 表示超时.
            - elapsed_time: 从调用开始到按键按下 (或超时) 的实际耗时 (秒).
    """
    global pressed_button
    pressed_button = None  # 清除上一次按键记录
    start = time.perf_counter()

    while pressed_button is None:
        elapsed = time.perf_counter() - start
        if elapsed >= timeout:
            # 超时：返回 None 和实际耗时
            return (None, elapsed)
        time.sleep(POLL_INTERVAL)

    # 按键被按下：计算实际反应时间
    elapsed = press_time - start
    return (pressed_button, elapsed)


def play_round(saks: SAKSHAT, round_num: int) -> tuple[bool, float]:
    """执行一轮反应速度测试.

    完整的一轮测试流程：
    1. 随机选择一个 LED (0-7) 作为目标
    2. 短暂停顿后亮起目标 LED，同时开始计时
    3. 等待用户按下轻触开关 (或超时)
    4. 判断按键是否正确，给出视觉和听觉反馈

    按键映射规则：
    - 左键 (SAKSPins.TACT_LEFT)  -> 对应 LED 0-3
    - 右键 (SAKSPins.TACT_RIGHT) -> 对应 LED 4-7

    Args:
        saks: SAKSHAT 主控制器实例.
        round_num: 当前轮次编号 (1-based)，用于日志输出.

    Returns:
        (success, reaction_time_ms) 元组:
            - success: True 表示用户正确按下对应按键.
            - reaction_time_ms: 反应时间 (毫秒)，失败时返回 0.0.
    """
    # ---- 第 1 步：随机选择目标 LED ----
    target_led = random.randint(0, LED_COUNT - 1)

    # ---- 第 2 步：回合开始前的准备 ----
    saks.ledrow.off()  # 确保所有 LED 熄灭
    time.sleep(ROUND_PAUSE)

    # ---- 第 3 步：亮起目标 LED，开始计时 ----
    saks.ledrow.on_for_index(target_led)

    # ---- 第 4 步：等待用户响应 ----
    button, elapsed = wait_for_press_or_timeout(TIMEOUT_SECONDS)

    # ---- 第 5 步：关闭 LED ----
    saks.ledrow.off()

    # ---- 第 6 步：判断结果并给出反馈 ----
    if button is None:
        # 超时：数码管显示 "----"，连续蜂鸣
        show_timeout(saks)
        saks.buzzer.beep_pattern(0.1, 0.1, 5)  # 连续短哔 5 次
        return (False, 0.0)

    # 判断按键与目标 LED 是否匹配
    if button == 'left':
        is_correct = (0 <= target_led <= 3)
    else:  # button == 'right'
        is_correct = (4 <= target_led <= 7)

    reaction_ms = elapsed * 1000.0  # 秒转毫秒

    if is_correct:
        # 正确：数码管显示反应时间，短哔一声
        show_reaction_time(saks, int(reaction_ms))
        saks.buzzer.beep(0.05)  # 短哔 (50ms)
        return (True, reaction_ms)
    else:
        # 错误：LED 全闪 3 次，数码管显示 "FAIL"，长哔
        show_fail(saks)
        flash_all_leds(saks, 3)
        saks.buzzer.beep(0.5)  # 长哔 (500ms)
        return (False, 0.0)


# =============================================================================
# 游戏重置
# =============================================================================

def reset_game(saks: SAKSHAT) -> None:
    """重置游戏状态.

    关闭所有 LED 和数码管，清除全局按键状态和重置标志。
    拨码开关触发重置时调用此函数。

    Args:
        saks: SAKSHAT 主控制器实例.
    """
    global reset_requested, pressed_button
    saks.ledrow.off()
    saks.digital_display.off()
    reset_requested = False
    pressed_button = None


# =============================================================================
# 主函数
# =============================================================================

def main() -> None:
    """主函数：运行反应速度测试游戏.

    游戏流程：
    1. 显示欢迎信息和规则说明
    2. 初始化 SAKS 扩展板，注册事件回调
    3. 等待用户按下任意轻触开关开始游戏
    4. 执行 TOTAL_ROUNDS 轮反应测试
    5. 计算并显示平均反应时间
    6. 循环回到第 3 步，等待下一局
    7. 拨码开关任意位拨动即可重置游戏
    8. Ctrl+C 退出
    """
    global reset_requested, pressed_button

    # ---- 打印欢迎信息和游戏规则 ----
    print("=" * 55)
    print("  SAKS SDK 示例 16: 反应速度测试游戏")
    print("=" * 55)
    print()
    print("  游戏规则:")
    print("    - 8 个 LED 中随机亮起一个")
    print("    - 左键 (TACT_LEFT)  对应 LED 0-3")
    print("    - 右键 (TACT_RIGHT) 对应 LED 4-7")
    print("    - 尽快按下对应按键，数码管显示反应时间 (ms)")
    print("    - 按错：LED 全闪 3 次，数码管显示 FAIL")
    print(f"    - 超时 ({TIMEOUT_SECONDS:.0f} 秒)：数码管显示 ----")
    print(f"    - 共 {TOTAL_ROUNDS} 轮，结束后显示平均反应时间")
    print("    - 拨动拨码开关可随时重置游戏")
    print("    - 按 Ctrl+C 退出")
    print()

    # ---- 初始化 SAKS 扩展板 ----
    saks = SAKSHAT()

    # 注册 GPIO 事件回调函数
    saks.tact_event_handler = on_tact_event
    saks.dip_switch_status_changed_handler = on_dip_switch_changed

    try:
        # ---- 主游戏循环 ----
        while True:
            # 等待用户开始游戏
            print("按下任意轻触开关开始游戏...")
            saks.digital_display.show("----")

            # 等待按键按下或拨码开关重置
            pressed_button = None
            while pressed_button is None and not reset_requested:
                time.sleep(POLL_INTERVAL)

            # 检查是否需要重置
            if reset_requested:
                reset_game(saks)
                print("游戏已重置。\n")
                continue

            # ---- 游戏正式开始 ----
            print(f"\n>>> 游戏开始！共 {TOTAL_ROUNDS} 轮 <<<\n")
            saks.buzzer.beep(0.1)  # 开始提示音

            reaction_times: list[float] = []  # 记录成功的反应时间 (ms)

            # ---- 逐轮执行测试 ----
            for round_num in range(1, TOTAL_ROUNDS + 1):
                # 检查是否在轮次间触发了重置
                if reset_requested:
                    break

                print(f"--- 第 {round_num}/{TOTAL_ROUNDS} 轮 ---")

                # 执行一轮测试
                success, reaction_ms = play_round(saks, round_num)

                if success:
                    reaction_times.append(reaction_ms)
                    print(f"    正确！反应时间: {reaction_ms:.0f} ms")
                else:
                    print(f"    失败！")

                # 轮次间停顿，让用户看清结果
                time.sleep(RESULT_DISPLAY_DURATION)
                saks.digital_display.off()

            # 如果游戏中途被重置，跳过结果显示
            if reset_requested:
                reset_game(saks)
                print("游戏已重置。\n")
                continue

            # ---- 游戏结束，显示统计结果 ----
            print(f"\n{'=' * 55}")
            if len(reaction_times) > 0:
                avg_ms = sum(reaction_times) / len(reaction_times)
                print(f"  游戏结束！")
                print(f"  成功次数: {len(reaction_times)}/{TOTAL_ROUNDS}")
                print(
                    f"  各轮反应时间: "
                    f"{', '.join(f'{t:.0f}ms' for t in reaction_times)}"
                )
                print(f"  平均反应时间: {avg_ms:.0f} ms")

                # 在数码管上显示平均反应时间 (格式: A215)
                show_average(saks, int(avg_ms))

                # 结束提示音：3 次短哔
                saks.buzzer.beep_pattern(0.1, 0.1, 3)
            else:
                print(f"  游戏结束！所有 {TOTAL_ROUNDS} 轮均失败。")
                saks.digital_display.show("FAIL")
                time.sleep(2)

            saks.digital_display.off()
            print(f"{'=' * 55}\n")

            # 短暂停顿后回到等待开始状态
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n游戏已停止。")
    finally:
        # ---- 清理资源 ----
        saks.digital_display.off()
        saks.ledrow.off()
        saks.cleanup()
        print("资源已清理。")
        print("=" * 55)


# =============================================================================
# 程序入口
# =============================================================================

if __name__ == "__main__":
    # 注册 SIGINT 信号处理器，确保 Ctrl+C 时能干净退出
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()