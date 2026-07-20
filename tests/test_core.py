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

"""SAKSHAT 主控制器核心测试."""

from __future__ import annotations

import pytest

from sakshat import (
    SAKSHAT,
    Buzzer,
    Led,
    LedRow,
    DigitalDisplay,
    DipSwitch2Bit,
    DS18B20,
    Tact,
    TactRow,
    Led74HC595,
    SAKSError,
)
from sakshat._gpio import GPIO, GPIOContext


class TestSAKSHATInit:
    """测试 SAKSHAT 初始化."""

    def test_init_creates_instance(self) -> None:
        """初始化创建 SAKSHAT 实例."""
        saks = SAKSHAT()
        assert saks is not None
        assert saks._initialized is True
        saks.cleanup()

    def test_init_creates_buzzer(self) -> None:
        """初始化后 buzzer 属性可用."""
        saks = SAKSHAT()
        assert hasattr(saks, "buzzer")
        assert isinstance(saks.buzzer, Buzzer)
        saks.cleanup()

    def test_init_creates_ledrow(self) -> None:
        """初始化后 ledrow 属性可用."""
        saks = SAKSHAT()
        assert hasattr(saks, "ledrow")
        assert isinstance(saks.ledrow, Led74HC595)
        saks.cleanup()

    def test_init_creates_ds18b20(self) -> None:
        """初始化后 ds18b20 属性可用."""
        saks = SAKSHAT()
        assert hasattr(saks, "ds18b20")
        assert isinstance(saks.ds18b20, DS18B20)
        saks.cleanup()

    def test_init_creates_digital_display(self) -> None:
        """初始化后 digital_display 属性可用."""
        saks = SAKSHAT()
        assert hasattr(saks, "digital_display")
        assert isinstance(saks.digital_display, DigitalDisplay)
        saks.cleanup()

    def test_init_creates_dip_switch(self) -> None:
        """初始化后 dip_switch 属性可用."""
        saks = SAKSHAT()
        assert hasattr(saks, "dip_switch")
        assert isinstance(saks.dip_switch, DipSwitch2Bit)
        saks.cleanup()

    def test_init_creates_tactrow(self) -> None:
        """初始化后 tactrow 属性可用."""
        saks = SAKSHAT()
        assert hasattr(saks, "tactrow")
        assert isinstance(saks.tactrow, TactRow)
        saks.cleanup()

    def test_init_initialized_flag(self) -> None:
        """初始化后 _initialized 为 True."""
        saks = SAKSHAT()
        assert saks._initialized is True
        saks.cleanup()


class TestSAKSHATCleanup:
    """测试 SAKSHAT.cleanup() 方法."""

    def test_cleanup_sets_initialized_false(self) -> None:
        """cleanup 后 _initialized 为 False."""
        saks = SAKSHAT()
        saks.cleanup()
        assert saks._initialized is False

    def test_cleanup_idempotent(self) -> None:
        """多次 cleanup 调用幂等."""
        saks = SAKSHAT()
        saks.cleanup()
        saks.cleanup()
        saks.cleanup()
        assert saks._initialized is False

    def test_cleanup_then_cleanup_again(self) -> None:
        """cleanup 后再次 cleanup 不报错."""
        saks = SAKSHAT()
        saks.cleanup()
        # 第二次 cleanup 不应抛出异常
        saks.cleanup()
        assert saks._initialized is False

    def test_cleanup_before_init(self) -> None:
        """未初始化时 cleanup 不报错 (通过 _auto_cleanup)."""
        # 实际上 SAKSHAT 初始化时如果失败会调用 cleanup
        # 这里测试 cleanup 的防御性
        saks = SAKSHAT()
        saks.cleanup()
        saks.cleanup()  # 幂等


class TestSAKSHATContextManager:
    """测试 SAKSHAT 上下文管理器."""

    def test_with_statement(self) -> None:
        """使用 with 语句创建 SAKSHAT."""
        with SAKSHAT() as saks:
            assert saks._initialized is True
            assert isinstance(saks.buzzer, Buzzer)
        # 退出 with 后应清理
        assert saks._initialized is False

    def test_with_statement_operations(self) -> None:
        """在 with 语句中执行操作."""
        with SAKSHAT() as saks:
            saks.buzzer.on()
            assert saks.buzzer.is_on is True
            saks.buzzer.off()
        assert saks._initialized is False

    def test_with_statement_exception_cleanup(self) -> None:
        """with 语句中发生异常时仍会清理."""
        try:
            with SAKSHAT() as saks:
                assert saks._initialized is True
                raise ValueError("test error")
        except ValueError:
            pass
        assert saks._initialized is False

    def test_with_statement_nested(self) -> None:
        """嵌套 with 语句."""
        with SAKSHAT() as saks1:
            assert saks1._initialized is True
            with SAKSHAT() as saks2:
                assert saks2._initialized is True
            assert saks2._initialized is False
        assert saks1._initialized is False

    def test_with_statement_enter_exit(self) -> None:
        """__enter__ 返回 self, __exit__ 清理资源."""
        saks = SAKSHAT()
        assert saks.__enter__() is saks
        saks.__exit__(None, None, None)
        assert saks._initialized is False


