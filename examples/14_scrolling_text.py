#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 14: 滚动文字显示.

在 4 位数码管上滚动显示文字消息，使用 show_raw() 方法实现逐帧动画。
预定义 CHARS 字典映射常用字符到段码，滚动时 LED 跑马灯同步，
最后显示 "DONE" 并蜂鸣提示。

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/14_scrolling_text.py
"""

import time
import sys
import signal

from sakshat import SAKSHAT


# ==============================================================================
# 7 段数码管段位布局与段码原理
# ==============================================================================
SEGMENT_LAYOUT = r"""
  7 段数码管段位布局 (共阳极，TM1637 驱动)
  =============================================

         a
        ---
      f| g |b
        ---
      e|   |c
        ---
         d    ·dp

  段码位定义 (bit 7..0 = dp.g.f.e.d.c.b.a):
    bit 0: a = 0x01  (上方横段)
    bit 1: b = 0x02  (右上竖段)
    bit 2: c = 0x04  (右下竖段)
    bit 3: d = 0x08  (下方横段)
    bit 4: e = 0x10  (左下竖段)
    bit 5: f = 0x20  (左上竖段)
    bit 6: g = 0x40  (中间横段)
    bit 7: dp = 0x80 (小数点)

  段码 = 所需点亮段掩码的按位 OR 结果
  例如: 数字 0 点亮 a,b,c,d,e,f 六段
        0x3F = 0x01|0x02|0x04|0x08|0x10|0x20 = 0b00111111
