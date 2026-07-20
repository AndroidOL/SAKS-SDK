# Copyright (c) 2015-2026 NXEZ.COM.
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

"""轻触开关 (Tact) 模块.

通过 GPIO 中断检测 SAKS 扩展板上轻触开关的按压/释放事件，
支持观察者模式和回调函数两种通知方式。
当 GPIO 边沿检测不可用时自动降级为轮询模式。

Example:
    >>> from sakshat import Tact, TactRow
    >>> tact = Tact(pin=20, active_level=GPIO.LOW)
    >>> print(tact.is_on)  # True 表示按下
    >>> row = TactRow([20, 16], active_level=GPIO.LOW)
"""

from __future__ import annotations

import logging
from typing import Callable
import sys

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

from sakshat._exceptions import SAKSValidationError
from sakshat._gpio import GPIO

logger = logging.getLogger(__name__)


class Tact:
    """单个轻触开关控制类.

    通过 GPIO 中断检测按压/释放事件。
    当边沿检测不可用时自动降级为轮询模式。

    Attributes:
        is_on: 开关当前是否被按下.
        pin: 开关连接的 GPIO 引脚编号.
    """

    def __init__(
        self, pin: int, *, active_level: int = GPIO.HIGH
    ) -> None:
        """初始化轻触开关.

        Args:
            pin: GPIO 引脚编号 (BCM 编号).
            active_level: 按下时的有效电平.

        Raises:
            SAKSValidationError: 引脚编号无效时抛出.
        """
        if pin < 0:
            raise SAKSValidationError(f"无效的引脚编号: {pin}")

        self._pin: int = pin
        self._active_level: int = active_level

        if active_level:
            self._status: bool = bool(GPIO.input(pin))
        else:
            self._status = not GPIO.input(pin)

        # 注册 GPIO 中断（bouncetime=1ms 防抖），失败则降级为轮询模式
        self._use_polling: bool = False
        try:
            GPIO.add_event_detect(
                pin, GPIO.BOTH, callback=self._on_event, bouncetime=1
            )
        except RuntimeError:
            logger.warning(
                "轻触开关引脚 %d 边沿检测不可用，降级为轮询模式。"
                "请通过 is_on 属性读取状态。",
                pin,
            )
            self._use_polling = True

        self._observers: list[object] = []
        self._callback: Callable[[int, bool], None] | None = None

    @property
    def is_on(self) -> bool:
        """开关当前是否被按下.

        轮询模式下直接读取 GPIO 引脚。
        """
        if self._use_polling:
            raw = GPIO.input(self._pin)
            new_status = bool(raw) if self._active_level else not raw
            if new_status != self._status:
                self._status = new_status
                self._notify_observers(new_status)
            return new_status

        if self._active_level:
            if self._status != GPIO.input(self._pin):
                self._status = GPIO.input(self._pin)
        else:
            if self._status == GPIO.input(self._pin):
                self._status = not GPIO.input(self._pin)
        return self._status

    @property
    def pin(self) -> int:
        """开关连接的 GPIO 引脚编号."""
        return self._pin

    def register(self, observer: object) -> None:
        """注册观察者对象.

        观察者需要实现 ``on_tact_event(pin, status)`` 方法。

        Args:
            observer: 观察者对象.
        """
        if observer not in self._observers:
            self._observers.append(observer)

    def deregister(self, observer: object) -> None:
        """移除观察者对象.

        Args:
            observer: 要移除的观察者对象.
        """
        if observer in self._observers:
            self._observers.remove(observer)

    def set_callback(
        self, callback: Callable[[int, bool], None]
    ) -> None:
        """设置简化的回调函数.

        Args:
            callback: 回调函数，签名为 ``callback(pin: int, status: bool) -> None``.

        Example:
            >>> def on_press(pin, status):
            ...     print(f"引脚 {pin} 状态: {'按下' if status else '释放'}")
            >>> tact.set_callback(on_press)
        """
        self._callback = callback

    def _notify_observers(self, status: bool) -> None:
        """通知所有观察者."""
        for observer in self._observers:
            try:
                observer.on_tact_event(self._pin, status)
            except Exception:
                logger.error("通知观察者时出错", exc_info=True)
        if self._callback is not None:
            try:
                self._callback(self._pin, status)
            except Exception:
                logger.error("回调函数执行出错", exc_info=True)

    def _on_event(self, channel: int) -> None:
        """GPIO 中断回调.

        Args:
            channel: 触发中断的 GPIO 通道.
        """
        new_status = (
            bool(GPIO.input(channel))
            if self._active_level
            else not GPIO.input(channel)
        )
        if new_status != self._status:
            self._status = new_status
            self._notify_observers(new_status)

    @override
    def __repr__(self) -> str:
        return f"Tact(pin={self._pin}, is_on={self._status})"


class TactRow:
    """轻触开关阵列控制类.

    管理多个轻触开关的集合，支持批量状态查询。

    Attributes:
        items: 所有轻触开关实例的列表.
        row_status: 每个开关的当前状态列表.
    """

    def __init__(
        self, pins: list[int], *, active_level: int = GPIO.HIGH
    ) -> None:
        """初始化轻触开关阵列.

        Args:
            pins: GPIO 引脚编号列表.
            active_level: 按下时的有效电平.

        Raises:
            SAKSValidationError: 当 pins 为空时抛出.
        """
        if not pins:
            raise SAKSValidationError("引脚列表不能为空")

        self._pins: list[int] = list(pins)
        self._active_level: int = active_level
        self._tacts: list[Tact] = [
            Tact(p, active_level=active_level) for p in pins
        ]

    def is_on(self, index: int) -> bool:
        """查询指定开关状态.

        Args:
            index: 开关索引.

        Returns:
            是否按下，越界返回 False.
        """
        if index < 0 or index >= len(self._tacts):
            return False
        return self._tacts[index].is_on

    @property
    def row_status(self) -> list[bool]:
        """返回所有开关的当前状态列表."""
        return [t.is_on for t in self._tacts]

    @property
    def items(self) -> list[Tact]:
        """返回所有开关实例的列表."""
        return self._tacts

    @override
    def __repr__(self) -> str:
        return f"TactRow(pins={self._pins}, status={self.row_status})"