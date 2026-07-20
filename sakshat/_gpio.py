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

"""GPIO 抽象层.

提供统一的 GPIO 操作接口，隔离 RPi.GPIO 依赖。
当 RPi.GPIO 不可用时（如开发/测试环境），所有操作静默降级为 no-op。

所有 GPIO 资源管理遵循 RAII 原则，通过上下文管理器确保资源释放。
"""

from __future__ import annotations

import logging
from contextlib import AbstractContextManager
from typing import Protocol

logger = logging.getLogger(__name__)

try:
    import RPi.GPIO as _GPIO  # type: ignore[import-untyped]
except ImportError:
    _GPIO = None  # type: ignore[assignment]
    logger.debug("RPi.GPIO 不可用，GPIO 操作将处于模拟模式")


class GPIOProvider(Protocol):
    """GPIO 操作提供者协议."""

    @staticmethod
    def setup(pin: int, mode: int, pull_up_down: int = 0) -> None: ...
    @staticmethod
    def output(pin: int, value: int) -> None: ...
    @staticmethod
    def input(pin: int) -> int: ...
    @staticmethod
    def add_event_detect(
        pin: int, edge: int, callback: object, bouncetime: int = 0
    ) -> None: ...
    @staticmethod
    def setmode(mode: int) -> None: ...
    @staticmethod
    def setwarnings(value: bool) -> None: ...
    @staticmethod
    def cleanup() -> None: ...
    @staticmethod
    def PWM(pin: int, frequency: int) -> object: ...


class _MockGPIO:
    """模拟 GPIO 实现，用于非树莓派环境."""

    BCM = 11
    BOARD = 10
    OUT = 0
    IN = 1
    HIGH = 1
    LOW = 0
    PUD_UP = 2
    PUD_DOWN = 1
    BOTH = 33
    RISING = 31
    FALLING = 32

    @staticmethod
    def setup(pin: int, mode: int, pull_up_down: int = 0) -> None:  # noqa: ARG004
        logger.debug("Mock GPIO.setup(pin=%d, mode=%d)", pin, mode)

    @staticmethod
    def output(pin: int, value: int) -> None:  # noqa: ARG004
        logger.debug("Mock GPIO.output(pin=%d, value=%d)", pin, value)

    @staticmethod
    def input(pin: int) -> int:  # noqa: ARG004
        return _MockGPIO.LOW

    @staticmethod
    def add_event_detect(
        pin: int, edge: int, callback: object, bouncetime: int = 0  # noqa: ARG004
    ) -> None:
        logger.debug("Mock GPIO.add_event_detect(pin=%d)", pin)

    @staticmethod
    def setmode(mode: int) -> None:  # noqa: ARG004
        logger.debug("Mock GPIO.setmode(mode=%d)", mode)

    @staticmethod
    def setwarnings(value: bool) -> None:  # noqa: ARG004
        logger.debug("Mock GPIO.setwarnings(value=%s)", value)

    @staticmethod
    def cleanup() -> None:
        logger.debug("Mock GPIO.cleanup()")

    @staticmethod
    def PWM(pin: int, frequency: int) -> object:  # noqa: ARG004
        """返回模拟 PWM 对象."""

        class _MockPWM:
            def start(self, duty_cycle: int) -> None: ...
            def stop(self) -> None: ...
            def ChangeDutyCycle(self, duty_cycle: int) -> None: ...
            def ChangeFrequency(self, frequency: int) -> None: ...

        return _MockPWM()


# 选择真实的 GPIO 或模拟实现
GPIO: GPIOProvider = _GPIO if _GPIO is not None else _MockGPIO  # type: ignore[assignment]


class GPIOContext(AbstractContextManager):
    """GPIO 资源管理上下文.

    确保 GPIO 资源在任何情况下都能被正确释放。
    支持重复调用 cleanup，不会产生副作用。

    Example:
        >>> with GPIOContext() as gpio:
        ...     gpio.setup(12, gpio.OUT)
        ...     gpio.output(12, gpio.HIGH)
    """

    def __init__(self) -> None:
        self._cleaned_up = False

    def __enter__(self) -> GPIOProvider:
        return GPIO

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> bool:
        self.cleanup()
        return False

    def cleanup(self) -> None:
        """清理 GPIO 资源，可重复调用."""
        if not self._cleaned_up:
            try:
                GPIO.cleanup()
            except Exception:
                logger.debug("GPIO cleanup 时发生异常", exc_info=True)
            finally:
                self._cleaned_up = True