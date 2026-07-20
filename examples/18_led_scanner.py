#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 18: LED 扫描特效 - 骑士灯 / 赛隆扫描器.

在 SAKS 扩展板的 8 颗 LED 上实现多种动态扫描特效，通过
拨码开关和轻触开关控制速度和模式切换。

四种扫描模式:
  1. 骑士灯 (Knight Rider) - 单颗 LED 来回弹跳，带拖尾渐隐效果
  2. 波浪 (Wave) - 2 颗相邻 LED 成组移动
  3. 乒乓 (Ping Pong) - LED 弹跳，速度先增后减
  4. 填充排空 (Fill & Drain) - LED 从左到右填充，再从右到左排空

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/18_led_scanner.py
"""

import time
import sys
import signal
import math

from sakshat import SAKSHAT, SAKSPins

# =============================================================================
# 配置常量
# =============================================================================
LED_COUNT: int = 8                     # LED 总数量
FAST_SPEED: float = 0.04               # 快速扫描间隔 (秒)
SLOW_SPEED: float = 0.12               # 慢速扫描间隔 (秒)
PATTERN_COUNT: int = 4                 # 扫描模式总数
AUTO_CYCLE_INTERVAL: float = 8.0       # 自动循环切换模式间隔 (秒)
FADE_SUBSTEPS: int = 8                 # 渐隐效果子帧数 (越多越平滑)
DEBOUNCE_DELAY: float = 0.15           # 按键消抖延迟 (秒)

# 模式名称映射
PATTERN_NAMES: dict[int, str] = {
    0: "P1",   # 骑士灯
    1: "P2",   # 波浪
    2: "P3",   # 乒乓
    3: "P4",   # 填充排空
}

# =============================================================================
# 全局状态变量 (主循环与中断回调之间共享)
# =============================================================================
current_pattern: int = 0               # 当前模式索引 (0-3)
auto_cycle: bool = False               # 是否自动循环切换模式 (拨码开关 S2)
last_button_time: float = 0.0          # 上次按键时间 (用于消抖)
beep_requested: bool = False           # 是否需要在主循环中蜂鸣


# =============================================================================
# GPIO 事件回调函数
# =============================================================================

def on_tact_event(pin: int, status: bool) -> None:
    """轻触开关事件回调函数.

    左键 (TACT_LEFT):  切换到上一个模式
    右键 (TACT_RIGHT): 切换到下一个模式

    包含消抖逻辑: 在 DEBOUNCE_DELAY 秒内忽略重复按键。

    Args:
        pin: 触发事件的 GPIO 引脚编号 (BCM 编号).
        status: True 表示按下，False 表示释放.
    """
    global current_pattern, last_button_time, beep_requested

    if not status:
        return  # 仅响应按下事件

    now = time.monotonic()
    if now - last_button_time < DEBOUNCE_DELAY:
        return  # 消抖: 忽略过快的重复按键

    last_button_time = now

    if pin == SAKSPins.TACT_LEFT:
        current_pattern = (current_pattern - 1) % PATTERN_COUNT
        print(f"  [左键] 切换到模式: {PATTERN_NAMES[current_pattern]}")
    elif pin == SAKSPins.TACT_RIGHT:
        current_pattern = (current_pattern + 1) % PATTERN_COUNT
        print(f"  [右键] 切换到模式: {PATTERN_NAMES[current_pattern]}")
    else:
        return

    beep_requested = True


def on_dip_switch_changed(status: list[bool]) -> None:
    """拨码开关状态变更回调函数.

    S1: 速度控制 (ON = 快速, OFF = 慢速)
    S2: 自动循环切换 (ON = 自动循环, OFF = 手动)

    Args:
        status: 两位拨码开关的当前状态 [S1, S2],
                True 表示 ON，False 表示 OFF.
    """
    global auto_cycle

    s1, s2 = status[0], status[1]
    auto_cycle = s2

    speed_label = "快速" if s1 else "慢速"
    cycle_label = "自动循环" if s2 else "手动切换"
    print(f"  [拨码开关] S1={'ON' if s1 else 'OFF'}({speed_label}), "
          f"S2={'ON' if s2 else 'OFF'}({cycle_label})")


# =============================================================================
# LED 扫描模式实现
# =============================================================================

def pattern_knight_rider(
    saks: SAKSHAT,
    speed: float,
    state: dict,
) -> bool:
    """模式 1: 骑士灯 (Knight Rider) - 带拖尾渐隐效果.

    单颗 LED 在 8 颗 LED 之间来回弹跳，身后留下 2 颗渐隐的拖尾 LED。
    通过子帧 PWM 模拟实现渐隐效果: 每个显示帧拆分为多个子帧，
    拖尾 LED 仅在部分子帧中点亮，形成视觉上的亮度递减。

    Args:
        saks: SAKSHAT 主控制器实例.
        speed: 当前扫描速度 (秒/帧).
        state: 模式状态字典，包含:
            - position: 当前 LED 位置 (0-7)
            - direction: 移动方向 (1=向右, -1=向左)

    Returns:
        True 表示模式完成了一个完整周期 (可用于自动循环计数器).
    """
    pos: int = state.setdefault("position", 0)
    direction: int = state.setdefault("direction", 1)

    completed_cycle = False

    # ---- 子帧 PWM 渐隐 ----
    # 主 LED (pos) 在所有子帧中点亮
    # 拖尾 LED 1 (pos - direction) 在 60% 子帧中点亮
    # 拖尾 LED 2 (pos - 2*direction) 在 30% 子帧中点亮
    for sub in range(FADE_SUBSTEPS):
        row = [False] * LED_COUNT

        # 主 LED: 始终点亮
        if 0 <= pos < LED_COUNT:
            row[pos] = True

        # 拖尾 LED 1: 在部分子帧中点亮
        trail1 = pos - direction
        if 0 <= trail1 < LED_COUNT:
            if sub < int(FADE_SUBSTEPS * 0.6):
                row[trail1] = True

        # 拖尾 LED 2: 在更少子帧中点亮
        trail2 = pos - 2 * direction
        if 0 <= trail2 < LED_COUNT:
            if sub < int(FADE_SUBSTEPS * 0.3):
                row[trail2] = True

        saks.ledrow.set_row(row)
        time.sleep(speed / FADE_SUBSTEPS)

    # ---- 更新位置 ----
    pos += direction

    # 边界反弹
    if pos >= LED_COUNT - 1:
        pos = LED_COUNT - 1
        direction = -1
        completed_cycle = True
    elif pos <= 0:
        pos = 0
        direction = 1
        completed_cycle = True

    state["position"] = pos
    state["direction"] = direction
    return completed_cycle


def pattern_wave(
    saks: SAKSHAT,
    speed: float,
    state: dict,
) -> bool:
    """模式 2: 波浪 (Wave) - 2 颗相邻 LED 成组移动.

    2 颗相邻的 LED 同时点亮，从左向右移动，到达右端后反向。
    例如: [1,1,0,0,0,0,0,0] -> [0,1,1,0,0,0,0,0] -> ...

    Args:
        saks: SAKSHAT 主控制器实例.
        speed: 当前扫描速度 (秒/帧).
        state: 模式状态字典，包含:
            - position: 当前 LED 组的起始位置 (0-6)
            - direction: 移动方向 (1=向右, -1=向左)

    Returns:
        True 表示模式完成了一个完整周期.
    """
    pos: int = state.setdefault("position", 0)
    direction: int = state.setdefault("direction", 1)

    completed_cycle = False

    # 设置 2 颗相邻 LED
    row = [False] * LED_COUNT
    if 0 <= pos < LED_COUNT:
        row[pos] = True
    if 0 <= pos + 1 < LED_COUNT:
        row[pos + 1] = True
    saks.ledrow.set_row(row)
    time.sleep(speed)

    # 更新位置
    pos += direction

    max_pos = LED_COUNT - 2  # 双 LED 组的最大起始位置
    if pos >= max_pos:
        pos = max_pos
        direction = -1
        completed_cycle = True
    elif pos <= 0:
        pos = 0
        direction = 1
        completed_cycle = True

    state["position"] = pos
    state["direction"] = direction
    return completed_cycle


def pattern_ping_pong(
    saks: SAKSHAT,
    speed: float,
    state: dict,
) -> bool:
    """模式 3: 乒乓 (Ping Pong) - LED 弹跳，速度先增后减.

    单颗 LED 从左向右移动，在中间位置速度最快，两端速度最慢，
    模拟乒乓球在球台上弹跳的视觉效果。

    速度曲线使用正弦函数: 在两端 (0 和 7) 最慢，中间 (3-4) 最快。

    Args:
        saks: SAKSHAT 主控制器实例.
        speed: 基础扫描速度 (秒/帧)，作为速度缩放基准.
        state: 模式状态字典，包含:
            - position: 当前 LED 位置 (0-7)
            - direction: 移动方向 (1=向右, -1=向左)

    Returns:
        True 表示模式完成了一个完整周期.
    """
    pos: int = state.setdefault("position", 0)
    direction: int = state.setdefault("direction", 1)

    completed_cycle = False

    # 显示当前 LED
    row = [False] * LED_COUNT
    row[pos] = True
    saks.ledrow.set_row(row)

    # 根据位置计算动态速度: 中间快，两端慢
    # 归一化位置到 [0, pi]，正弦值在中间最大
    normalized = (pos / (LED_COUNT - 1)) * math.pi
    speed_factor = math.sin(normalized)
    # 速度范围: 0.3x (两端) 到 1.0x (中间)
    dynamic_speed = speed * (1.0 - 0.7 * speed_factor)
    time.sleep(dynamic_speed)

    # 更新位置
    pos += direction

    if pos >= LED_COUNT - 1:
        pos = LED_COUNT - 1
        direction = -1
        completed_cycle = True
    elif pos <= 0:
        pos = 0
        direction = 1
        completed_cycle = True

    state["position"] = pos
    state["direction"] = direction
    return completed_cycle


def pattern_fill_drain(
    saks: SAKSHAT,
    speed: float,
    state: dict,
) -> bool:
    """模式 4: 填充排空 (Fill & Drain) - LED 逐颗填充再排空.

    从左到右逐颗点亮 (填充)，全部点亮后从右到左逐颗熄灭 (排空)。
    填充阶段: 每帧增加一颗 LED 点亮
    排空阶段: 每帧减少一颗 LED 点亮

    Args:
        saks: SAKSHAT 主控制器实例.
        speed: 当前扫描速度 (秒/帧).
        state: 模式状态字典，包含:
            - fill_level: 当前亮起的 LED 数量 (0-8)
            - filling: True 表示填充阶段，False 表示排空阶段

    Returns:
        True 表示模式完成了一个完整周期.
    """
    fill_level: int = state.setdefault("fill_level", 0)
    filling: bool = state.setdefault("filling", True)

    completed_cycle = False

    # 根据填充级别设置 LED
    row = [False] * LED_COUNT
    if filling:
        # 填充阶段: 从左到右点亮 fill_level 颗 LED
        for i in range(fill_level):
            row[i] = True
    else:
        # 排空阶段: 从右到左保持 fill_level 颗 LED 亮起
        # fill_level 颗 LED 在右侧亮起
        for i in range(LED_COUNT - fill_level, LED_COUNT):
            row[i] = True

    saks.ledrow.set_row(row)
    time.sleep(speed)

    # 更新填充级别
    if filling:
        fill_level += 1
        if fill_level > LED_COUNT:
            # 全部点亮，切换到排空阶段
            fill_level = LED_COUNT - 1
            filling = False
    else:
        fill_level -= 1
        if fill_level < 0:
            # 全部熄灭，切换回填充阶段
            fill_level = 1
            filling = True
            completed_cycle = True

    state["fill_level"] = fill_level
    state["filling"] = filling
    return completed_cycle


# =============================================================================
# 模式调度器
# =============================================================================

# 模式函数注册表
PATTERN_FUNCTIONS: list = [
    pattern_knight_rider,
    pattern_wave,
    pattern_ping_pong,
    pattern_fill_drain,
]


def get_speed(dip_status: list[bool]) -> tuple[float, str]:
    """根据拨码开关 S1 状态获取扫描速度.

    Args:
        dip_status: 拨码开关状态列表 [S1, S2].

    Returns:
        (speed, label) 元组，speed 为帧间隔秒数.
    """
    if dip_status[0]:  # S1 = ON
        return (FAST_SPEED, "快速")
    else:
        return (SLOW_SPEED, "慢速")


# =============================================================================
# 主函数
# =============================================================================

def main() -> None:
    """主函数: 运行 LED 扫描特效演示.

    演示流程:
    1. 显示欢迎信息和操作说明
    2. 初始化 SAKS 扩展板，注册事件回调
    3. 进入主循环: 根据当前模式执行 LED 扫描特效
    4. 拨码开关 S1 控制速度，S2 控制自动循环
    5. 轻触开关手动切换模式
    6. 数码管显示当前模式编号 (P1-P4)
    7. Ctrl+C 退出
    """
    global current_pattern, auto_cycle, beep_requested

    # ---- 打印欢迎信息和操作说明 ----
    print("=" * 60)
    print("  SAKS SDK 示例 18: LED 扫描特效")
    print("  骑士灯 / 赛隆扫描器 (Knight Rider / Cylon Scanner)")
    print("=" * 60)
    print()
    print("  四种扫描模式:")
    print("    P1 - 骑士灯 (Knight Rider): 单 LED 弹跳 + 拖尾渐隐")
    print("    P2 - 波浪 (Wave): 2 颗 LED 成组移动")
    print("    P3 - 乒乓 (Ping Pong): 弹跳速度先增后减")
    print("    P4 - 填充排空 (Fill & Drain): 逐颗填充再排空")
    print()
    print("  操作说明:")
    print("    拨码开关 S1: 速度控制 (ON=快速, OFF=慢速)")
    print("    拨码开关 S2: 自动循环 (ON=自动切换模式, OFF=手动)")
    print("    左键 (TACT_LEFT):  上一个模式")
    print("    右键 (TACT_RIGHT): 下一个模式")
    print("    数码管: 显示当前模式 (P1-P4) 和速度 (F=快, S=慢)")
    print("    按 Ctrl+C 退出")
    print()

    # ---- 初始化 SAKS 扩展板 ----
    with SAKSHAT() as saks:
        # 注册 GPIO 事件回调函数
        saks.tact_event_handler = on_tact_event
        saks.dip_switch_status_changed_handler = on_dip_switch_changed

        # 读取拨码开关初始状态
        init_status = saks.dip_switch.is_on
        if init_status[0] or init_status[1]:
            on_dip_switch_changed(init_status)

        # 确保设备初始状态
        saks.ledrow.off()
        saks.buzzer.off()

        # 显示初始模式
        saks.digital_display.show(PATTERN_NAMES[current_pattern])
        print(f"\n  初始模式: {PATTERN_NAMES[current_pattern]}")
        print("  按 Ctrl+C 可随时退出\n")

        # 每个模式的状态存储 (独立字典，切换模式时保留)
        pattern_states: list[dict] = [{} for _ in range(PATTERN_COUNT)]

        # 自动循环计时器
        auto_cycle_timer: float = time.monotonic()
        cycle_count: int = 0  # 完整周期计数 (用于自动循环)

        try:
            # ---- 主循环 ----
            while True:
                # 读取拨码开关状态
                dip_status = saks.dip_switch.is_on
                speed, speed_label = get_speed(dip_status)
                auto_cycle = dip_status[1]

                # 更新数码管显示: 模式 + 速度
                # 格式: P1F (P1=模式1, F=快速) 或 P2S (P2=模式2, S=慢速)
                speed_char = "F" if dip_status[0] else "S"
                display_str = f"{PATTERN_NAMES[current_pattern]}{speed_char}"
                saks.digital_display.show(display_str)

                # 蜂鸣提示 (模式切换时)
                if beep_requested:
                    saks.buzzer.beep(0.05)
                    beep_requested = False

                # 执行当前模式的单帧
                pattern_func = PATTERN_FUNCTIONS[current_pattern]
                completed = pattern_func(saks, speed, pattern_states[current_pattern])

                # 自动循环: 每完成一个完整周期或超时后切换模式
                if completed:
                    cycle_count += 1

                if auto_cycle:
                    elapsed = time.monotonic() - auto_cycle_timer
                    if elapsed >= AUTO_CYCLE_INTERVAL:
                        old = current_pattern
                        current_pattern = (current_pattern + 1) % PATTERN_COUNT
                        beep_requested = True
                        auto_cycle_timer = time.monotonic()
                        print(f"  [自动循环] {PATTERN_NAMES[old]} -> "
                              f"{PATTERN_NAMES[current_pattern]}")

        except KeyboardInterrupt:
            print("\n\n  演示已停止。")

        finally:
            # ---- 清理资源 (with 语句退出时也会自动调用) ----
            saks.digital_display.off()
            saks.ledrow.off()
            saks.buzzer.off()
            print("  资源已清理。")
            print("=" * 60)


# =============================================================================
# 程序入口
# =============================================================================

if __name__ == "__main__":
    # 注册 SIGINT 信号处理器，确保 Ctrl+C 时能干净退出
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()