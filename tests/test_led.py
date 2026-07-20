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

"""LED 和 LedRow 控制测试."""

from __future__ import annotations

import pytest

from sakshat import Led, LedRow
from sakshat._exceptions import SAKSValidationError
from sakshat._gpio import GPIO


class TestLedInit:
    """测试 Led 初始化."""

    def test_init_with_valid_pin(self) -> None:
        """使用有效引脚初始化 LED."""
        led = Led(pin=6)
        assert led.pin == 6
        assert led.is_on is False

    def test_init_with_active_level_high(self) -> None:
        """使用高电平有效初始化 LED."""
        led = Led(pin=6, active_level=GPIO.HIGH)
        assert led.is_on is False

    def test_init_with_active_level_low(self) -> None:
        """使用低电平有效初始化 LED."""
        led = Led(pin=6, active_level=GPIO.LOW)
        assert led.is_on is False

    def test_init_with_negative_pin_raises(self) -> None:
        """使用负数引脚初始化应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="无效的引脚编号"):
            Led(pin=-1)

    def test_init_with_pin_zero(self) -> None:
        """使用引脚 0 初始化 LED."""
        led = Led(pin=0)
        assert led.pin == 0


class TestLedOnOff:
    """测试 Led 开关操作."""

    def test_on_sets_is_on(self) -> None:
        """打开 LED 后 is_on 应为 True."""
        led = Led(pin=6)
        led.on()
        assert led.is_on is True

    def test_off_sets_is_on_false(self) -> None:
        """关闭 LED 后 is_on 应为 False."""
        led = Led(pin=6)
        led.on()
        led.off()
        assert led.is_on is False

    def test_on_then_off(self) -> None:
        """连续开关 LED."""
        led = Led(pin=6)
        led.on()
        assert led.is_on is True
        led.off()
        assert led.is_on is False
        led.on()
        assert led.is_on is True
        led.off()
        assert led.is_on is False

    def test_off_when_already_off(self) -> None:
        """关闭已关闭的 LED (幂等)."""
        led = Led(pin=6)
        led.off()
        assert led.is_on is False
        led.off()
        assert led.is_on is False

    def test_on_when_already_on(self) -> None:
        """打开已打开的 LED (幂等)."""
        led = Led(pin=6)
        led.on()
        assert led.is_on is True
        led.on()
        assert led.is_on is True

    def test_multiple_cycles(self) -> None:
        """多次开关循环."""
        led = Led(pin=6)
        for _ in range(10):
            led.on()
            assert led.is_on is True
            led.off()
            assert led.is_on is False


class TestLedFlash:
    """测试 Led.flash() 方法."""

    def test_flash_positive_duration(self) -> None:
        """正常闪烁指定时长."""
        led = Led(pin=6)
        led.flash(0.01)
        assert led.is_on is False

    def test_flash_zero_duration_raises(self) -> None:
        """持续时间为 0 应抛出 SAKSValidationError."""
        led = Led(pin=6)
        with pytest.raises(SAKSValidationError, match="持续时间必须为正数"):
            led.flash(0)

    def test_flash_negative_duration_raises(self) -> None:
        """持续时间为负数应抛出 SAKSValidationError."""
        led = Led(pin=6)
        with pytest.raises(SAKSValidationError, match="持续时间必须为正数"):
            led.flash(-0.5)

    def test_flash_state_after(self) -> None:
        """闪烁后状态应为关闭."""
        led = Led(pin=6)
        led.flash(0.01)
        assert led.is_on is False


class TestLedFlashPattern:
    """测试 Led.flash_pattern() 方法."""

    def test_flash_pattern_valid(self) -> None:
        """正常节奏闪烁."""
        led = Led(pin=6)
        led.flash_pattern(0.01, 0.01, 2)
        assert led.is_on is False

    def test_flash_pattern_single_repeat(self) -> None:
        """单次重复闪烁."""
        led = Led(pin=6)
        led.flash_pattern(0.01, 0.01, 1)
        assert led.is_on is False

    def test_flash_pattern_on_time_zero_raises(self) -> None:
        """亮起时间为 0 应抛出 SAKSValidationError."""
        led = Led(pin=6)
        with pytest.raises(SAKSValidationError, match="亮起时间必须为正数"):
            led.flash_pattern(0, 0.02, 5)

    def test_flash_pattern_on_time_negative_raises(self) -> None:
        """亮起时间为负数应抛出 SAKSValidationError."""
        led = Led(pin=6)
        with pytest.raises(SAKSValidationError, match="亮起时间必须为正数"):
            led.flash_pattern(-0.01, 0.02, 5)

    def test_flash_pattern_off_time_zero_raises(self) -> None:
        """间隔时间为 0 应抛出 SAKSValidationError."""
        led = Led(pin=6)
        with pytest.raises(SAKSValidationError, match="间隔时间必须为正数"):
            led.flash_pattern(0.02, 0, 5)

    def test_flash_pattern_off_time_negative_raises(self) -> None:
        """间隔时间为负数应抛出 SAKSValidationError."""
        led = Led(pin=6)
        with pytest.raises(SAKSValidationError, match="间隔时间必须为正数"):
            led.flash_pattern(0.02, -0.01, 5)

    def test_flash_pattern_repeat_zero_raises(self) -> None:
        """重复次数为 0 应抛出 SAKSValidationError."""
        led = Led(pin=6)
        with pytest.raises(SAKSValidationError, match="重复次数必须为正整数"):
            led.flash_pattern(0.02, 0.02, 0)

    def test_flash_pattern_repeat_negative_raises(self) -> None:
        """重复次数为负数应抛出 SAKSValidationError."""
        led = Led(pin=6)
        with pytest.raises(SAKSValidationError, match="重复次数必须为正整数"):
            led.flash_pattern(0.02, 0.02, -1)


class TestLedRepr:
    """测试 Led __repr__."""

    def test_repr_off_state(self) -> None:
        """关闭状态下的 __repr__."""
        led = Led(pin=6)
        r = repr(led)
        assert "Led" in r
        assert "pin=6" in r
        assert "is_on=False" in r

    def test_repr_on_state(self) -> None:
        """打开状态下的 __repr__."""
        led = Led(pin=6)
        led.on()
        r = repr(led)
        assert "is_on=True" in r


class TestLedProperties:
    """测试 Led 属性."""

    def test_pin_property(self) -> None:
        """pin 属性返回正确的引脚编号."""
        led = Led(pin=6)
        assert led.pin == 6
        assert isinstance(led.pin, int)

    def test_is_on_property_default(self) -> None:
        """默认 is_on 为 False."""
        led = Led(pin=6)
        assert led.is_on is False


class TestLedRowInit:
    """测试 LedRow 初始化."""

    def test_init_with_valid_pins(self) -> None:
        """使用有效引脚列表初始化 LedRow."""
        row = LedRow([6, 19, 13])
        assert len(row.items) == 3
        assert row.row_status == [False, False, False]

    def test_init_with_single_pin(self) -> None:
        """使用单个引脚初始化 LedRow."""
        row = LedRow([6])
        assert len(row.items) == 1
        assert row.row_status == [False]

    def test_init_with_empty_pins_raises(self) -> None:
        """使用空引脚列表应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="引脚列表不能为空"):
            LedRow([])

    def test_init_with_active_level(self) -> None:
        """使用低电平有效初始化 LedRow."""
        row = LedRow([6, 19, 13], active_level=GPIO.LOW)
        assert len(row.items) == 3


