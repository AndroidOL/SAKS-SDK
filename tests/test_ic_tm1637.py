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

"""TM1637 数码管驱动芯片测试."""

from __future__ import annotations

import pytest

from sakshat import ICTM1637, IC_TM1637
from sakshat._exceptions import SAKSValidationError
from sakshat._gpio import GPIO


class TestICTM1637Init:
    """测试 ICTM1637 初始化."""

    def test_init_with_valid_pins(self) -> None:
        """使用有效引脚初始化."""
        ic = ICTM1637(di=25, clk=5)
        assert ic is not None

    def test_init_with_active_level_high(self) -> None:
        """使用高电平有效初始化."""
        ic = ICTM1637(di=25, clk=5, active_level=GPIO.HIGH)
        assert ic is not None

    def test_init_with_active_level_low(self) -> None:
        """使用低电平有效初始化."""
        ic = ICTM1637(di=25, clk=5, active_level=GPIO.LOW)
        assert ic is not None


class TestICTM1637Constants:
    """测试 ICTM1637 常量."""

    def test_addresses(self) -> None:
        """验证 ADDRESSES 常量."""
        assert ICTM1637.ADDRESSES == (0xC0, 0xC1, 0xC2, 0xC3)

    def test_cmd_data_auto(self) -> None:
        """验证 CMD_DATA_AUTO 常量."""
        assert ICTM1637.CMD_DATA_AUTO == 0x40

    def test_cmd_data_fixed(self) -> None:
        """验证 CMD_DATA_FIXED 常量."""
        assert ICTM1637.CMD_DATA_FIXED == 0x44

    def test_cmd_display_off(self) -> None:
        """验证 CMD_DISPLAY_OFF 常量."""
        assert ICTM1637.CMD_DISPLAY_OFF == 0x80

    def test_cmd_display_on(self) -> None:
        """验证 CMD_DISPLAY_ON 常量."""
        assert ICTM1637.CMD_DISPLAY_ON == 0x8F


class TestICTM1637SendCommand:
    """测试 ICTM1637.send_command() 方法."""

    @pytest.fixture
    def ic(self) -> ICTM1637:
        """创建测试用 ICTM1637 实例."""
        return ICTM1637(di=25, clk=5)

    def test_send_display_on(self, ic: ICTM1637) -> None:
        """发送开启显示命令."""
        ic.send_command(ICTM1637.CMD_DISPLAY_ON)

    def test_send_display_off(self, ic: ICTM1637) -> None:
        """发送关闭显示命令."""
        ic.send_command(ICTM1637.CMD_DISPLAY_OFF)

    def test_send_data_auto(self, ic: ICTM1637) -> None:
        """发送自动地址增加模式命令."""
        ic.send_command(ICTM1637.CMD_DATA_AUTO)

    def test_send_data_fixed(self, ic: ICTM1637) -> None:
        """发送固定地址模式命令."""
        ic.send_command(ICTM1637.CMD_DATA_FIXED)

    def test_send_custom_command(self, ic: ICTM1637) -> None:
        """发送自定义命令."""
        ic.send_command(0x88)  # 中等亮度


