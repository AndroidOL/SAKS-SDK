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

"""SAKSPins 引脚定义和验证测试."""

from __future__ import annotations

import pytest

from sakshat import SAKSPins


class TestSAKSPinsConstants:
    """测试 SAKSPins 常量定义."""

    def test_ic_74hc595_pins(self) -> None:
        """验证 74HC595 芯片引脚常量."""
        assert SAKSPins.IC_74HC595_DS == 6
        assert SAKSPins.IC_74HC595_SHCP == 19
        assert SAKSPins.IC_74HC595_STCP == 13

    def test_ic_tm1637_pins(self) -> None:
        """验证 TM1637 芯片引脚常量."""
        assert SAKSPins.IC_TM1637_DI == 25
        assert SAKSPins.IC_TM1637_CLK == 5

    def test_buzzer_pin(self) -> None:
        """验证蜂鸣器引脚常量."""
        assert SAKSPins.BUZZER == 12

    def test_tact_pins(self) -> None:
        """验证轻触开关引脚常量."""
        assert SAKSPins.TACT_RIGHT == 20
        assert SAKSPins.TACT_LEFT == 16

    def test_dip_switch_pins(self) -> None:
        """验证拨码开关引脚常量."""
        assert SAKSPins.DIP_SWITCH_1 == 21
        assert SAKSPins.DIP_SWITCH_2 == 26

    def test_extension_pins(self) -> None:
        """验证扩展接口引脚常量."""
        assert SAKSPins.IR_SENDER == 17
        assert SAKSPins.IR_RECEIVER == 9
        assert SAKSPins.DS18B20 == 4
        assert SAKSPins.UART_TXD == 14
        assert SAKSPins.UART_RXD == 15
        assert SAKSPins.I2C_SDA == 2
        assert SAKSPins.I2C_SCL == 3

    def test_pins_are_integers(self) -> None:
        """验证所有引脚值都是整数."""
        for member in SAKSPins:
            assert isinstance(member.value, int)

    def test_pins_are_positive(self) -> None:
        """验证所有引脚值都是正数."""
        for member in SAKSPins:
            assert member.value > 0


class TestSAKSPinsValidate:
    """测试 SAKSPins.validate() 方法."""

    def test_validate_known_pin(self) -> None:
        """验证已知引脚返回 True."""
        assert SAKSPins.validate(12) is True
        assert SAKSPins.validate(6) is True
        assert SAKSPins.validate(25) is True
        assert SAKSPins.validate(4) is True

    def test_validate_all_defined_pins(self) -> None:
        """验证所有已定义的引脚都通过 validate."""
        for member in SAKSPins:
            assert SAKSPins.validate(member.value) is True, (
                f"引脚 {member.name}={member.value} 应该有效"
            )

    def test_validate_unknown_pin(self) -> None:
        """验证未定义的引脚返回 False."""
        assert SAKSPins.validate(0) is False
        assert SAKSPins.validate(99) is False
        assert SAKSPins.validate(100) is False

    def test_validate_negative_pin(self) -> None:
        """验证负数引脚返回 False."""
        assert SAKSPins.validate(-1) is False
        assert SAKSPins.validate(-100) is False

    def test_validate_large_positive_pin(self) -> None:
        """验证大正数引脚返回 False."""
        assert SAKSPins.validate(9999) is False


class TestSAKSPinsListAll:
    """测试 SAKSPins.list_all() 方法."""

    def test_list_all_returns_dict(self) -> None:
        """验证 list_all 返回字典."""
        result = SAKSPins.list_all()
        assert isinstance(result, dict)

    def test_list_all_contains_expected_keys(self) -> None:
        """验证 list_all 包含预期的引脚."""
        result = SAKSPins.list_all()
        assert 12 in result
        assert result[12] == "BUZZER"
        assert 6 in result
        assert result[6] == "IC_74HC595_DS"
        assert 4 in result
        assert result[4] == "DS18B20"

    def test_list_all_count_matches_enum(self) -> None:
        """验证 list_all 返回的数量与枚举成员数一致."""
        result = SAKSPins.list_all()
        expected_count = len(list(SAKSPins))
        assert len(result) == expected_count

    def test_list_all_names_are_strings(self) -> None:
        """验证所有名称都是字符串."""
        result = SAKSPins.list_all()
        for name in result.values():
            assert isinstance(name, str)
            assert len(name) > 0

    def test_list_all_keys_are_integers(self) -> None:
        """验证所有键都是整数."""
        result = SAKSPins.list_all()
        for key in result:
            assert isinstance(key, int)


class TestSAKSPinsEnumBehavior:
    """测试 SAKSPins 的 IntEnum 行为."""

    def test_int_equality(self) -> None:
        """验证 IntEnum 可以与整数进行比较."""
        assert SAKSPins.BUZZER == 12

    def test_enum_member_access(self) -> None:
        """验证可以通过值访问枚举成员."""
        assert SAKSPins(12) == SAKSPins.BUZZER

    def test_enum_member_name(self) -> None:
        """验证枚举成员的名称属性."""
        assert SAKSPins.BUZZER.name == "BUZZER"

    def test_enum_member_value(self) -> None:
        """验证枚举成员的值属性."""
        assert SAKSPins.BUZZER.value == 12

    def test_no_duplicate_values(self) -> None:
        """验证没有重复的引脚值."""
        values = [m.value for m in SAKSPins]
        assert len(values) == len(set(values))