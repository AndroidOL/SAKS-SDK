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

"""蜂鸣器 (Buzzer) 控制测试."""

from __future__ import annotations

import pytest

from sakshat import Buzzer
from sakshat._exceptions import SAKSValidationError
from sakshat._gpio import GPIO


class TestBuzzerInit:
    """测试 Buzzer 初始化."""

    def test_init_with_valid_pin(self) -> None:
        """使用有效引脚初始化蜂鸣器."""
        buzzer = Buzzer(pin=12)
        assert buzzer.pin == 12
        assert buzzer.is_on is False

    def test_init_with_active_level_high(self) -> None:
        """使用高电平有效初始化蜂鸣器."""
        buzzer = Buzzer(pin=12, active_level=GPIO.HIGH)
        assert buzzer.pin == 12
        assert buzzer.is_on is False

    def test_init_with_active_level_low(self) -> None:
        """使用低电平有效初始化蜂鸣器."""
        buzzer = Buzzer(pin=12, active_level=GPIO.LOW)
        assert buzzer.pin == 12
        assert buzzer.is_on is False

    def test_init_with_pin_zero(self) -> None:
        """使用引脚 0 初始化蜂鸣器."""
        buzzer = Buzzer(pin=0)
        assert buzzer.pin == 0

    def test_init_with_negative_pin_raises(self) -> None:
        """使用负数引脚初始化应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="无效的引脚编号"):
            Buzzer(pin=-1)

    def test_init_with_large_negative_pin_raises(self) -> None:
        """使用大负数引脚初始化应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError):
            Buzzer(pin=-100)


class TestBuzzerOnOff:
    """测试 Buzzer 开关操作."""

    def test_on_sets_is_on(self) -> None:
        """打开蜂鸣器后 is_on 应为 True."""
        buzzer = Buzzer(pin=12)
        buzzer.on()
        assert buzzer.is_on is True

    def test_off_sets_is_on_false(self) -> None:
        """关闭蜂鸣器后 is_on 应为 False."""
        buzzer = Buzzer(pin=12)
        buzzer.on()
        buzzer.off()
        assert buzzer.is_on is False

    def test_on_then_off(self) -> None:
        """连续开关蜂鸣器."""
        buzzer = Buzzer(pin=12)
        buzzer.on()
        assert buzzer.is_on is True
        buzzer.off()
        assert buzzer.is_on is False
        buzzer.on()
        assert buzzer.is_on is True
        buzzer.off()
        assert buzzer.is_on is False

    def test_off_when_already_off(self) -> None:
        """关闭已关闭的蜂鸣器 (幂等)."""
        buzzer = Buzzer(pin=12)
        buzzer.off()
        assert buzzer.is_on is False
        buzzer.off()
        assert buzzer.is_on is False

    def test_on_when_already_on(self) -> None:
        """打开已打开的蜂鸣器 (幂等)."""
        buzzer = Buzzer(pin=12)
        buzzer.on()
        assert buzzer.is_on is True
        buzzer.on()
        assert buzzer.is_on is True

    def test_multiple_cycles(self) -> None:
        """多次开关循环."""
        buzzer = Buzzer(pin=12)
        for _ in range(10):
            buzzer.on()
            assert buzzer.is_on is True
            buzzer.off()
            assert buzzer.is_on is False


class TestBuzzerBeep:
    """测试 Buzzer.beep() 方法."""

    def test_beep_positive_duration(self) -> None:
        """正常蜂鸣指定时长."""
        buzzer = Buzzer(pin=12)
        buzzer.beep(0.01)
        assert buzzer.is_on is False  # beep 结束后应关闭

    def test_beep_zero_duration_raises(self) -> None:
        """持续时间为 0 应抛出 SAKSValidationError."""
        buzzer = Buzzer(pin=12)
        with pytest.raises(SAKSValidationError, match="蜂鸣时长必须为正数"):
            buzzer.beep(0)

    def test_beep_negative_duration_raises(self) -> None:
        """持续时间为负数应抛出 SAKSValidationError."""
        buzzer = Buzzer(pin=12)
        with pytest.raises(SAKSValidationError, match="蜂鸣时长必须为正数"):
            buzzer.beep(-0.5)

    def test_beep_state_after_beep(self) -> None:
        """蜂鸣后状态应为关闭."""
        buzzer = Buzzer(pin=12)
        buzzer.beep(0.01)
        assert buzzer.is_on is False

    def test_beep_then_on(self) -> None:
        """蜂鸣后可以再次打开."""
        buzzer = Buzzer(pin=12)
        buzzer.beep(0.01)
        buzzer.on()
        assert buzzer.is_on is True


