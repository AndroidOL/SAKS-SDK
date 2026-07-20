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

"""74HC595 移位寄存器驱动测试."""

from __future__ import annotations

import pytest

from sakshat import IC74HC595, IC_74HC595
from sakshat._exceptions import SAKSValidationError
from sakshat._gpio import GPIO


class TestIC74HC595Init:
    """测试 IC74HC595 初始化."""

    def test_init_with_valid_pins(self) -> None:
        """使用有效引脚初始化 IC74HC595."""
        ic = IC74HC595(ds=6, shcp=19, stcp=13)
        assert ic.data == 0x00

    def test_init_with_active_level_high(self) -> None:
        """使用高电平有效初始化."""
        ic = IC74HC595(ds=6, shcp=19, stcp=13, active_level=GPIO.HIGH)
        assert ic.data == 0x00

    def test_init_with_active_level_low(self) -> None:
        """使用低电平有效初始化."""
        ic = IC74HC595(ds=6, shcp=19, stcp=13, active_level=GPIO.LOW)
        assert ic.data == 0x00

    def test_default_data_is_zero(self) -> None:
        """默认数据为 0."""
        ic = IC74HC595(ds=6, shcp=19, stcp=13)
        assert ic.data == 0
        assert ic.data == 0x00


class TestIC74HC595SetData:
    """测试 IC74HC595.set_data() 方法."""

    @pytest.fixture
    def ic(self) -> IC74HC595:
        """创建测试用 IC74HC595 实例."""
        return IC74HC595(ds=6, shcp=19, stcp=13)

    def test_set_data_zero(self, ic: IC74HC595) -> None:
        """设置数据为 0x00."""
        ic.set_data(0x00)
        assert ic.data == 0x00

    def test_set_data_max(self, ic: IC74HC595) -> None:
        """设置数据为 0xFF."""
        ic.set_data(0xFF)
        assert ic.data == 0xFF

    def test_set_data_mid_range(self, ic: IC74HC595) -> None:
        """设置数据为中间值."""
        ic.set_data(0x55)
        assert ic.data == 0x55
        ic.set_data(0xAA)
        assert ic.data == 0xAA

    def test_set_data_single_bit(self, ic: IC74HC595) -> None:
        """设置单个位."""
        for bit in range(8):
            value = 1 << bit
            ic.set_data(value)
            assert ic.data == value

    def test_set_data_negative_raises(self, ic: IC74HC595) -> None:
        """负数数据应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="数据必须在 0x00-0xFF"):
            ic.set_data(-1)

    def test_set_data_above_255_raises(self, ic: IC74HC595) -> None:
        """超过 255 的数据应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="数据必须在 0x00-0xFF"):
            ic.set_data(256)

    def test_set_data_large_value_raises(self, ic: IC74HC595) -> None:
        """大值数据应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="数据必须在 0x00-0xFF"):
            ic.set_data(1000)

    def test_set_data_boundary_255(self, ic: IC74HC595) -> None:
        """边界值 255 应通过."""
        ic.set_data(255)
        assert ic.data == 255

    def test_set_data_boundary_0(self, ic: IC74HC595) -> None:
        """边界值 0 应通过."""
        ic.set_data(0)
        assert ic.data == 0

    def test_sequential_set_data(self, ic: IC74HC595) -> None:
        """连续设置不同数据."""
        for value in [0x00, 0xFF, 0x55, 0xAA, 0x01, 0x80]:
            ic.set_data(value)
            assert ic.data == value


class TestIC74HC595Clear:
    """测试 IC74HC595.clear() 方法."""

    @pytest.fixture
    def ic(self) -> IC74HC595:
        """创建测试用 IC74HC595 实例."""
        return IC74HC595(ds=6, shcp=19, stcp=13)

    def test_clear_from_zero(self, ic: IC74HC595) -> None:
        """从 0 清零."""
        ic.set_data(0x00)
        ic.clear()
        assert ic.data == 0x00

    def test_clear_from_max(self, ic: IC74HC595) -> None:
        """从 0xFF 清零."""
        ic.set_data(0xFF)
        ic.clear()
        assert ic.data == 0x00

    def test_clear_from_mid(self, ic: IC74HC595) -> None:
        """从中间值清零."""
        ic.set_data(0xAA)
        ic.clear()
        assert ic.data == 0x00

    def test_clear_idempotent(self, ic: IC74HC595) -> None:
        """多次清零操作幂等."""
        ic.clear()
        assert ic.data == 0x00
        ic.clear()
        assert ic.data == 0x00
        ic.clear()
        assert ic.data == 0x00


class TestIC74HC595Repr:
    """测试 IC74HC595 __repr__."""

    def test_repr_contains_info(self) -> None:
        """验证 __repr__ 包含关键信息."""
        ic = IC74HC595(ds=6, shcp=19, stcp=13)
        r = repr(ic)
        assert "IC74HC595" in r
        assert "ds=6" in r
        assert "shcp=19" in r
        assert "stcp=13" in r

    def test_repr_shows_data(self) -> None:
        """验证 __repr__ 显示当前数据."""
        ic = IC74HC595(ds=6, shcp=19, stcp=13)
        ic.set_data(0xAB)
        r = repr(ic)
        assert "AB" in r


class TestIC74HC595DataProperty:
    """测试 IC74HC595 data 属性."""

    def test_data_property_read_only(self) -> None:
        """data 是只读属性，设置后通过 set_data 更新."""
        ic = IC74HC595(ds=6, shcp=19, stcp=13)
        ic.set_data(0x42)
        assert ic.data == 0x42
        ic.set_data(0x00)
        assert ic.data == 0x00

    def test_data_type(self) -> None:
        """data 返回 int 类型."""
        ic = IC74HC595(ds=6, shcp=19, stcp=13)
        ic.set_data(0xFF)
        assert isinstance(ic.data, int)


class TestIC74HC595Alias:
    """测试向后兼容别名 IC_74HC595."""

    def test_alias_is_same_class(self) -> None:
        """IC_74HC595 是 IC74HC595 的别名."""
        assert IC_74HC595 is IC74HC595

    def test_alias_works(self) -> None:
        """使用别名创建实例."""
        ic = IC_74HC595(ds=6, shcp=19, stcp=13)
        ic.set_data(0x55)
        assert ic.data == 0x55