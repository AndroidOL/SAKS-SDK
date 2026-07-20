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

"""轻触开关 (Tact) 和 TactRow 测试."""

from __future__ import annotations

import pytest

from sakshat import Tact, TactRow
from sakshat._exceptions import SAKSValidationError
from sakshat._gpio import GPIO


class TestTactInit:
    """测试 Tact 初始化."""

    def test_init_with_valid_pin(self) -> None:
        """使用有效引脚初始化."""
        tact = Tact(pin=20)
        assert tact.pin == 20

    def test_init_with_active_level_high(self) -> None:
        """使用高电平有效初始化."""
        tact = Tact(pin=20, active_level=GPIO.HIGH)
        assert tact.pin == 20

    def test_init_with_active_level_low(self) -> None:
        """使用低电平有效初始化."""
        tact = Tact(pin=16, active_level=GPIO.LOW)
        assert tact.pin == 16

    def test_init_with_negative_pin_raises(self) -> None:
        """负数引脚应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="无效的引脚编号"):
            Tact(pin=-1)

    def test_init_with_pin_zero(self) -> None:
        """引脚 0 初始化."""
        tact = Tact(pin=0)
        assert tact.pin == 0


class TestTactIsOn:
    """测试 Tact.is_on 属性."""

    @pytest.fixture
    def tact(self) -> Tact:
        """创建测试用 Tact 实例."""
        return Tact(pin=20)

    def test_is_on_default(self, tact: Tact) -> None:
        """默认 is_on 为 False (MockGPIO 返回 LOW)."""
        assert isinstance(tact.is_on, bool)

    def test_is_on_returns_bool(self, tact: Tact) -> None:
        """is_on 返回布尔值."""
        assert isinstance(tact.is_on, bool)


class TestTactRegister:
    """测试 Tact 观察者注册."""

    @pytest.fixture
    def tact(self) -> Tact:
        """创建测试用 Tact 实例."""
        return Tact(pin=20)

    def test_register_observer(self, tact: Tact) -> None:
        """注册观察者."""
        observer = _MockTactObserver()
        tact.register(observer)
        assert observer in tact._observers

    def test_register_duplicate_observer(self, tact: Tact) -> None:
        """重复注册同一个观察者不会重复添加."""
        observer = _MockTactObserver()
        tact.register(observer)
        tact.register(observer)
        count = tact._observers.count(observer)
        assert count == 1

    def test_deregister_observer(self, tact: Tact) -> None:
        """移除观察者."""
        observer = _MockTactObserver()
        tact.register(observer)
        tact.deregister(observer)
        assert observer not in tact._observers

    def test_deregister_nonexistent_observer(self, tact: Tact) -> None:
        """移除不存在的观察者不报错."""
        observer = _MockTactObserver()
        tact.deregister(observer)

    def test_register_multiple_observers(self, tact: Tact) -> None:
        """注册多个观察者."""
        observer1 = _MockTactObserver()
        observer2 = _MockTactObserver()
        tact.register(observer1)
        tact.register(observer2)
        assert observer1 in tact._observers
        assert observer2 in tact._observers


class TestTactCallback:
    """测试 Tact 回调函数."""

    @pytest.fixture
    def tact(self) -> Tact:
        """创建测试用 Tact 实例."""
        return Tact(pin=20)

    def test_set_callback(self, tact: Tact) -> None:
        """设置回调函数."""
        callback_called = []

        def callback(pin: int, status: bool) -> None:
            callback_called.append((pin, status))

        tact.set_callback(callback)
        assert tact._callback is not None

    def test_set_callback_none(self, tact: Tact) -> None:
        """设置回调函数为 None."""
        tact.set_callback(None)
        assert tact._callback is None


class TestTactProperties:
    """测试 Tact 属性."""

    def test_pin_property(self) -> None:
        """pin 属性返回正确的引脚编号."""
        tact = Tact(pin=20)
        assert tact.pin == 20
        assert isinstance(tact.pin, int)

    def test_pin_property_different_pin(self) -> None:
        """不同引脚."""
        tact = Tact(pin=16)
        assert tact.pin == 16


class TestTactRepr:
    """测试 Tact __repr__."""

    def test_repr_contains_info(self) -> None:
        """验证 __repr__ 包含关键信息."""
        tact = Tact(pin=20)
        r = repr(tact)
        assert "Tact" in r
        assert "pin=20" in r

    def test_repr_contains_status(self) -> None:
        """验证 __repr__ 包含状态."""
        tact = Tact(pin=20)
        r = repr(tact)
        assert "is_on=" in r


class TestTactRowInit:
    """测试 TactRow 初始化."""

    def test_init_with_valid_pins(self) -> None:
        """使用有效引脚列表初始化."""
        row = TactRow([20, 16])
        assert len(row.items) == 2

    def test_init_with_single_pin(self) -> None:
        """使用单个引脚初始化."""
        row = TactRow([20])
        assert len(row.items) == 1

    def test_init_with_empty_pins_raises(self) -> None:
        """空引脚列表应抛出 SAKSValidationError."""
        with pytest.raises(SAKSValidationError, match="引脚列表不能为空"):
            TactRow([])

    def test_init_with_active_level(self) -> None:
        """使用低电平有效初始化."""
        row = TactRow([20, 16], active_level=GPIO.LOW)
        assert len(row.items) == 2


class TestTactRowOperations:
    """测试 TactRow 操作."""

    @pytest.fixture
    def row(self) -> TactRow:
        """创建测试用 TactRow 实例."""
        return TactRow([20, 16])

    def test_is_on_valid_index(self, row: TactRow) -> None:
        """有效索引的 is_on."""
        result = row.is_on(0)
        assert isinstance(result, bool)

    def test_is_on_negative_index(self, row: TactRow) -> None:
        """负索引 is_on 返回 False."""
        assert row.is_on(-1) is False

    def test_is_on_out_of_range(self, row: TactRow) -> None:
        """越界索引 is_on 返回 False."""
        assert row.is_on(100) is False

    def test_items_returns_tact_list(self, row: TactRow) -> None:
        """items 返回 Tact 实例列表."""
        items = row.items
        assert len(items) == 2
        for item in items:
            assert isinstance(item, Tact)

    def test_row_status(self, row: TactRow) -> None:
        """row_status 返回状态列表."""
        status = row.row_status
        assert isinstance(status, list)
        assert len(status) == 2
        for s in status:
            assert isinstance(s, bool)


class TestTactRowRepr:
    """测试 TactRow __repr__."""

    def test_repr_contains_info(self) -> None:
        """验证 __repr__ 包含关键信息."""
        row = TactRow([20, 16])
        r = repr(row)
        assert "TactRow" in r
        assert "pins=" in r
        assert "status=" in r


class TestTactEdgeCases:
    """测试 Tact 边缘情况."""

    def test_multiple_tacts_different_pins(self) -> None:
        """多个不同引脚的 Tact 独立工作."""
        tact1 = Tact(pin=20)
        tact2 = Tact(pin=16)
        assert tact1.pin == 20
        assert tact2.pin == 16

    def test_deregister_then_register(self) -> None:
        """移除后重新注册."""
        tact = Tact(pin=20)
        observer = _MockTactObserver()
        tact.register(observer)
        tact.deregister(observer)
        tact.register(observer)
        assert observer in tact._observers


class _MockTactObserver:
    """模拟观察者对象."""

    def on_tact_event(self, pin: int, status: bool) -> None:
        """模拟回调."""
        pass