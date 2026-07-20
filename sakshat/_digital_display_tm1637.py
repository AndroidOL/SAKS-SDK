# Copyright (c) 2016-2026 NXEZ.COM.
# https://www.nxez.com
#
# Licensed under the GNU General Public License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.gnu.org/licenses/gpl-2.0.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""TM1637 数码管显示模块.

通过 TM1637 芯片驱动 4 位共阳极数码管，支持数字、字母、小数点显示，
以及段码级别的精细控制。

7 段数码管段位布局 (共阳极)::

       a
      ---
    f|   |b
      -g-
    e|   |c
      ---
       d    ·dp

段码位定义 (bit 7..0 = dp.g.f.e.d.c.b.a):
    - a = 0x01 (bit 0)
    - b = 0x02 (bit 1)
    - c = 0x04 (bit 2)
    - d = 0x08 (bit 3)
    - e = 0x10 (bit 4)
    - f = 0x20 (bit 5)
    - g = 0x40 (bit 6)
    - dp = 0x80 (bit 7)

显示格式说明:
    - "1.2.3.4." -> 显示 "1234"，所有小数点都亮
    - "12.34"    -> 显示 "1234"，第 2 位后的小数点亮
    - "###1"     -> 前三位熄灭，第 4 位显示 "1"
    - "-1.5"     -> 第 1 位显示负号，后面显示 "1.5"

段码控制:
    - show_segment(1, 0x38)    -> 第 1 位显示 "L" (d,e,f 段亮)
    - show_segments(1, "def")  -> 同上，使用段名
    - show_raw([0x3F, 0x06, 0x00, 0x00])  -> 原始段码控制全部 4 位

Example:
    >>> from sakshat import DigitalDisplay
    >>> display = DigitalDisplay(di=25, clk=5)
    >>> display.show("12.34")
    >>> display.show_segment(0, 0x38)  # 第 0 位显示 'L'
    >>> display.off()
