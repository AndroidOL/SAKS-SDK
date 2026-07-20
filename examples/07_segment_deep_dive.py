#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 07: 数码管段码深度解析.

深入探索 7 段数码管的段码原理，包括:
  - 7 段数码管段位布局 ASCII 图
  - 段名到 hex 值的完整映射表
  - 段码位定义 (bit0=a, bit1=b, ..., bit7=dp)
  - 数字 0-9 的段码表 (数字, 段码hex, 点亮段名, 视觉示意)
  - 扩展字符表 (A-F, H, L, P, U 等)
  - show_segment() / show_segments() / show_char() / show_raw() 演示
  - segment_to_bits() / segments_to_code() 工具方法演示
  - 交互式段名查询

硬件要求: 树莓派 + SAKS 扩展板
运行方式: python3 examples/07_segment_deep_dive.py
"""

import time
import sys
import signal

from sakshat import DigitalDisplay, SAKSPins


# ==============================================================================
#  7 段数码管段位布局 ASCII 图
# ==============================================================================
SEGMENT_LAYOUT_ASCII = r"""
  7 段数码管段位布局 (共阳极，TM1637 驱动)
  =============================================

         a
        ---
      f| g |b
        ---
      e|   |c
        ---
         d    ·dp

  段名说明:
    a, b, c, d, e, f, g  -- 7 个发光段 (组成数字/字母)
    dp (dot point)        -- 小数点

  段码位定义 (bit 7..0 = dp.g.f.e.d.c.b.a):
    bit 7: dp (0x80) -- 小数点
    bit 6: g  (0x40) -- 中间横段
    bit 5: f  (0x20) -- 左上竖段
    bit 4: e  (0x10) -- 左下竖段
    bit 3: d  (0x08) -- 下方横段
    bit 2: c  (0x04) -- 右下竖段
    bit 1: b  (0x02) -- 右上竖段
    bit 0: a  (0x01) -- 上方横段

  示例: 数字 0 点亮 a,b,c,d,e,f 六段，段码 = 0x3F
        0x3F = 0b00111111 = 0x01 + 0x02 + 0x04 + 0x08 + 0x10 + 0x20