class TestLedRowOperations:
    """测试 LedRow 操作."""

    @pytest.fixture
    def row(self) -> LedRow:
        """创建测试用 LedRow 实例."""
        return LedRow([6, 19, 13])

    def test_on_turns_all_on(self, row: LedRow) -> None:
        """打开所有 LED."""
        row.on()
        assert row.row_status == [True, True, True]

    def test_off_turns_all_off(self, row: LedRow) -> None:
        """关闭所有 LED."""
        row.on()
        row.off()
        assert row.row_status == [False, False, False]

    def test_set_row_full(self, row: LedRow) -> None:
        """设置完整的 LED 状态."""
        row.set_row([True, False, True])
        assert row.row_status == [True, False, True]

    def test_set_row_with_none(self, row: LedRow) -> None:
        """使用 None 保持当前状态不变."""
        row.set_row([True, False, True])
        row.set_row([None, True, None])
        assert row.row_status == [True, True, True]

    def test_set_row_longer_than_leds(self, row: LedRow) -> None:
        """状态列表比 LED 数量多时不应报错."""
        row.set_row([True, False, True, True, False])
        assert row.row_status == [True, False, True]

    def test_set_row_empty(self, row: LedRow) -> None:
        """空状态列表不应改变任何 LED."""
        row.set_row([True, False, True])
        row.set_row([])
        assert row.row_status == [True, False, True]

    def test_set_row_all_none(self, row: LedRow) -> None:
        """全 None 状态列表不应改变任何 LED."""
        row.set_row([True, False, True])
        row.set_row([None, None, None])
        assert row.row_status == [True, False, True]