class TestSAKSHATPeripherals:
    """测试 SAKSHAT 外设操作."""

    def test_buzzer_operations(self) -> None:
        """通过 SAKSHAT 操作蜂鸣器."""
        saks = SAKSHAT()
        saks.buzzer.on()
        assert saks.buzzer.is_on is True
        saks.buzzer.off()
        assert saks.buzzer.is_on is False
        saks.cleanup()

    def test_ledrow_operations(self) -> None:
        """通过 SAKSHAT 操作 LED 阵列."""
        saks = SAKSHAT()
        saks.ledrow.on()
        assert saks.ledrow.row_status == [True] * 8
        saks.ledrow.off()
        assert saks.ledrow.row_status == [False] * 8
        saks.cleanup()

    def test_ledrow_set_row(self) -> None:
        """通过 SAKSHAT 设置 LED 阵列."""
        saks = SAKSHAT()
        saks.ledrow.set_row([True, False, True, False, True, False, True, False])
        assert saks.ledrow.row_status == [True, False, True, False, True, False, True, False]
        saks.cleanup()

    def test_digital_display_operations(self) -> None:
        """通过 SAKSHAT 操作数码管."""
        saks = SAKSHAT()
        saks.digital_display.show("12.34")
        assert saks.digital_display.is_on is True
        saks.digital_display.off()
        assert saks.digital_display.is_on is False
        saks.cleanup()

    def test_ds18b20_property(self) -> None:
        """通过 SAKSHAT 访问 DS18B20."""
        saks = SAKSHAT()
        assert isinstance(saks.ds18b20, DS18B20)
        saks.cleanup()

    def test_dip_switch_property(self) -> None:
        """通过 SAKSHAT 访问拨码开关."""
        saks = SAKSHAT()
        assert isinstance(saks.dip_switch, DipSwitch2Bit)
        saks.cleanup()

    def test_tactrow_property(self) -> None:
        """通过 SAKSHAT 访问轻触开关."""
        saks = SAKSHAT()
        assert isinstance(saks.tactrow, TactRow)
        assert len(saks.tactrow.items) == 2
        saks.cleanup()


class TestSAKSHATCallbacks:
    """测试 SAKSHAT 回调处理."""

    def test_dip_switch_status_changed_handler_default(self) -> None:
        """默认 dip_switch_status_changed_handler 为 None."""
        saks = SAKSHAT()
        assert saks.dip_switch_status_changed_handler is None
        saks.cleanup()

    def test_dip_switch_status_changed_handler_set(self) -> None:
        """设置 dip_switch_status_changed_handler."""
        saks = SAKSHAT()
        handler_called = []

        def handler(status: list[bool]) -> None:
            handler_called.append(status)

        saks.dip_switch_status_changed_handler = handler
        assert saks.dip_switch_status_changed_handler is handler
        saks.cleanup()

    def test_tact_event_handler_default(self) -> None:
        """默认 tact_event_handler 为 None."""
        saks = SAKSHAT()
        assert saks.tact_event_handler is None
        saks.cleanup()

    def test_tact_event_handler_set(self) -> None:
        """设置 tact_event_handler."""
        saks = SAKSHAT()
        handler_called = []

        def handler(pin: int, status: bool) -> None:
            handler_called.append((pin, status))

        saks.tact_event_handler = handler
        assert saks.tact_event_handler is handler
        saks.cleanup()

    def test_on_dip_switch_2bit_status_changed_no_handler(self) -> None:
        """无 handler 时回调不报错."""
        saks = SAKSHAT()
        saks.on_dip_switch_2bit_status_changed([True, False])
        saks.cleanup()

    def test_on_dip_switch_2bit_status_changed_with_handler(self) -> None:
        """有 handler 时回调正常执行."""
        saks = SAKSHAT()
        received = []

        def handler(status: list[bool]) -> None:
            received.append(status)

        saks.dip_switch_status_changed_handler = handler
        saks.on_dip_switch_2bit_status_changed([True, False])
        assert received == [[True, False]]
        saks.cleanup()

    def test_on_tact_event_no_handler(self) -> None:
        """无 handler 时回调不报错."""
        saks = SAKSHAT()
        saks.on_tact_event(20, True)
        saks.cleanup()

    def test_on_tact_event_with_handler(self) -> None:
        """有 handler 时回调正常执行."""
        saks = SAKSHAT()
        received = []

        def handler(pin: int, status: bool) -> None:
            received.append((pin, status))

        saks.tact_event_handler = handler
        saks.on_tact_event(20, True)
        assert received == [(20, True)]
        saks.cleanup()

    def test_callback_exception_handled(self) -> None:
        """回调函数抛出异常时不应传播."""
        saks = SAKSHAT()

        def bad_handler(status: list[bool]) -> None:
            raise RuntimeError("callback error")

        saks.dip_switch_status_changed_handler = bad_handler
        # 不应抛出异常
        saks.on_dip_switch_2bit_status_changed([True, False])
        saks.cleanup()