"""


# ==============================================================================
#  段名到 hex 值的完整映射
# ==============================================================================
def print_segment_map() -> None:
    """打印 SEGMENT_MAP 完整映射表 (段名 -> hex 值)."""
    print("\n" + "=" * 65)
    print("  SEGMENT_MAP 段名 -> hex 值映射表")
    print("=" * 65)
    print(f"  {'段名':<8} {'hex 值':<10} {'二进制':<16} {'说明'}")
    print("  " + "-" * 55)

    segment_map = DigitalDisplay.SEGMENT_MAP
    # 按 bit 位顺序排列: a(0) -> b(1) -> c(2) -> d(3) -> e(4) -> f(5) -> g(6) -> dp(7)
    order = ["a", "b", "c", "d", "e", "f", "g", "dp"]
    for seg in order:
        hex_val = segment_map[seg]
        bin_str = f"0b{hex_val:08b}"
        print(f"  {seg:<8} 0x{hex_val:02X}      {bin_str:<16} bit {hex_val.bit_length() - 1}")

    print("  " + "-" * 55)
    print("  注: 通过 OR 运算组合多个段，如 'def' = 0x10|0x08|0x20 = 0x38")


# ==============================================================================
#  段码位定义表
# ==============================================================================
def print_bit_definition_table() -> None:
    """打印段码位定义表 (bit0=a, bit1=b, ..., bit7=dp)."""
    print("\n" + "=" * 65)
    print("  段码位定义表 (bit 7..0 = dp.g.f.e.d.c.b.a)")
    print("=" * 65)
    print(f"  {'Bit 位':<8} {'掩码':<10} {'段名':<8} {'几何位置'}")
    print("  " + "-" * 50)

    bit_defs = [
        (0, 0x01, "a", "上方横段"),
        (1, 0x02, "b", "右上竖段"),
        (2, 0x04, "c", "右下竖段"),
        (3, 0x08, "d", "下方横段"),
        (4, 0x10, "e", "左下竖段"),
        (5, 0x20, "f", "左上竖段"),
        (6, 0x40, "g", "中间横段"),
        (7, 0x80, "dp", "小数点"),
    ]
    for bit, mask, seg, pos in bit_defs:
        print(f"  bit {bit:<5} 0x{mask:02X}      {seg:<8} {pos}")

    print("  " + "-" * 50)
    print("  段码 = 所有点亮段掩码的 OR 结果")
    print("  例如: 数字 0 = a|b|c|d|e|f = 0x01|0x02|0x04|0x08|0x10|0x20 = 0x3F")


# ==============================================================================
#  数字 0-9 的段码表
# ==============================================================================
def print_digit_segment_table() -> None:
    """打印数字 0-9 的段码表 (数字, 段码hex, 点亮段名, 视觉示意)."""
    print("\n" + "=" * 65)
    print("  数字 0-9 的段码表")
    print("=" * 65)
    print(f"  {'数字':<6} {'段码':<10} {'二进制':<16} {'点亮段':<15} {'视觉示意'}")
    print("  " + "-" * 55)

    # 数字 0-9 的段码 (来自 SDK 内部 _SEGMENT_CODE)
    digit_codes = [
        0x3F,  # 0
        0x06,  # 1
        0x5B,  # 2
        0x4F,  # 3
        0x66,  # 4
        0x6D,  # 5
        0x7D,  # 6
        0x07,  # 7
        0x7F,  # 8
        0x6F,  # 9
    ]

    # 视觉示意 (用 7 段风格表示)
    visual_map = {
        0x3F: " _ \n| |\n|_|",   # 0
        0x06: "   \n  |\n  |",   # 1
        0x5B: " _ \n _|\n|_ ",   # 2
        0x4F: " _ \n _|\n _|",   # 3
        0x66: "   \n|_|\n  |",   # 4
        0x6D: " _ \n|_ \n _|",   # 5
        0x7D: " _ \n|_ \n|_|",   # 6
        0x07: " _ \n  |\n  |",   # 7
        0x7F: " _ \n|_|\n|_|",   # 8
        0x6F: " _ \n|_|\n _|",   # 9
    }

    for digit, code in enumerate(digit_codes):
        bits = DigitalDisplay.segment_to_bits(code)
        bin_str = f"0b{code:08b}"
        visual = visual_map[code].replace("\n", " ")
        print(f"  {digit:<6} 0x{code:02X}      {bin_str:<16} {bits:<15} {visual}")

    print("  " + "-" * 55)


# ==============================================================================
#  扩展字符表
# ==============================================================================
def print_extended_char_table() -> None:
    """打印扩展字符表 (A-F, H, L, P, U 等)."""
    print("\n" + "=" * 65)
    print("  扩展字符表 (字母和特殊符号)")
    print("=" * 65)
    print(f"  {'字符':<6} {'段码':<10} {'二进制':<16} {'点亮段':<15} {'说明'}")
    print("  " + "-" * 55)

    char_map = DigitalDisplay.CHAR_MAP
    # 按字母顺序排列
    char_descriptions = {
        "A": "大写 A, 缺 d 段",
        "B": "小写 b 风格, 缺 a 段",
        "C": "大写 C, 缺 b,g 段",
        "D": "小写 d 风格, 缺 a,f 段",
        "E": "大写 E, 缺 b,c 段",
        "F": "大写 F, 缺 b,c,d 段",
        "H": "大写 H, 缺 a,d 段",
        "L": "大写 L, 缺 a,b,c,g 段",  # 注意: 实际是 d,e,f
        "P": "大写 P, 缺 c,d 段",
        "U": "大写 U, 缺 a,g 段",
        "o": "小写 o, 缺 a,b,f 段",
        "n": "小写 n, 缺 a,b,d,f 段",
        "r": "小写 r, 缺 a,b,c,d,f 段",
        "t": "小写 t, 缺 a,b,c 段",
        "y": "小写 y, 缺 a 段",
    }

    for char in sorted(char_map.keys(), key=lambda c: (c.islower(), c.upper())):
        code = char_map[char]
        bits = DigitalDisplay.segment_to_bits(code)
        bin_str = f"0b{code:08b}"
        desc = char_descriptions.get(char, "")
        print(f"  '{char}'{' ' * (4 - len(char))} 0x{code:02X}      {bin_str:<16} {bits:<15} {desc}")

    # 特殊字符: 空白、负号、小数点
    print(f"  {'#'}{' ' * 4} 0x00      0b00000000      {'(无)'}            空白 (全部熄灭)")
    print(f"  {'-'}{' ' * 4} 0x40      0b01000000      g               负号 (仅 g 段)")
    print(f"  {'.'}{' ' * 4} 0x80      0b10000000      dp              小数点 (仅 dp 段)")
    print("  " + "-" * 55)


# ==============================================================================
#  演示: show_segment() -- 逐位显示自定义段码
# ==============================================================================
def demo_show_segment(display: DigitalDisplay) -> None:
    """演示 show_segment() 方法: 逐位显示自定义段码.

    show_segment() 接受十六进制段码，直接控制单个数码管的每段亮灭。
    段码的每个 bit 对应一段: bit7=dp, bit6=g, bit5=f, bit4=e, bit3=d, bit2=c, bit1=b, bit0=a.
    """
    print("\n" + "=" * 65)
    print("  演示: show_segment(digit, code) -- 逐位自定义段码")
    print("=" * 65)

    # 演示 1: 显示字母 "L A S K" 在 4 位数码管上
    print("\n  [1] 显示 'L A S K' 在数码管上 (S 和 K 用自定义段码)")
    display.show_segment(0, 0x38)   # 第 0 位: L (d,e,f 段亮)
    display.show_segment(1, 0x77)   # 第 1 位: A (a,b,c,e,f,g 段亮)
    display.show_segment(2, 0x6D)   # 第 2 位: 5 (a,c,d,f,g 段亮, 近似 S)
    display.show_segment(3, 0x00)   # 第 3 位: 全灭
    print("  第 0 位: 0x38 (L)  -- d,e,f 段亮")
    print("  第 1 位: 0x77 (A)  -- a,b,c,e,f,g 段亮")
    print("  第 2 位: 0x6D (5)  -- a,c,d,f,g 段亮")
    print("  第 3 位: 0x00      -- 全部熄灭")
    time.sleep(2)

    # 演示 2: 逐位滚动显示段码 0x00 到 0xFF
    print("\n  [2] 逐位遍历段码 0x00-0xFF 中最有代表性的值")
    # 选择一些有代表性的段码
    interesting_codes = [
        0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80,  # 单个段
        0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F,  # 数字 0-9
        0x77, 0x7C, 0x39, 0x5E, 0x79, 0x71, 0x76, 0x38, 0x73, 0x3E,  # 字母
        0xFF,  # 全亮
    ]
    for code in interesting_codes:
        bits = DigitalDisplay.segment_to_bits(code)
        display.show_segment(0, code)
        print(f"  show_segment(0, 0x{code:02X}) -> 点亮段: {bits if bits else '(无)'}")
        time.sleep(0.08)

    display.off()
    print("  演示完成!")


# ==============================================================================
#  演示: show_segments() -- 用段名字符串控制
# ==============================================================================
def demo_show_segments(display: DigitalDisplay) -> None:
    """演示 show_segments() 方法: 用段名字符串控制.

    show_segments() 通过段名字符串控制单个数码管的亮灭。
    段名由 'a'~'g' 和 'dp' 组成，如 "def" 表示点亮 d、e、f 三段。
    """
    print("\n" + "=" * 65)
    print("  演示: show_segments(digit, segments) -- 段名字符串控制")
    print("=" * 65)

    # 演示 1: 在 4 位上分别显示不同字母 (用段名方式)
    print("\n  [1] 用段名字符串显示 'H E L P'")
    display.show_segments(0, "bcefg")   # H: b,c,e,f,g 段亮
    display.show_segments(1, "adefg")   # E: a,d,e,f,g 段亮
    display.show_segments(2, "def")     # L: d,e,f 段亮
    display.show_segments(3, "abefg")   # P: a,b,e,f,g 段亮
    print("  第 0 位: 'bcefg'  -> H")
    print("  第 1 位: 'adefg'  -> E")
    print("  第 2 位: 'def'    -> L")
    print("  第 3 位: 'abefg'  -> P")
    time.sleep(2)

    # 演示 2: 小数点的各种组合
    print("\n  [2] 小数点段名 'dp' 演示")
    display.show_segments(0, "abcdefg")    # 数字 8 (无小数点)
    display.show_segments(1, "abcdefgdp")  # 数字 8 + 小数点
    display.show_segments(2, "dp")         # 仅小数点
    display.show_segments(3, "")           # 全部熄灭
    print("  第 0 位: 'abcdefg'    -> 8 (无小数点)")
    print("  第 1 位: 'abcdefgdp'  -> 8. (带小数点)")
    print("  第 2 位: 'dp'         -> 仅小数点")
    print("  第 3 位: ''           -> 全部熄灭")
    time.sleep(2)

    # 演示 3: 段名顺序无关 (OR 运算)
    print("\n  [3] 段名顺序无关 -- 'def' 和 'fed' 效果相同")
    display.show_segments(0, "def")
    time.sleep(1)
    display.show_segments(0, "fed")
    time.sleep(1)
    print("  'def' 和 'fed' 都产生相同的段码 0x38 (d|e|f)")
    print("  因为段码 = 各段 mask 的 OR 结果，与顺序无关")

    display.off()
    print("  演示完成!")


# ==============================================================================
#  演示: show_char() -- 显示字母
# ==============================================================================
def demo_show_char(display: DigitalDisplay) -> None:
    """演示 show_char() 方法: 通过字符名称显示数字/字母.

    show_char() 支持数字 0-9、字母 A-F/H/L/P/U 及小写变体、
    减号 '-'、空白 '#'、小数点 '.'。
    """
    print("\n" + "=" * 65)
    print("  演示: show_char(digit, char) -- 显示字符")
    print("=" * 65)

    # 演示 1: 遍历所有支持的字母
    print("\n  [1] 遍历所有支持的字母字符")
    supported_chars = list("ABCDEFHLPU") + list("onrty") + ["-", "#", "."]
    for ch in supported_chars:
        display.show_char(0, ch)
        # 显示对应的段码信息
        if ch == "#":
            code = 0x00
        elif ch == "-":
            code = 0x40
        elif ch == ".":
            code = 0x80
        elif ch.isdigit():
            code = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F][int(ch)]
        else:
            code = DigitalDisplay.CHAR_MAP.get(ch.upper(), 0)
        bits = DigitalDisplay.segment_to_bits(code)
        print(f"  show_char(0, '{ch}') -> 段码 0x{code:02X}, 点亮段: {bits if bits else '(无)'}")
        time.sleep(0.15)

    # 演示 2: 在 4 位上显示不同字符
    print("\n  [2] 在 4 位上显示 'A B C D'")
    display.show_char(0, "A")
    display.show_char(1, "B")
    display.show_char(2, "C")
    display.show_char(3, "D")
    print("  show_char(0, 'A') -> 0x77")
    print("  show_char(1, 'B') -> 0x7C")
    print("  show_char(2, 'C') -> 0x39")
    print("  show_char(3, 'D') -> 0x5E")
    time.sleep(2)

    # 演示 3: 错误处理 -- 不支持的字符
    print("\n  [3] 异常处理: 不支持的字符")
    try:
        display.show_char(0, "Z")
    except Exception as e:
        print(f"  捕获异常: {e}")

    display.off()
    print("  演示完成!")


# ==============================================================================
#  演示: show_raw() -- 原始段码数组
# ==============================================================================
def demo_show_raw(display: DigitalDisplay) -> None:
    """演示 show_raw() 方法: 通过原始段码数组控制全部 4 位数码管.

    show_raw() 一次性设置所有 4 位数码管的段码。
    """
    print("\n" + "=" * 65)
    print("  演示: show_raw(codes) -- 原始段码数组控制全部 4 位")
    print("=" * 65)

    # 演示 1: 显示 "C0DE" 用原始段码
    print("\n  [1] 显示 'C0DE' 用原始段码")
    # C=0x39, 0=0x3F, D=0x5E, E=0x79
    display.show_raw([0x39, 0x3F, 0x5E, 0x79])
    print("  show_raw([0x39, 0x3F, 0x5E, 0x79]) -> C 0 D E")
    for i, code in enumerate([0x39, 0x3F, 0x5E, 0x79]):
        bits = DigitalDisplay.segment_to_bits(code)
        print(f"    位 {i}: 0x{code:02X} -> {bits}")
    time.sleep(2)

    # 演示 2: 全亮和全灭交替
    print("\n  [2] 全亮和全灭交替闪烁")
    for _ in range(3):
        display.show_raw([0xFF, 0xFF, 0xFF, 0xFF])  # 全亮
        time.sleep(0.3)
        display.show_raw([0x00, 0x00, 0x00, 0x00])  # 全灭
        time.sleep(0.3)

    # 演示 3: 错误处理 -- 长度不为 4
    print("\n  [3] 异常处理: 列表长度不为 4")
    try:
        display.show_raw([0x3F, 0x06, 0x5B])  # 只有 3 个元素
    except Exception as e:
        print(f"  捕获异常: {e}")

    # 演示 4: 错误处理 -- 段码超出范围
    print("\n  [4] 异常处理: 段码超出范围")
    try:
        display.show_raw([0x3F, 0x100, 0x5B, 0x4F])  # 0x100 超出 0x00-0xFF
    except Exception as e:
        print(f"  捕获异常: {e}")

    display.off()
    print("  演示完成!")


# ==============================================================================
#  演示: segment_to_bits() 工具方法
# ==============================================================================
def demo_segment_to_bits() -> None:
    """演示 segment_to_bits() 工具方法: 将段码解析为段名.

    这是一个类方法，无需实例即可调用。
    """
    print("\n" + "=" * 65)
    print("  演示: segment_to_bits(code) -- 段码 -> 段名解析")
    print("=" * 65)

    print("\n  将段码解析为人类可读的段位描述:")
    test_codes = [
        (0x3F, "数字 0"),
        (0x06, "数字 1"),
        (0x38, "字母 L"),
        (0x77, "字母 A"),
        (0xFF, "全亮 (含 dp)"),
        (0x00, "全灭"),
        (0x80, "仅小数点"),
        (0x40, "仅 g 段"),
    ]
    for code, desc in test_codes:
        bits = DigitalDisplay.segment_to_bits(code)
        print(f"  segment_to_bits(0x{code:02X}) = '{bits}'  ({desc})")

    # 演示所有单个段
    print("\n  逐段解析:")
    for seg_name in ["a", "b", "c", "d", "e", "f", "g", "dp"]:
        mask = DigitalDisplay.SEGMENT_MAP[seg_name]
        bits = DigitalDisplay.segment_to_bits(mask)
        print(f"  segment_to_bits(0x{mask:02X}) = '{bits}'  (仅 {seg_name} 段)")

    print("  演示完成!")


# ==============================================================================
#  演示: segments_to_code() 工具方法
# ==============================================================================
def demo_segments_to_code() -> None:
    """演示 segments_to_code() 工具方法: 将段名组合转换为段码.

    这是一个类方法，无需实例即可调用。
    """
    print("\n" + "=" * 65)
    print("  演示: segments_to_code(*segments) -- 段名 -> 段码")
    print("=" * 65)

    print("\n  将段名组合转换为段码:")
    test_cases = [
        (("a", "b", "c", "d", "e", "f"), "数字 0 的段"),
        (("b", "c"), "数字 1 的段"),
        (("d", "e", "f"), "字母 L 的段"),
        (("a", "b", "c", "e", "f", "g"), "字母 A 的段"),
        (("a", "b", "c", "d", "e", "f", "g", "dp"), "全亮含小数点"),
        ((), "全灭"),
    ]
    for segments, desc in test_cases:
        code = DigitalDisplay.segments_to_code(*segments)
        seg_str = "".join(segments) if segments else "(无)"
        print(f"  segments_to_code({seg_str}) = 0x{code:02X}  ({desc})")

    # 演示与 segment_to_bits 的往返
    print("\n  往返验证: segment_to_bits(segments_to_code(*segs)) == segs")
    test_segs = ["def", "abcefg", "abcdefg", "abcdefgdp"]
    for seg_str in test_segs:
        # 将字符串拆分为段名列表
        segs = []
        i = 0
        while i < len(seg_str):
            if i + 1 < len(seg_str) and seg_str[i:i + 2] == "dp":
                segs.append("dp")
                i += 2
            else:
                segs.append(seg_str[i])
                i += 1
        code = DigitalDisplay.segments_to_code(*segs)
        back = DigitalDisplay.segment_to_bits(code)
        match = "OK" if back == seg_str else "FAIL"
        print(f"  '{seg_str}' -> 0x{code:02X} -> '{back}' [{match}]")

    # 演示异常
    print("\n  异常处理: 无效段名")
    try:
        DigitalDisplay.segments_to_code("x", "y")
    except Exception as e:
        print(f"  捕获异常: {e}")

    print("  演示完成!")


# ==============================================================================
#  交互式: 让用户输入段名查看点亮效果
# ==============================================================================
def interactive_segment_explorer(display: DigitalDisplay) -> None:
    """交互式段名探索器.

    用户输入段名组合 (如 "def", "abcefg", "abcdefgdp")，
    程序在数码管上显示对应的点亮效果，并打印段码信息。
    """
    print("\n" + "=" * 65)
    print("  交互式段名探索器")
    print("=" * 65)
    print("""
  输入段名组合 (a,b,c,d,e,f,g,dp) 查看点亮效果。
  例如: def     -> 显示 L (d,e,f 段亮)
        abcefg  -> 显示 A (a,b,c,e,f,g 段亮)
        abcdefg -> 显示 8 (全部 7 段亮)
        dp      -> 仅点亮小数点
        ""      -> 全部熄灭
        q       -> 退出交互模式