"""


# ==============================================================================
# 字符段码映射表 (CHARS)
# ==============================================================================
# 将常用字符 (A-Z, 0-9, 特殊符号) 映射到 7 段数码管段码。
# 由于 7 段数码管只有 7 个发光段，部分字母只能做近似显示。
# 段码 = 所需点亮段掩码的 OR 结果，详见上方段位布局。
CHARS: dict[str, int] = {
    # ---- 数字 0-9 ----
    '0': 0x3F,  # a,b,c,d,e,f
    '1': 0x06,  # b,c
    '2': 0x5B,  # a,b,d,e,g
    '3': 0x4F,  # a,b,c,d,g
    '4': 0x66,  # b,c,f,g
    '5': 0x6D,  # a,c,d,f,g
    '6': 0x7D,  # a,c,d,e,f,g
    '7': 0x07,  # a,b,c
    '8': 0x7F,  # a,b,c,d,e,f,g
    '9': 0x6F,  # a,b,c,d,f,g

    # ---- 字母 A-Z (7 段数码管最佳近似) ----
    # 注: 7 段数码管无法完美显示所有英文字母，
    #     以下为常见的近似表示方案。
    'A': 0x77,  # a,b,c,e,f,g    -- 标准大写 A
    'B': 0x7C,  # c,d,e,f,g      -- 小写 b 风格
    'C': 0x39,  # a,d,e,f        -- 标准大写 C
    'D': 0x5E,  # b,c,d,e,g      -- 小写 d 风格
    'E': 0x79,  # a,d,e,f,g      -- 标准大写 E
    'F': 0x71,  # a,e,f,g        -- 标准大写 F
    'G': 0x3D,  # a,c,d,e,f      -- 大写 G, 缺少 g 段
    'H': 0x76,  # b,c,e,f,g      -- 标准大写 H
    'I': 0x06,  # b,c            -- 同数字 1
    'J': 0x1E,  # b,c,d,e        -- 大写 J, 缺 a,f,g
    'K': 0x76,  # b,c,e,f,g      -- 同 H (7 段无法区分 K 的两条斜线)
    'L': 0x38,  # d,e,f          -- 标准大写 L
    'M': 0x37,  # a,b,c,e,f      -- 近似 M, 缺 d,g (两个峰)
    'N': 0x54,  # c,e,g          -- 小写 n 风格
    'O': 0x5C,  # c,d,e,g        -- 小写 o 风格
    'P': 0x73,  # a,b,e,f,g      -- 标准大写 P
    'Q': 0x67,  # a,b,c,f,g      -- 近似 Q, 带尾巴
    'R': 0x50,  # e,g            -- 小写 r 风格
    'S': 0x6D,  # a,c,d,f,g      -- 同数字 5
    'T': 0x78,  # d,e,f,g        -- 小写 t 风格
    'U': 0x3E,  # b,c,d,e,f      -- 标准大写 U
    'V': 0x3E,  # b,c,d,e,f      -- 同 U (7 段无法区分 V 的斜线)
    'W': 0x7E,  # b,c,d,e,f,g    -- 近似 W (顶部加横)
    'X': 0x76,  # b,c,e,f,g      -- 同 H (7 段无法区分 X 的对角线)
    'Y': 0x6E,  # b,c,d,f,g      -- 小写 y 风格
    'Z': 0x5B,  # a,b,d,e,g      -- 同数字 2

    # ---- 特殊字符 ----
    '-': 0x40,  # g 段 (中间横段, 用作负号/破折号)
    '#': 0x00,  # 空白 (全部熄灭, 占位符)
    ' ': 0x00,  # 空格 (全部熄灭)
    '.': 0x80,  # dp 段 (小数点)
    '_': 0x08,  # d 段 (下划线)
    '=': 0x48,  # d,g 段 (等号, 两条横线)
    '*': 0x63,  # a,b,d,f,g? 近似星号... 使用 0x63 = a,b,f,g 近似
    '!': 0x06,  # b,c (同 1/I, 近似感叹号竖线)
    '?': 0x53,  # a,b,d,e,g (近似问号)
}


# ==============================================================================
# 滚动消息播放列表
# ==============================================================================
# 每条消息将在数码管上从右向左滚动显示
SCROLL_MESSAGES: list[str] = [
    "HELLO",   # 问候语
    "SAKS",    # 扩展板名称
    "2026",    # 年份
    "PI",      # 树莓派 (Raspberry Pi)
    "DONE",    # 结束提示
]


# ==============================================================================
# 核心函数: 在数码管上滚动显示消息
# ==============================================================================
def scroll_message(
    saks: SAKSHAT,
    message: str,
    *,
    step_delay: float = 0.3,
    padding: int = 3,
) -> None:
    """在 4 位数码管上滚动显示一条消息。

    滚动原理:
        将消息两端各填充 padding 个空格，然后用一个 4 字符宽的滑动窗口
        从左到右逐帧移动。每帧通过 show_raw() 将 4 个字符的段码发送到数码管。

        窗口滑动示意 (消息 "HELLO", padding=3):
        ┌─────────────────────────────────────────────────────┐
        │ "   HELLO   "  (填充后字符串)                        │
        │  [   H]  -> 帧 0, 窗口位置 0..3                      │
        │   [  HE]  -> 帧 1, 窗口位置 1..4                      │
        │    [ HEL]  -> 帧 2, 窗口位置 2..5                      │
        │     [HELL]  -> 帧 3, 窗口位置 3..6  (完整显示)        │
        │      [ELLO]  -> 帧 4, 窗口位置 4..7  (完整显示)       │
        │       [LLO ]  -> 帧 5, 窗口位置 5..8                  │
        │        [LO  ]  -> 帧 6, 窗口位置 6..9                  │
        │         [O   ]  -> 帧 7, 窗口位置 7..10               │
        │          [   ]  -> 帧 8, 窗口位置 8..11 (全部空白)     │
        └─────────────────────────────────────────────────────┘

    Args:
        saks: SAKSHAT 实例.
        message: 要滚动的消息字符串.
        step_delay: 每帧之间的间隔时间 (秒).
        padding: 消息两端填充的空格数 (控制滚入/滚出帧数).
    """
    # 构建填充后的消息缓冲区
    pad = " " * padding
    buffer = pad + message + pad

    # 总帧数 = 填充后长度 - 3 (最后的 4 字符窗口位置)
    total_frames = len(buffer) - 3

    print(f"  滚动消息: \"{message}\" ({total_frames} 帧)")

    for frame in range(total_frames):
        # 提取当前窗口的 4 个字符
        window = buffer[frame:frame + 4]

        # 将字符转换为段码
        codes = [CHARS.get(c.upper(), 0x00) for c in window]

        # 使用 show_raw() 一次性更新全部 4 位数码管
        saks.digital_display.show_raw(codes)

        # LED 跑马灯同步: 当前帧对应的 LED 位置
        # LED 从左到右移动，到达最右端后回到最左端
        led_pos = frame % 8
        saks.ledrow.off()
        saks.ledrow.on_for_index(led_pos)

        # 帧间隔
        time.sleep(step_delay)


# ==============================================================================
# 字符表打印函数
# ==============================================================================
def print_chars_table() -> None:
    """打印 CHARS 字典中所有字符及其段码的对照表."""
    print("\n" + "=" * 65)
    print("  字符段码映射表 (CHARS)")
    print("=" * 65)
    print(f"  {'字符':<6} {'段码':<10} {'二进制':<16} {'点亮段':<15}")
    print("  " + "-" * 55)

    # 按类别分组打印
    categories = [
        ("数字 0-9", [str(d) for d in range(10)]),
        ("字母 A-Z", [chr(ord('A') + i) for i in range(26)]),
        ("特殊字符", ['-', '#', ' ', '.', '_', '=', '!', '?']),
    ]

    for cat_name, chars in categories:
        print(f"\n  --- {cat_name} ---")
        for c in chars:
            code = CHARS.get(c, 0x00)
            bin_str = f"0b{code:08b}"
            # 解析点亮的段名
            seg_names = []
            segment_map = {
                "a": 0x01, "b": 0x02, "c": 0x04, "d": 0x08,
                "e": 0x10, "f": 0x20, "g": 0x40, "dp": 0x80,
            }
            for seg, mask in segment_map.items():
                if code & mask:
                    seg_names.append(seg)
            segs_str = "".join(seg_names) if seg_names else "(无)"
            display_c = c if c != ' ' else '(空格)'
            print(f"  '{display_c}'{' ' * (4 - len(display_c))} 0x{code:02X}      {bin_str:<16} {segs_str:<15}")


# ==============================================================================
# 段码转段名工具函数
# ==============================================================================
def segment_to_bits(code: int) -> str:
    """将段码解析为人类可读的段位描述 (独立工具函数).

    Args:
        code: 段码 (0x00-0xFF).

    Returns:
        段位描述字符串，如 "abcdefg" 表示全部 7 段亮。
    """
    segment_map = {
        "a": 0x01, "b": 0x02, "c": 0x04, "d": 0x08,
        "e": 0x10, "f": 0x20, "g": 0x40, "dp": 0x80,
    }
    result = ""
    for seg_name, mask in segment_map.items():
        if code & mask:
            result += seg_name
    return result if result else "(无)"


# ==============================================================================
# 主函数
# ==============================================================================
def main() -> None:
    """主函数."""
    print("=" * 65)
    print("  SAKS SDK 示例 14: 滚动文字显示")
    print("=" * 65)

    # ---- 第一部分: 知识讲解 (无需硬件) ----
    print(SEGMENT_LAYOUT)
    print_chars_table()

    print("\n" + "=" * 65)
    print("  滚动显示原理说明")
    print("=" * 65)
    print("""
  1. 消息两端填充空格，构建待滚动缓冲区
  2. 使用 4 字符宽的滑动窗口逐帧截取
  3. 每帧将 4 个字符通过 CHARS 字典转换为段码
  4. 调用 show_raw([code0, code1, code2, code3]) 更新数码管
  5. 同步控制 LED 跑马灯位置 (frame % 8)
  6. 帧间延时 0.3 秒，产生连续滚动视觉效果
