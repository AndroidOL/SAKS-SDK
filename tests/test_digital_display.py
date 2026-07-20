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

"""数码管显示 (DigitalDisplay) 测试."""

from __future__ import annotations

import pytest

from sakshat import DigitalDisplay, DigitalDisplayTM1637
from sakshat._exceptions import SAKSValidationError
from sakshat._gpio import GPIO


class TestDigitalDisplayInit:
    """测试 DigitalDisplay 初始化."""

    def test_init_with_valid_pins(self) -> None:
        """使用有效引脚初始化."""
        display = DigitalDisplay(di=25, clk=5)
        assert display.is_on is False
        assert display.numbers == []

    def test_init_with_active_level_high(self) -> None:
        """使用高电平有效初始化."""
        display = DigitalDisplay(di=25, clk=5, active_level=GPIO.HIGH)
        assert display.is_on is False

    def test_init_with_active_level_low(self) -> None:
        """使用低电平有效初始化."""
        display = DigitalDisplay(di=25, clk=5, active_level=GPIO.LOW)
        assert display.is_on is False


class TestDigitalDisplayProperties:
    """测试 DigitalDisplay 属性."""

    @pytest.fixture
    def display(self) -> DigitalDisplay:
        """创建测试用 DigitalDisplay 实例."""
        return DigitalDisplay(di=25, clk=5)

    def test_is_on_default(self, display: DigitalDisplay) -> None:
        """默认 is_on 为 False."""
        assert display.is_on is False

    def test_numbers_default(self, display: DigitalDisplay) -> None:
        """默认 numbers 为空列表."""
        assert display.numbers == []

    def test_ic_property(self, display: DigitalDisplay) -> None:
        """ic 属性返回 ICTM1637 实例."""
        from sakshat import ICTM1637
        assert isinstance(display.ic, ICTM1637)


class TestDigitalDisplayParse:
    """测试 DigitalDisplay._parse_display_string()."""

    def test_parse_simple_digits(self) -> None:
        """解析简单数字字符串."""
        result = DigitalDisplay._parse_display_string("1234")
        assert result == ["1", "2", "3", "4"]

    def test_parse_with_dot(self) -> None:
        """解析带小数点的字符串."""
        result = DigitalDisplay._parse_display_string("12.34")
        assert result == ["1", "2.", "3", "4"]

    def test_parse_all_dots(self) -> None:
        """解析所有位都带小数点."""
        result = DigitalDisplay._parse_display_string("1.2.3.4.")
        assert result == ["1.", "2.", "3.", "4."]

    def test_parse_with_hash(self) -> None:
        """解析带 # 的字符串."""
        result = DigitalDisplay._parse_display_string("###1")
        assert result == ["#", "#", "#", "1"]

    def test_parse_with_minus(self) -> None:
        """解析带负号的字符串."""
        result = DigitalDisplay._parse_display_string("-1.5")
        assert result == ["-", "1.", "5"]

    def test_parse_short_string(self) -> None:
        """解析短字符串."""
        result = DigitalDisplay._parse_display_string("1")
        assert result == ["1"]

    def test_parse_long_string(self) -> None:
        """解析长字符串 (截断为 4 位)."""
        result = DigitalDisplay._parse_display_string("12345678")
        assert len(result) == 4
        assert result == ["1", "2", "3", "4"]

    def test_parse_empty_string(self) -> None:
        """解析空字符串."""
        result = DigitalDisplay._parse_display_string("")
        assert result == []

    def test_parse_invalid_chars(self) -> None:
        """解析包含无效字符的字符串."""
        result = DigitalDisplay._parse_display_string("ab12")
        assert result == ["1", "2"]

    def test_parse_only_dot(self) -> None:
        """解析纯小数点."""
        result = DigitalDisplay._parse_display_string(".")
        assert result == []

    def test_parse_trailing_dot(self) -> None:
        """解析末尾带小数点的字符串."""
        result = DigitalDisplay._parse_display_string("12.")
        assert result == ["1", "2."]

    def test_parse_leading_dot(self) -> None:
        """解析开头带小数点的字符串."""
        result = DigitalDisplay._parse_display_string(".12")
        assert result == ["1", "2"]


class TestDigitalDisplayOnOff:
    """测试 DigitalDisplay 开关操作."""

    @pytest.fixture
    def display(self) -> DigitalDisplay:
        """创建测试用 DigitalDisplay 实例."""
        return DigitalDisplay(di=25, clk=5)

    def test_on(self, display: DigitalDisplay) -> None:
        """开启显示."""
        display.on()
        assert display.is_on is True

    def test_off(self, display: DigitalDisplay) -> None:
        """关闭显示."""
        display.on()
        display.off()
        assert display.is_on is False

    def test_off_when_off(self, display: DigitalDisplay) -> None:
        """关闭已关闭的显示 (幂等)."""
        display.off()
        assert display.is_on is False
        display.off()
        assert display.is_on is False

    def test_on_when_on(self, display: DigitalDisplay) -> None:
        """打开已打开的显示 (幂等)."""
        display.on()
        assert display.is_on is True
        display.on()
        assert display.is_on is True

    def test_on_off_cycle(self, display: DigitalDisplay) -> None:
        """开关循环."""
        for _ in range(3):
            display.on()
            assert display.is_on is True
            display.off()
            assert display.is_on is False


