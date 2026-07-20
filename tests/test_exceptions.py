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

"""SAKS SDK 异常体系测试."""

from __future__ import annotations

import pytest

from sakshat import (
    SAKSError,
    SAKSGPIOError,
    SAKSHardwareError,
    SAKSInitError,
    SAKSTimeoutError,
    SAKSValidationError,
)


class TestExceptionHierarchy:
    """测试异常继承层次."""

    def test_saks_error_is_base(self) -> None:
        """验证 SAKSError 是所有异常的基类."""
        assert issubclass(SAKSGPIOError, SAKSError)
        assert issubclass(SAKSHardwareError, SAKSError)
        assert issubclass(SAKSInitError, SAKSError)
        assert issubclass(SAKSTimeoutError, SAKSError)
        assert issubclass(SAKSValidationError, SAKSError)

    def test_saks_error_is_exception(self) -> None:
        """验证 SAKSError 继承自 Exception."""
        assert issubclass(SAKSError, Exception)

    def test_gpio_error_is_saks_error(self) -> None:
        """验证 SAKSGPIOError 是 SAKSError 的子类."""
        assert issubclass(SAKSGPIOError, SAKSError)

    def test_hardware_error_is_saks_error(self) -> None:
        """验证 SAKSHardwareError 是 SAKSError 的子类."""
        assert issubclass(SAKSHardwareError, SAKSError)

    def test_init_error_is_saks_error(self) -> None:
        """验证 SAKSInitError 是 SAKSError 的子类."""
        assert issubclass(SAKSInitError, SAKSError)

    def test_timeout_error_is_saks_error(self) -> None:
        """验证 SAKSTimeoutError 是 SAKSError 的子类."""
        assert issubclass(SAKSTimeoutError, SAKSError)

    def test_validation_error_is_saks_error(self) -> None:
        """验证 SAKSValidationError 是 SAKSError 的子类."""
        assert issubclass(SAKSValidationError, SAKSError)


class TestExceptionInstantiation:
    """测试异常实例化."""

    def test_saks_error_with_message(self) -> None:
        """验证 SAKSError 可以携带消息."""
        exc = SAKSError("测试错误")
        assert str(exc) == "测试错误"

    def test_saks_error_without_message(self) -> None:
        """验证 SAKSError 可以不带消息."""
        exc = SAKSError()
        assert isinstance(exc, SAKSError)

    def test_validation_error_with_message(self) -> None:
        """验证 SAKSValidationError 可以携带消息."""
        exc = SAKSValidationError("无效的引脚编号: -1")
        assert "无效的引脚编号" in str(exc)

    def test_init_error_with_message(self) -> None:
        """验证 SAKSInitError 可以携带消息."""
        exc = SAKSInitError("GPIO 初始化失败")
        assert "GPIO" in str(exc)

    def test_hardware_error_with_message(self) -> None:
        """验证 SAKSHardwareError 可以携带消息."""
        exc = SAKSHardwareError("传感器读取失败")
        assert "传感器" in str(exc)

    def test_timeout_error_with_message(self) -> None:
        """验证 SAKSTimeoutError 可以携带消息."""
        exc = SAKSTimeoutError("操作超时")
        assert "超时" in str(exc)

    def test_gpio_error_with_message(self) -> None:
        """验证 SAKSGPIOError 可以携带消息."""
        exc = SAKSGPIOError("引脚初始化失败")
        assert "引脚" in str(exc)


class TestExceptionCatching:
    """测试异常捕获模式."""

    def test_catch_saks_error_catches_all(self) -> None:
        """验证使用 SAKSError 可以捕获所有 SAKS 异常."""
        errors = [
            SAKSGPIOError("gpio"),
            SAKSHardwareError("hw"),
            SAKSInitError("init"),
            SAKSTimeoutError("timeout"),
            SAKSValidationError("validation"),
        ]
        for exc in errors:
            try:
                raise exc
            except SAKSError:
                pass  # 预期行为

    def test_catch_validation_error_excludes_others(self) -> None:
        """验证捕获 SAKSValidationError 不会捕获其他 SAKS 异常."""
        caught = False
        try:
            raise SAKSGPIOError("gpio error")
        except SAKSValidationError:
            caught = True
        except SAKSError:
            pass
        assert caught is False

    def test_catch_exception_catches_all(self) -> None:
        """验证使用 Exception 可以捕获所有 SAKS 异常."""
        errors = [
            SAKSError("base"),
            SAKSGPIOError("gpio"),
            SAKSValidationError("validation"),
        ]
        for exc in errors:
            try:
                raise exc
            except Exception:
                pass  # 预期行为

    def test_validation_error_is_saks_error_instance(self) -> None:
        """验证 SAKSValidationError 实例也是 SAKSError 实例."""
        exc = SAKSValidationError("test")
        assert isinstance(exc, SAKSError)
        assert isinstance(exc, Exception)