class TestICTM1637WriteByte:
    """测试 ICTM1637.write_byte() 方法."""

    @pytest.fixture
    def ic(self) -> ICTM1637:
        """创建测试用 ICTM1637 实例."""
        return ICTM1637(di=25, clk=5)

    def test_write_byte_min(self, ic: ICTM1637) -> None:
        """写入最小值 0x00."""
        ic.write_byte(0x00)

    def test_write_byte_max(self, ic: ICTM1637) -> None:
        """写入最大值 0xFF."""
        ic.write_byte(0xFF)

    def test_write_byte_mid(self, ic: ICTM1637) -> None:
        """写入中间值."""
        ic.write_byte(0x55)
        ic.write_byte(0xAA)

    def test_write_byte_negative_raises(self, ic: ICTM1637) -> None:
        """负数应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="数据必须在 0x00-0xFF"):
            ic.write_byte(-1)

    def test_write_byte_above_255_raises(self, ic: ICTM1637) -> None:
        """超过 255 应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="数据必须在 0x00-0xFF"):
            ic.write_byte(256)

    def test_write_byte_large_value_raises(self, ic: ICTM1637) -> None:
        """大值应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="数据必须在 0x00-0xFF"):
            ic.write_byte(1000)


class TestICTM1637WriteData:
    """测试 ICTM1637.write_data() 方法."""

    @pytest.fixture
    def ic(self) -> ICTM1637:
        """创建测试用 ICTM1637 实例."""
        return ICTM1637(di=25, clk=5)

    def test_write_data_valid(self, ic: ICTM1637) -> None:
        """正常写入数据."""
        ic.write_data(0xC0, 0x3F)

    def test_write_data_all_addresses(self, ic: ICTM1637) -> None:
        """写入所有地址."""
        for addr in ICTM1637.ADDRESSES:
            ic.write_data(addr, 0x3F)

    def test_write_data_address_below_range_raises(self, ic: ICTM1637) -> None:
        """地址低于 0xC0 应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="地址必须在 0xC0-0xC3"):
            ic.write_data(0xBF, 0x3F)

    def test_write_data_address_above_range_raises(self, ic: ICTM1637) -> None:
        """地址高于 0xC3 应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="地址必须在 0xC0-0xC3"):
            ic.write_data(0xC4, 0x3F)

    def test_write_data_invalid_data_raises(self, ic: ICTM1637) -> None:
        """无效数据应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="数据必须在 0x00-0xFF"):
            ic.write_data(0xC0, 256)

    def test_write_data_boundary_address(self, ic: ICTM1637) -> None:
        """边界地址应通过."""
        ic.write_data(0xC0, 0x3F)  # 下限
        ic.write_data(0xC3, 0x3F)  # 上限

    def test_write_data_boundary_data(self, ic: ICTM1637) -> None:
        """边界数据应通过."""
        ic.write_data(0xC0, 0x00)  # 下限
        ic.write_data(0xC0, 0xFF)  # 上限


class TestICTM1637Clear:
    """测试 ICTM1637.clear() 方法."""

    @pytest.fixture
    def ic(self) -> ICTM1637:
        """创建测试用 ICTM1637 实例."""
        return ICTM1637(di=25, clk=5)

    def test_clear(self, ic: ICTM1637) -> None:
        """清除显示."""
        ic.clear()

    def test_clear_multiple_times(self, ic: ICTM1637) -> None:
        """多次清除 (幂等)."""
        ic.clear()
        ic.clear()
        ic.clear()


class TestICTM1637BusControl:
    """测试 ICTM1637 总线控制."""

    @pytest.fixture
    def ic(self) -> ICTM1637:
        """创建测试用 ICTM1637 实例."""
        return ICTM1637(di=25, clk=5)

    def test_start_bus(self, ic: ICTM1637) -> None:
        """发送起始条件."""
        ic.start_bus()

    def test_stop_bus(self, ic: ICTM1637) -> None:
        """发送停止条件."""
        ic.stop_bus()

    def test_start_stop_sequence(self, ic: ICTM1637) -> None:
        """起始/停止序列."""
        ic.start_bus()
        ic.stop_bus()

    def test_multiple_start_stop(self, ic: ICTM1637) -> None:
        """多次起始/停止序列."""
        for _ in range(3):
            ic.start_bus()
            ic.stop_bus()


class TestICTM1637Repr:
    """测试 ICTM1637 __repr__."""

    def test_repr_contains_info(self) -> None:
        """验证 __repr__ 包含关键信息."""
        ic = ICTM1637(di=25, clk=5)
        r = repr(ic)
        assert "ICTM1637" in r
        assert "di=25" in r
        assert "clk=5" in r


class TestICTM1637Alias:
    """测试向后兼容别名 IC_TM1637."""

    def test_alias_is_same_class(self) -> None:
        """IC_TM1637 是 ICTM1637 的别名."""
        assert IC_TM1637 is ICTM1637

    def test_alias_works(self) -> None:
        """使用别名创建实例."""
        ic = IC_TM1637(di=25, clk=5)
        ic.send_command(ICTM1637.CMD_DISPLAY_ON)


class TestICTM1637FullFlow:
    """测试 ICTM1637 完整工作流程."""

    def test_display_on_write_off(self) -> None:
        """完整流程: 开启显示 -> 写入数据 -> 关闭显示."""
        ic = ICTM1637(di=25, clk=5)
        ic.send_command(ICTM1637.CMD_DATA_FIXED)
        ic.write_data(0xC0, 0x3F)  # 显示数字 0
        ic.send_command(ICTM1637.CMD_DISPLAY_ON)
        ic.clear()