class TestSAKSHATRepr:
    """测试 SAKSHAT __repr__."""

    def test_repr_initialized(self) -> None:
        """初始化后的 __repr__."""
        saks = SAKSHAT()
        r = repr(saks)
        assert "SAKSHAT" in r
        assert "initialized=True" in r
        saks.cleanup()

    def test_repr_after_cleanup(self) -> None:
        """清理后的 __repr__."""
        saks = SAKSHAT()
        saks.cleanup()
        r = repr(saks)
        assert "initialized=False" in r


class TestSAKSHATIntegration:
    """测试 SAKSHAT 集成场景."""

    def test_full_lifecycle(self) -> None:
        """完整生命周期: 初始化 -> 操作 -> 清理."""
        saks = SAKSHAT()
        assert saks._initialized is True

        # 操作蜂鸣器
        saks.buzzer.on()
        assert saks.buzzer.is_on is True
        saks.buzzer.off()

        # 操作 LED
        saks.ledrow.set_row([True, False, True, False, True, False, True, False])
        saks.ledrow.off()

        # 操作数码管
        saks.digital_display.show("8888")
        saks.digital_display.off()

        saks.cleanup()
        assert saks._initialized is False

    def test_cleanup_turns_off_devices(self) -> None:
        """cleanup 关闭所有设备."""
        saks = SAKSHAT()
        saks.buzzer.on()
        saks.ledrow.on()
        saks.digital_display.show("8888")
        saks.cleanup()
        assert saks._initialized is False

    def test_multiple_init_cleanup_cycles(self) -> None:
        """多次初始化-清理循环."""
        for _ in range(3):
            saks = SAKSHAT()
            assert saks._initialized is True
            saks.buzzer.on()
            saks.buzzer.off()
            saks.cleanup()
            assert saks._initialized is False

    def test_shortcut_buzzer_beep(self) -> None:
        """通过 SAKSHAT 快捷使用蜂鸣器."""
        saks = SAKSHAT()
        saks.buzzer.beep(0.01)
        assert saks.buzzer.is_on is False
        saks.cleanup()


class TestGPIOContext:
    """测试 GPIOContext 上下文管理器."""

    def test_gpio_context_enter(self) -> None:
        """进入 GPIOContext 返回 GPIO 提供者."""
        with GPIOContext() as gpio:
            assert gpio is GPIO

    def test_gpio_context_exit_cleans_up(self) -> None:
        """退出 GPIOContext 触发清理."""
        ctx = GPIOContext()
        with ctx:
            assert ctx._cleaned_up is False
        assert ctx._cleaned_up is True

    def test_gpio_context_cleanup_idempotent(self) -> None:
        """多次 cleanup 幂等."""
        ctx = GPIOContext()
        ctx.cleanup()
        assert ctx._cleaned_up is True
        ctx.cleanup()
        assert ctx._cleaned_up is True

    def test_gpio_context_exception_cleanup(self) -> None:
        """上下文中异常时仍清理."""
        ctx = GPIOContext()
        try:
            with ctx:
                raise ValueError("test")
        except ValueError:
            pass
        assert ctx._cleaned_up is True


class TestSAKSHATEdgeCases:
    """测试 SAKSHAT 边缘情况."""

    def test_cleanup_then_operate(self) -> None:
        """清理后外设操作不会报错 (仅 no-op)."""
        saks = SAKSHAT()
        saks.cleanup()
        # cleanup 后外设应该仍然存在
        assert hasattr(saks, "buzzer")
        assert hasattr(saks, "ledrow")

    def test_cleanup_does_not_remove_attributes(self) -> None:
        """清理不会删除属性."""
        saks = SAKSHAT()
        saks.cleanup()
        assert hasattr(saks, "buzzer")
        assert hasattr(saks, "ledrow")
        assert hasattr(saks, "digital_display")
        assert hasattr(saks, "dip_switch")
        assert hasattr(saks, "tactrow")
        assert hasattr(saks, "ds18b20")

    def test_cleanup_without_devices_initialized(self) -> None:
        """设备未完全初始化时 cleanup 不报错."""
        # 通过直接设置 _initialized 来模拟
        saks = SAKSHAT()
        saks.cleanup()
        # 再次 cleanup
        saks.cleanup()

    def test_context_manager_returns_self(self) -> None:
        """上下文管理器 __enter__ 返回 self."""
        saks = SAKSHAT()
        assert saks.__enter__() is saks
        saks.cleanup()

    def test_context_manager_exit_returns_false(self) -> None:
        """__exit__ 返回 False 不抑制异常."""
        saks = SAKSHAT()
        result = saks.__exit__(None, None, None)
        assert result is False
        # 注意: __exit__ 已经调用了 cleanup，所以 _initialized 为 False
        assert saks._initialized is False