class TestLedRowIndexOperations:
    """测试 LedRow 按索引操作."""

    @pytest.fixture
    def row(self) -> LedRow:
        """创建测试用 LedRow 实例."""
        return LedRow([6, 19, 13])

    def test_on_for_index_valid(self, row: LedRow) -> None:
        """打开指定索引的 LED."""
        row.on_for_index(0)
        assert row.is_on(0) is True
        assert row.is_on(1) is False
        assert row.is_on(2) is False

    def test_off_for_index_valid(self, row: LedRow) -> None:
        """关闭指定索引的 LED."""
        row.on()
        row.off_for_index(1)
        assert row.is_on(0) is True
        assert row.is_on(1) is False
        assert row.is_on(2) is True

    def test_on_for_index_negative_raises(self, row: LedRow) -> None:
        """负索引应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="LED 索引"):
            row.on_for_index(-1)

    def test_on_for_index_out_of_range_raises(self, row: LedRow) -> None:
        """越界索引应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="LED 索引"):
            row.on_for_index(3)

    def test_off_for_index_negative_raises(self, row: LedRow) -> None:
        """负索引应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="LED 索引"):
            row.off_for_index(-1)

    def test_off_for_index_out_of_range_raises(self, row: LedRow) -> None:
        """越界索引应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="LED 索引"):
            row.off_for_index(100)

    def test_is_on_negative_index(self, row: LedRow) -> None:
        """负索引 is_on 应返回 False."""
        assert row.is_on(-1) is False

    def test_is_on_out_of_range(self, row: LedRow) -> None:
        """越界索引 is_on 应返回 False."""
        assert row.is_on(100) is False


class TestLedRowRepr:
    """测试 LedRow __repr__."""

    def test_repr(self) -> None:
        """验证 __repr__ 包含关键信息."""
        row = LedRow([6, 19, 13])
        r = repr(row)
        assert "LedRow" in r
        assert "pins=" in r

    def test_repr_after_set_row(self) -> None:
        """设置状态后的 __repr__."""
        row = LedRow([6, 19, 13])
        row.set_row([True, False, True])
        r = repr(row)
        assert "True" in r
        assert "False" in r


class TestLedRowProperties:
    """测试 LedRow 属性."""

    @pytest.fixture
    def row(self) -> LedRow:
        """创建测试用 LedRow 实例."""
        return LedRow([6, 19, 13])

    def test_items_returns_led_list(self, row: LedRow) -> None:
        """items 返回 Led 实例列表."""
        items = row.items
        assert len(items) == 3
        for item in items:
            assert isinstance(item, Led)

    def test_row_status_default(self, row: LedRow) -> None:
        """默认 row_status 全为 False."""
        assert row.row_status == [False, False, False]

    def test_row_status_after_operations(self, row: LedRow) -> None:
        """操作后 row_status 正确反映状态."""
        row.on()
        assert row.row_status == [True, True, True]
        row.off_for_index(1)
        assert row.row_status == [True, False, True]


class TestLedEdgeCases:
    """测试 Led 边缘情况."""

    def test_multiple_leds_different_pins(self) -> None:
        """多个不同引脚的 LED 独立工作."""
        led1 = Led(pin=6)
        led2 = Led(pin=19)
        led1.on()
        assert led1.is_on is True
        assert led2.is_on is False
        led2.on()
        assert led1.is_on is True
        assert led2.is_on is True

    def test_cleanup_repeatability(self) -> None:
        """多次关闭的幂等性."""
        led = Led(pin=6)
        led.on()
        for _ in range(5):
            led.off()
        assert led.is_on is False