""")

    while True:
        try:
            user_input = input("  请输入段名组合 > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  退出交互模式。")
            break

        if user_input in ("q", "quit", "exit"):
            print("  退出交互模式。")
            break

        # 验证输入的段名
        valid = True
        i = 0
        parsed_segs = []
        while i < len(user_input):
            if i + 1 < len(user_input) and user_input[i:i + 2] == "dp":
                parsed_segs.append("dp")
                i += 2
            else:
                seg = user_input[i]
                if seg not in DigitalDisplay.SEGMENT_MAP:
                    print(f"  [错误] 无效段名: '{seg}'，有效: a, b, c, d, e, f, g, dp")
                    valid = False
                    break
                parsed_segs.append(seg)
                i += 1

        if not valid:
            continue

        if not parsed_segs:
            # 空字符串 -> 全部熄灭
            code = 0x00
            display.show_segments(0, "")
            print(f"  段名: (无) -> 段码: 0x{code:02X} -> 全部熄灭")
        else:
            # 计算段码
            code = 0
            for seg in parsed_segs:
                code |= DigitalDisplay.SEGMENT_MAP[seg]
            # 在第 0 位显示
            display.show_segments(0, user_input)
            bits = DigitalDisplay.segment_to_bits(code)
            print(f"  段名: '{user_input}' -> 段码: 0x{code:02X} -> 点亮段: {bits}")

    display.off()


# ==============================================================================
#  主函数
# ==============================================================================
def main() -> None:
    """主函数."""
    print("=" * 65)
    print("  SAKS SDK 示例 07: 数码管段码深度解析")
    print("=" * 65)

    # ---- 第一部分: 知识讲解 (无需硬件) ----
    print(SEGMENT_LAYOUT_ASCII)
    input("\n按 Enter 继续查看 SEGMENT_MAP 映射表...")
    print_segment_map()

    input("\n按 Enter 继续查看段码位定义表...")
    print_bit_definition_table()

    input("\n按 Enter 继续查看数字 0-9 段码表...")
    print_digit_segment_table()

    input("\n按 Enter 继续查看扩展字符表...")
    print_extended_char_table()

    # ---- 第二部分: 工具方法演示 (无需硬件) ----
    input("\n按 Enter 继续演示 segment_to_bits() 工具方法...")
    demo_segment_to_bits()

    input("\n按 Enter 继续演示 segments_to_code() 工具方法...")
    demo_segments_to_code()

    # ---- 第三部分: 硬件演示 (需要树莓派 + SAKS 扩展板) ----
    print("\n" + "=" * 65)
    print("  以下演示需要硬件支持 (树莓派 + SAKS 扩展板)")
    print("=" * 65)

    # 初始化数码管
    display = DigitalDisplay(
        di=SAKSPins.IC_TM1637_DI,
        clk=SAKSPins.IC_TM1637_CLK,
    )

    try:
        input("\n按 Enter 开始 show_segment() 演示...")
        demo_show_segment(display)

        input("\n按 Enter 开始 show_segments() 演示...")
        demo_show_segments(display)

        input("\n按 Enter 开始 show_char() 演示...")
        demo_show_char(display)

        input("\n按 Enter 开始 show_raw() 演示...")
        demo_show_raw(display)

        input("\n按 Enter 进入交互式段名探索器...")
        interactive_segment_explorer(display)

    except KeyboardInterrupt:
        print("\n\n演示被中断。")
    finally:
        display.off()

    print("\n" + "=" * 65)
    print("  示例 07 完成!")
    print("=" * 65)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()