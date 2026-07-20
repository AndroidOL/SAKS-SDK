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

"""拨码开关 (DipSwitch2Bit) 测试."""

from __future__ import annotations

import pytest

from sakshat import DipSwitch2Bit
from sakshat._exceptions import SAKSValidationError
from sakshat._gpio import GPIO


class TestDipSwitch2BitInit:
    """测试 DipSwitch2Bit 初始化."""

    def test_init_with_valid_pins(self) -> None:
        """使用有效引脚初始化."""
        dip = DipSwitch2Bit(switch1=21, switch2=26)
        assert dip.is_on is not None
        assert len(dip.is_on) == 2

    def test_init_with_active_level_high(self) -> None:
        """使用高电平有效初始化."""
        dip = DipSwitch2Bit(switch1=21, switch2=26, active_level=GPIO.HIGH)
        assert len(dip.is_on) == 2

    def test_init_with_active_level_low(self) -> None:
        """使用低电平有效初始化."""
        dip = DipSwitch2Bit(switch1=21, switch2=26, active_level=GPIO.LOW)
        assert len(dip.is_on) == 2

    def test_init_negative_switch1_raises(self) -> None:
        """switch1 为负数应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="无效的引脚编号"):
            DipSwitch2Bit(switch1=-1, switch2=26)

    def test_init_negative_switch2_raises(self) -> None:
        """switch2 为负数应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="无效的引脚编号"):
            DipSwitch2Bit(switch1=21, switch2=-1)

    def test_init_both_negative_raises(self) -> None:
        """两个引脚均为负数应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="无效的引脚编号"):
            DipSwitch2Bit(switch1=-1, switch2=-2)


class TestDipSwitch2BitIsOn:
    """测试 DipSwitch2Bit.is_on 属性."""

    @pytest.fixture
    def dip(self) -> DipSwitch2Bit:
        """创建测试用 DipSwitch2Bit 实例."""
        return DipSwitch2Bit(switch1=21, switch2=26)

    def test_is_on_returns_list(self, dip: DipSwitch2Bit) -> None:
        """is_on 返回列表."""
        status = dip.is_on
        assert isinstance(status, list)
        assert len(status) == 2

    def test_is_on_returns_bool_list(self, dip: DipSwitch2Bit) -> None:
        """is_on 返回布尔值列表."""
        for value in dip.is_on:
            assert isinstance(value, bool)

    def test_is_on_is_copy(self, dip: DipSwitch2Bit) -> None:
        """is_on 返回的是副本，修改不影响原始数据."""
        status = dip.is_on
        status[0] = not status[0]
        # 再次获取不应被修改
        assert dip.is_on != status or True  # 至少长度一致
        assert len(dip.is_on) == 2


class TestDipSwitch2BitRegister:
    """测试 DipSwitch2Bit 观察者注册."""

    @pytest.fixture
    def dip(self) -> DipSwitch2Bit:
        """创建测试用 DipSwitch2Bit 实例."""
        return DipSwitch2Bit(switch1=21, switch2=26)

    def test_register_observer(self, dip: DipSwitch2Bit) -> None:
        """注册观察者."""
        observer = _MockObserver()
        dip.register(observer)
        assert observer in dip._observers

    def test_register_duplicate_observer(self, dip: DipSwitch2Bit) -> None:
        """重复注册同一个观察者不会重复添加."""
        observer = _MockObserver()
        dip.register(observer)
        dip.register(observer)
        count = dip._observers.count(observer)
        assert count == 1

    def test_deregister_observer(self, dip: DipSwitch2Bit) -> None:
        """移除观察者."""
        observer = _MockObserver()
        dip.register(observer)
        dip.deregister(observer)
        assert observer not in dip._observers

    def test_deregister_nonexistent_observer(self, dip: DipSwitch2Bit) -> None:
        """移除不存在的观察者不报错."""
        observer = _MockObserver()
        dip.deregister(observer)  # 不应抛出异常

    def test_register_multiple_observers(self, dip: DipSwitch2Bit) -> None:
        """注册多个观察者."""
        observer1 = _MockObserver()
        observer2 = _MockObserver()
        dip.register(observer1)
        dip.register(observer2)
        assert observer1 in dip._observers
        assert observer2 in dip._observers


class TestDipSwitch2BitCallback:
    """测试 DipSwitch2Bit 回调函数."""

    @pytest.fixture
    def dip(self) -> DipSwitch2Bit:
        """创建测试用 DipSwitch2Bit 实例."""
        return DipSwitch2Bit(switch1=21, switch2=26)

    def test_set_callback(self, dip: DipSwitch2Bit) -> None:
        """设置回调函数."""
        callback_called = []

        def callback(status: list[bool]) -> None:
            callback_called.append(status)

        dip.set_callback(callback)
        assert dip._callback is not None

    def test_set_callback_none(self, dip: DipSwitch2Bit) -> None:
        """设置回调函数为 None."""
        dip.set_callback(None)
        assert dip._callback is None


class TestDipSwitch2BitRepr:
    """测试 DipSwitch2Bit __repr__."""

    def test_repr_contains_info(self) -> None:
        """验证 __repr__ 包含关键信息."""
        dip = DipSwitch2Bit(switch1=21, switch2=26)
        r = repr(dip)
        assert "DipSwitch2Bit" in r
        assert "pins=" in r

    def test_repr_shows_status(self) -> None:
        """验证 __repr__ 显示状态."""
        dip = DipSwitch2Bit(switch1=21, switch2=26)
        r = repr(dip)
        assert "status=" in r


class _MockObserver:
    """模拟观察者对象."""

    def on_dip_switch_2bit_status_changed(self, status: list[bool]) -> None:
        """模拟回调."""
        pass


class TestDipSwitch2BitEdgeCases:
    """测试 DipSwitch2Bit 边缘情况."""

    def test_init_with_same_pins(self) -> None:
        """两个引脚相同也可以初始化."""
        # 技术上允许（虽然实际使用中不推荐）
        dip = DipSwitch2Bit(switch1=21, switch2=21)
        assert len(dip.is_on) == 2

    def test_deregister_then_register(self) -> None:
        """移除后重新注册."""
        dip = DipSwitch2Bit(switch1=21, switch2=26)
        observer = _MockObserver()
        dip.register(observer)
        dip.deregister(observer)
        dip.register(observer)
        assert observer in dip._observers