class TestDigitalDisplayShow:
    """测试 DigitalDisplay.show() 方法."""

    @pytest.fixture
    def display(self) -> DigitalDisplay:
        """创建测试用 DigitalDisplay 实例."""
        return DigitalDisplay(di=25, clk=5)

    def test_show_simple_digits(self, display: DigitalDisplay) -> None:
        """显示简单数字."""
        display.show("1234")
        assert display.is_on is True
        assert display.numbers == ["1", "2", "3", "4"]

    def test_show_with_dot(self, display: DigitalDisplay) -> None:
        """显示带小数点的数字."""
        display.show("12.34")
        assert display.is_on is True
        assert display.numbers == ["1", "2.", "3", "4"]

    def test_show_single_digit(self, display: DigitalDisplay) -> None:
        """显示单个数字."""
        display.show("5")
        assert display.is_on is True
        assert display.numbers == ["5"]

    def test_show_with_hash(self, display: DigitalDisplay) -> None:
        """显示带 # 的字符串."""
        display.show("###1")
        assert display.is_on is True
        assert display.numbers == ["#", "#", "#", "1"]

    def test_show_with_minus(self, display: DigitalDisplay) -> None:
        """显示带负号的字符串."""
        display.show("-1.5")
        assert display.is_on is True
        assert display.numbers == ["-", "1.", "5"]

    def test_show_empty_string_raises(self, display: DigitalDisplay) -> None:
        """空字符串应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="显示字符串不能为空"):
            display.show("")

    def test_show_numbers_property_updated(self, display: DigitalDisplay) -> None:
        """show 后 numbers 属性正确更新."""
        display.show("9.876")
        assert display.numbers == ["9.", "8", "7", "6"]

    def test_show_sequential(self, display: DigitalDisplay) -> None:
        """连续显示不同内容."""
        display.show("1111")
        assert display.numbers == ["1", "1", "1", "1"]
        display.show("2222")
        assert display.numbers == ["2", "2", "2", "2"]
        display.show("3333")
        assert display.numbers == ["3", "3", "3", "3"]

    def test_show_numbers_copy_independent(self, display: DigitalDisplay) -> None:
        """numbers 返回的是副本，修改不影响原始数据."""
        display.show("1234")
        numbers = display.numbers
        numbers.append("5")
        assert display.numbers == ["1", "2", "3", "4"]


class TestDigitalDisplayRepr:
    """测试 DigitalDisplay __repr__."""

    def test_repr_default(self) -> None:
        """默认状态下的 __repr__."""
        display = DigitalDisplay(di=25, clk=5)
        r = repr(display)
        assert "DigitalDisplay" in r
        assert "is_on=False" in r

    def test_repr_after_show(self) -> None:
        """显示内容后的 __repr__."""
        display = DigitalDisplay(di=25, clk=5)
        display.show("1234")
        r = repr(display)
        assert "is_on=True" in r


class TestDigitalDisplayAlias:
    """测试向后兼容别名 DigitalDisplayTM1637."""

    def test_alias_is_same_class(self) -> None:
        """DigitalDisplayTM1637 是 DigitalDisplay 的别名."""
        assert DigitalDisplayTM1637 is DigitalDisplay

    def test_alias_works(self) -> None:
        """使用别名创建实例."""
        display = DigitalDisplayTM1637(di=25, clk=5)
        display.show("8888")
        assert display.is_on is True


class TestDigitalDisplayEdgeCases:
    """测试 DigitalDisplay 边缘情况."""

    @pytest.fixture
    def display(self) -> DigitalDisplay:
        """创建测试用 DigitalDisplay 实例."""
        return DigitalDisplay(di=25, clk=5)

    def test_show_invalid_characters_handled(self, display: DigitalDisplay) -> None:
        """无效字符被静默处理."""
        display.show("abc")
        # 无效字符被解析为空白，不会抛出异常

    def test_show_long_string_truncated(self, display: DigitalDisplay) -> None:
        """长字符串被截断为 4 位."""
        display.show("1234567890")
        assert len(display.numbers) == 4
        assert display.numbers == ["1", "2", "3", "4"]

    def test_show_then_off(self, display: DigitalDisplay) -> None:
        """显示后关闭."""
        display.show("1234")
        assert display.is_on is True
        display.off()
        assert display.is_on is False

    def test_show_then_show_again(self, display: DigitalDisplay) -> None:
        """连续显示."""
        display.show("1111")
        display.show("2222")
        assert display.is_on is True
        assert display.numbers == ["2", "2", "2", "2"]