class TestBuzzerBeepPattern:
    """测试 Buzzer.beep_pattern() 方法."""

    def test_beep_pattern_valid(self) -> None:
        """正常节奏蜂鸣."""
        buzzer = Buzzer(pin=12)
        buzzer.beep_pattern(0.01, 0.01, 2)
        assert buzzer.is_on is False

    def test_beep_pattern_single_repeat(self) -> None:
        """单次重复蜂鸣."""
        buzzer = Buzzer(pin=12)
        buzzer.beep_pattern(0.01, 0.01, 1)
        assert buzzer.is_on is False

    def test_beep_pattern_on_time_zero_raises(self) -> None:
        """蜂鸣时间为 0 应抛出 SAKSValidationError."""
        buzzer = Buzzer(pin=12)
        with pytest.raises(SAKSValidationError, match="蜂鸣时间必须为正数"):
            buzzer.beep_pattern(0, 0.02, 5)

    def test_beep_pattern_on_time_negative_raises(self) -> None:
        """蜂鸣时间为负数应抛出 SAKSValidationError."""
        buzzer = Buzzer(pin=12)
        with pytest.raises(SAKSValidationError, match="蜂鸣时间必须为正数"):
            buzzer.beep_pattern(-0.01, 0.02, 5)

    def test_beep_pattern_off_time_zero_raises(self) -> None:
        """间隔时间为 0 应抛出 SAKSValidationError."""
        buzzer = Buzzer(pin=12)
        with pytest.raises(SAKSValidationError, match="间隔时间必须为正数"):
            buzzer.beep_pattern(0.02, 0, 5)

    def test_beep_pattern_off_time_negative_raises(self) -> None:
        """间隔时间为负数应抛出 SAKSValidationError."""
        buzzer = Buzzer(pin=12)
        with pytest.raises(SAKSValidationError, match="间隔时间必须为正数"):
            buzzer.beep_pattern(0.02, -0.01, 5)

    def test_beep_pattern_repeat_zero_raises(self) -> None:
        """重复次数为 0 应抛出 SAKSValidationError."""
        buzzer = Buzzer(pin=12)
        with pytest.raises(SAKSValidationError, match="重复次数必须为正整数"):
            buzzer.beep_pattern(0.02, 0.02, 0)

    def test_beep_pattern_repeat_negative_raises(self) -> None:
        """重复次数为负数应抛出 SAKSValidationError."""
        buzzer = Buzzer(pin=12)
        with pytest.raises(SAKSValidationError, match="重复次数必须为正整数"):
            buzzer.beep_pattern(0.02, 0.02, -1)

    def test_beep_pattern_state_after(self) -> None:
        """节奏蜂鸣结束后状态应为关闭."""
        buzzer = Buzzer(pin=12)
        buzzer.beep_pattern(0.01, 0.01, 3)
        assert buzzer.is_on is False


class TestBuzzerRepr:
    """测试 Buzzer __repr__."""

    def test_repr_off_state(self) -> None:
        """关闭状态下的 __repr__."""
        buzzer = Buzzer(pin=12)
        r = repr(buzzer)
        assert "Buzzer" in r
        assert "pin=12" in r
        assert "is_on=False" in r

    def test_repr_on_state(self) -> None:
        """打开状态下的 __repr__."""
        buzzer = Buzzer(pin=12)
        buzzer.on()
        r = repr(buzzer)
        assert "is_on=True" in r

    def test_repr_with_active_level(self) -> None:
        """不同有效电平下的 __repr__."""
        buzzer = Buzzer(pin=5, active_level=GPIO.LOW)
        r = repr(buzzer)
        assert "pin=5" in r


class TestBuzzerProperties:
    """测试 Buzzer 属性."""

    def test_pin_property(self) -> None:
        """pin 属性返回正确的引脚编号."""
        buzzer = Buzzer(pin=12)
        assert buzzer.pin == 12
        assert isinstance(buzzer.pin, int)

    def test_is_on_property_default(self) -> None:
        """默认 is_on 为 False."""
        buzzer = Buzzer(pin=12)
        assert buzzer.is_on is False
        assert isinstance(buzzer.is_on, bool)


class TestBuzzerEdgeCases:
    """测试 Buzzer 边缘情况."""

    def test_pin_zero_works(self) -> None:
        """引脚 0 可以正常工作."""
        buzzer = Buzzer(pin=0)
        buzzer.on()
        assert buzzer.is_on is True
        buzzer.off()
        assert buzzer.is_on is False

    def test_very_short_beep(self) -> None:
        """极短蜂鸣时间."""
        buzzer = Buzzer(pin=12)
        buzzer.beep(0.001)
        assert buzzer.is_on is False

    def test_very_short_beep_pattern(self) -> None:
        """极短时间的节奏蜂鸣."""
        buzzer = Buzzer(pin=12)
        buzzer.beep_pattern(0.001, 0.001, 3)
        assert buzzer.is_on is False

    def test_cleanup_repeatability_on_off(self) -> None:
        """多次开关的幂等性."""
        buzzer = Buzzer(pin=12)
        for _ in range(5):
            buzzer.off()
            assert buzzer.is_on is False
        for _ in range(5):
            buzzer.on()
            assert buzzer.is_on is True
        for _ in range(5):
            buzzer.off()
            assert buzzer.is_on is False