""")

    # ---- 第二部分: 硬件演示 (需要树莓派 + SAKS 扩展板) ----
    print("=" * 65)
    print("  以下演示需要硬件支持 (树莓派 + SAKS 扩展板)")
    print("=" * 65)

    # 使用 with 语句自动管理资源
    with SAKSHAT() as saks:
        print("\n  初始化完成!")
        print("  按 Ctrl+C 可随时退出\n")

        try:
            # 确保设备初始状态
            saks.ledrow.off()
            saks.digital_display.off()
            saks.buzzer.off()

            time.sleep(0.5)

            # 循环播放所有消息
            for idx, msg in enumerate(SCROLL_MESSAGES):
                print(f"\n  [{idx + 1}/{len(SCROLL_MESSAGES)}] ", end="")
                scroll_message(saks, msg, step_delay=0.3, padding=3)

                # 消息之间短暂停顿
                time.sleep(0.3)

            # 最后显示 "DONE" 并蜂鸣提示
            print("\n  >> 显示完成! 蜂鸣提示...")
            saks.ledrow.off()

            # 显示 "DONE" 在数码管上
            # D=0x5E, O=0x5C, N=0x54, E=0x79
            saks.digital_display.show_raw([0x5E, 0x5C, 0x54, 0x79])
            time.sleep(0.5)

            # 蜂鸣提示: 三声短促蜂鸣
            for _ in range(3):
                saks.buzzer.beep(0.1)
                time.sleep(0.15)

            # 关闭数码管
            saks.digital_display.off()

            print("  完成!")

        except KeyboardInterrupt:
            print("\n\n  演示被中断。")

    print("\n  资源已自动清理。")
    print("=" * 65)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()