"""

from __future__ import annotations

import re
import logging
import sys

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

from sakshat._exceptions import SAKSValidationError
from sakshat._gpio import GPIO
from sakshat._ic_tm1637 import ICTM1637

logger = logging.getLogger(__name__)


class DigitalDisplay:
    """TM1637 4 位数码管显示控制类.

    通过 TM1637 芯片驱动 4 位共阳极数码管。
    支持数字 0-9、字母 A-F/L/P/U、负号 '-'、小数点 '.'、空白 '#'，
    以及段码级别的精细控制。

    Attributes:
        is_on: 数码管是否处于显示状态.
        numbers: 当前显示的字符列表.
        SEGMENT_MAP: 段名到掩码的映射字典.
    """

    # 7 段数码管码表: 0-9, 空白(#), 负号(-)
    # 段位: .GFEDCBA (1=亮, 0=灭)
    _SEGMENT_CODE: tuple[int, ...] = (
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
        0x00,  # 空白 (#)
        0x40,  # 负号 (-)
    )

    _BLANK_INDEX: int = 10
    _MINUS_INDEX: int = 11

    # ---- 段码映射 ----
    # 段名到位掩码的映射
    SEGMENT_MAP: dict[str, int] = {
        "a": 0x01,   # bit 0
        "b": 0x02,   # bit 1
        "c": 0x04,   # bit 2
        "d": 0x08,   # bit 3
        "e": 0x10,   # bit 4
        "f": 0x20,   # bit 5
        "g": 0x40,   # bit 6
        "dp": 0x80,  # bit 7 (小数点)
    }

    # ---- 扩展字符码表 ----
    # 常用字母的段码
    CHAR_MAP: dict[str, int] = {
        "A": 0x77,  # a,b,c,e,f,g
        "B": 0x7C,  # c,d,e,f,g  (小写 b 风格)
        "C": 0x39,  # a,d,e,f
        "D": 0x5E,  # b,c,d,e,g  (小写 d 风格)
        "E": 0x79,  # a,d,e,f,g
        "F": 0x71,  # a,e,f,g
        "H": 0x76,  # b,c,e,f,g
        "L": 0x38,  # d,e,f
        "P": 0x73,  # a,b,e,f,g
        "U": 0x3E,  # b,c,d,e,f
        "o": 0x5C,  # c,d,e,g  (小写 o)
        "n": 0x54,  # c,e,g    (小写 n)
        "r": 0x50,  # e,g      (小写 r)
        "t": 0x78,  # d,e,f,g  (小写 t)
        "y": 0x6E,  # b,c,d,f,g (小写 y)
    }

    def __init__(
        self,
        *,
        di: int,
        clk: int,
        active_level: int = GPIO.HIGH,
    ) -> None:
        """初始化数码管显示.

        Args:
            di: 数据输入/输出引脚 (BCM 编号).
            clk: 时钟引脚 (BCM 编号).
            active_level: 有效电平.
        """
        self._ic: ICTM1637 = ICTM1637(
            di=di, clk=clk, active_level=active_level
        )
        self._numbers: list[str] = []
        self._is_on: bool = False

    @property
    def is_on(self) -> bool:
        """数码管是否处于显示状态."""
        return self._is_on

    @property
    def numbers(self) -> list[str]:
        """当前显示的字符列表."""
        return self._numbers.copy()

    @property
    def ic(self) -> ICTM1637:
        """底层 TM1637 芯片实例."""
        return self._ic

    @staticmethod
    def _parse_display_string(text: str) -> list[str]:
        """解析显示字符串为字符列表.

        Args:
            text: 显示字符串，如 "12.34"、"###1"、"-1.5".

        Returns:
            解析后的字符列表，每个元素如 "1", "2.", "3", "4".
        """
        pattern = re.compile(r"[-#\d]\.?")
        return pattern.findall(text)[:4]

    def on(self) -> None:
        """开启显示 (最大亮度)."""
        self._ic.send_command(self._ic.CMD_DISPLAY_ON)
        self._is_on = True

    def off(self) -> None:
        """关闭显示."""
        self._ic.clear()
        self._is_on = False

    def show(self, text: str) -> None:
        """在数码管上显示字符串.

        Args:
            text: 显示字符串，支持以下格式:
                - "1234"  -> 显示 4 位数字
                - "12.34" -> 显示 "1234"，第 2 位小数点亮
                - "###1"  -> 前 3 位熄灭，第 4 位显示 1
                - "-1.5"  -> 第 1 位显示负号

        Raises:
            SAKSValidationError: 字符串为空时抛出.
        """
        if not text:
            raise SAKSValidationError("显示字符串不能为空")

        self._numbers = self._parse_display_string(text)
        self._ic.send_command(self._ic.CMD_DATA_FIXED)

        for i, item in enumerate(self._numbers):
            if i >= 4:
                break

            has_dot = "." in item
            char = item.replace(".", "")

            if char == "#":
                seg_index = self._BLANK_INDEX
            elif char == "-":
                seg_index = self._MINUS_INDEX
            else:
                try:
                    seg_index = int(char)
                except ValueError:
                    seg_index = self._BLANK_INDEX

            code = self._SEGMENT_CODE[seg_index]
            if has_dot:
                code |= 0x80

            self._ic.write_data(self._ic.ADDRESSES[i], code)

        self.on()

    # ---- 段码级精细控制 ----
    def show_segment(self, digit: int, code: int) -> None:
        """在指定位数码管上显示自定义段码.

        直接通过十六进制段码控制单个数码管的每段亮灭。
        段码的每个 bit 对应一段::

            bit 7: dp (小数点)
            bit 6: g
            bit 5: f
            bit 4: e
            bit 3: d
            bit 2: c
            bit 1: b
            bit 0: a

        Args:
            digit: 数码管索引 (0-3，从左到右).
            code: 段码 (0x00-0xFF)，每个 bit 控制一段亮灭.

        Raises:
            SAKSValidationError: 索引或段码超出范围时抛出.

        Example:
            >>> # 第 0 位显示 'L' (d,e,f 段亮 = 0x38)
            >>> display.show_segment(0, 0x38)
            >>> # 第 1 位显示 'A' (a,b,c,e,f,g 段亮 = 0x77)
            >>> display.show_segment(1, 0x77)
            >>> # 第 2 位显示数字 8 加小数点 (0x7F | 0x80 = 0xFF)
            >>> display.show_segment(2, 0xFF)
            >>> # 第 3 位全部熄灭
            >>> display.show_segment(3, 0x00)
        """
        if not (0 <= digit <= 3):
            raise SAKSValidationError(
                f"数码管索引必须在 0-3 范围内，收到: {digit}"
            )
        if not (0 <= code <= 0xFF):
            raise SAKSValidationError(
                f"段码必须在 0x00-0xFF 范围内，收到: {hex(code)}"
            )
        self._ic.send_command(self._ic.CMD_DATA_FIXED)
        self._ic.write_data(self._ic.ADDRESSES[digit], code)
        self.on()

    def show_segments(self, digit: int, segments: str) -> None:
        """在指定位数码管上点亮指定段.

        通过段名字符串控制单个数码管的亮灭。

        Args:
            digit: 数码管索引 (0-3，从左到右).
            segments: 段名字符串，由 'a'~'g' 和 'dp' 组成。
                      例如 "def" 表示点亮 d、e、f 三段。
                      传入空字符串 "" 表示全部熄灭。

        Raises:
            SAKSValidationError: 索引越界或段名无效时抛出.

        Example:
            >>> # 第 0 位显示 'L' (d,e,f 段亮)
            >>> display.show_segments(0, "def")
            >>> # 第 1 位显示 'A' (a,b,c,e,f,g 段亮)
            >>> display.show_segments(1, "abcefg")
            >>> # 第 2 位显示数字 8 加小数点
            >>> display.show_segments(2, "abcdefgdp")
            >>> # 第 3 位全部熄灭
            >>> display.show_segments(3, "")
        """
        if not (0 <= digit <= 3):
            raise SAKSValidationError(
                f"数码管索引必须在 0-3 范围内，收到: {digit}"
            )

        code = 0
        # 解析段名: 支持连续字符串如 "def" / "abcefgdp"
        # 先尝试匹配 "dp" (双字符)，再匹配单字符
        i = 0
        while i < len(segments):
            if i + 1 < len(segments) and segments[i:i + 2] == "dp":
                code |= self.SEGMENT_MAP["dp"]
                i += 2
            else:
                seg = segments[i]
                if seg not in self.SEGMENT_MAP:
                    raise SAKSValidationError(
                        f"无效的段名: '{seg}'，有效段名: a, b, c, d, e, f, g, dp"
                    )
                code |= self.SEGMENT_MAP[seg]
                i += 1

        self.show_segment(digit, code)

    def show_char(self, digit: int, char: str) -> None:
        """在指定位数码管上显示单个字符.

        支持数字 0-9、字母 A-F/H/L/P/U 及小写变体、减号 '-'、
        空白 '#'、小数点 '.'。

        Args:
            digit: 数码管索引 (0-3，从左到右).
            char: 要显示的字符，支持:
                - 数字: "0"-"9"
                - 字母: "A"-"F", "H", "L", "P", "U", "o", "n", "r", "t", "y"
                - 空白: "#" (全部熄灭)
                - 减号: "-"
                - 小数点: "." (仅点亮 dp 段)

        Raises:
            SAKSValidationError: 索引越界或字符不支持时抛出.

        Example:
            >>> display.show_char(0, "L")   # 第 0 位显示 'L'
            >>> display.show_char(1, "A")   # 第 1 位显示 'A'
            >>> display.show_char(2, "5")   # 第 2 位显示 '5'
            >>> display.show_char(3, "#")   # 第 3 位熄灭
        """
        if not (0 <= digit <= 3):
            raise SAKSValidationError(
                f"数码管索引必须在 0-3 范围内，收到: {digit}"
            )

        if char == "#":
            code = self._SEGMENT_CODE[self._BLANK_INDEX]
        elif char == "-":
            code = self._SEGMENT_CODE[self._MINUS_INDEX]
        elif char == ".":
            code = self.SEGMENT_MAP["dp"]
        elif char.isdigit():
            code = self._SEGMENT_CODE[int(char)]
        elif char.upper() in self.CHAR_MAP:
            code = self.CHAR_MAP[char.upper()]
        else:
            raise SAKSValidationError(
                f"不支持的字符: '{char}'。"
                f"支持的字符: 0-9, A-F, H, L, P, U, o, n, r, t, y, -, #, ."
            )

        self.show_segment(digit, code)

    def show_raw(self, codes: list[int]) -> None:
        """通过原始段码数组控制全部 4 位数码管.

        一次性设置所有 4 位数码管的段码，适合需要同时更新全部位的场景。

        Args:
            codes: 4 个段码的列表 (0x00-0xFF)，索引 0 对应最左位。

        Raises:
            SAKSValidationError: 列表长度不为 4 或段码超出范围时抛出.

        Example:
            >>> # 显示 "L A 5" 加全灭
            >>> display.show_raw([0x38, 0x77, 0x6D, 0x00])
        """
        if len(codes) != 4:
            raise SAKSValidationError(
                f"段码列表必须有 4 个元素，收到: {len(codes)}"
            )
        for i, code in enumerate(codes):
            if not (0 <= code <= 0xFF):
                raise SAKSValidationError(
                    f"段码 [{i}] 必须在 0x00-0xFF 范围内，收到: {hex(code)}"
                )

        self._ic.send_command(self._ic.CMD_DATA_FIXED)
        for i, code in enumerate(codes):
            self._ic.write_data(self._ic.ADDRESSES[i], code)
        self.on()

    # ---- 工具方法 ----
    @classmethod
    def segment_to_bits(cls, code: int) -> str:
        """将段码解析为人类可读的段位描述.

        Args:
            code: 段码 (0x00-0xFF).

        Returns:
            段位描述字符串，如 "abcdefg" 表示全部段亮。

        Example:
            >>> DigitalDisplay.segment_to_bits(0x38)
            'def'
            >>> DigitalDisplay.segment_to_bits(0x3F)
            'abcdef'
        """
        result = ""
        for seg_name, mask in cls.SEGMENT_MAP.items():
            if code & mask:
                result += seg_name
        return result

    @classmethod
    def segments_to_code(cls, *segments: str) -> int:
        """将段名组合转换为段码.

        Args:
            *segments: 段名，如 "a", "b", "dp" 等。

        Returns:
            合并后的段码。

        Example:
            >>> DigitalDisplay.segments_to_code("d", "e", "f")
            0x38
            >>> DigitalDisplay.segments_to_code("a", "b", "c", "d", "e", "f")
            0x3F
        """
        code = 0
        for seg in segments:
            if seg not in cls.SEGMENT_MAP:
                raise SAKSValidationError(
                    f"无效的段名: '{seg}'，有效段名: a, b, c, d, e, f, g, dp"
                )
            code |= cls.SEGMENT_MAP[seg]
        return code

    @override
    def __repr__(self) -> str:
        return f"DigitalDisplay(numbers={self._numbers}, is_on={self._is_on})"


# 向后兼容别名
DigitalDisplayTM1637 = DigitalDisplay