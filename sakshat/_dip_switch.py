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

"""拨码开关 (2位) 模块.

通过 GPIO 中断检测 SAKS 扩展板上 2 位拨码开关的状态变化，
支持观察者模式回调。当 GPIO 边沿检测不可用时自动降级为轮询模式。

Example:
    >>> from sakshat import DipSwitch2Bit
    >>> dip = DipSwitch2Bit(switch1=21, switch2=26, active_level=GPIO.LOW)
    >>> print(dip.is_on)  # [False, True] 表示第 1 位关、第 2 位开
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


class DipSwitch2Bit:
    """2 位拨码开关控制类.

    通过 GPIO 中断检测拨码开关状态变化，并通过回调通知。
    当边沿检测不可用时自动降级为轮询模式（需调用 poll() 或通过 is_on 属性读取）。

    Attributes:
        is_on: 两位开关的当前状态 [bit1, bit2].
    """

    def __init__(
        self,
        *,
        switch1: int,
        switch2: int,
        active_level: int = GPIO.HIGH,
    ) -> None:
        """初始化拨码开关.

        Args:
            switch1: 第 1 位开关的 GPIO 引脚 (BCM 编号).
            switch2: 第 2 位开关的 GPIO 引脚 (BCM 编号).
            active_level: 有效电平 (拨到 ON 时的电平).

        Raises:
            SAKSValidationError: 引脚编号无效时抛出.
        """
        if switch1 < 0 or switch2 < 0:
            raise SAKSValidationError(
                f"无效的引脚编号: switch1={switch1}, switch2={switch2}"
            )

        self._pins: tuple[int, int] = (switch1, switch2)
        self._active_level: int = active_level

        # 读取初始状态
        if active_level:
            self._status: list[bool] = [
                bool(GPIO.input(switch1)), bool(GPIO.input(switch2))
            ]
        else:
            self._status = [
                not GPIO.input(switch1), not GPIO.input(switch2)
            ]

        # 注册 GPIO 中断（bouncetime=50ms 防抖），失败则降级为轮询模式
        self._use_polling: bool = False
        for pin in self._pins:
            try:
                GPIO.add_event_detect(
                    pin, GPIO.BOTH, callback=self._on_event, bouncetime=50
                )
            except Exception:
                logger.warning(
                    "拨码开关引脚 %d 边沿检测不可用，降级为轮询模式。"
                    "请调用 poll() 或在循环中检查 is_on 属性。",
                    pin,
                )
                self._use_polling = True

        self._observers: list[object] = []
        self._callback: Callable[[list[bool]], None] | None = None

    @property
    def is_on(self) -> list[bool]:
        """返回两位开关的当前状态 [bit1, bit2].

        轮询模式下会自动读取 GPIO 并通知观察者。
        """
        if self._use_polling:
            self.poll()
        return self._status.copy()

    def poll(self) -> bool:
        """轮询 GPIO 引脚状态并通知变更.

        轮询模式下调用此方法以检测状态变化。
        中断模式下无需调用（状态由硬件中断自动更新）。

        Returns:
            True 如果状态发生了变化，False 否则.
        """
        changed = False
        for i, pin in enumerate(self._pins):
            raw = GPIO.input(pin)
            new_status = bool(raw) if self._active_level else not raw
            if new_status != self._status[i]:
                self._status[i] = new_status
                changed = True

        if changed:
            self._notify_observers()
        return changed

    def register(self, observer: object) -> None:
        """注册观察者对象.

        观察者需要实现 ``on_dip_switch_2bit_status_changed(status)`` 方法。

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

    def set_callback(self, callback: Callable[[list[bool]], None]) -> None:
        """设置简化的回调函数.

        Args:
            callback: 回调函数，签名为 ``callback(status: list[bool]) -> None``.

        Example:
            >>> def on_change(status):
            ...     print(f"拨码开关状态: {status}")
            >>> dip.set_callback(on_change)
        """
        self._callback = callback

    def _notify_observers(self) -> None:
        """通知所有观察者状态已变更."""
        for observer in self._observers:
            try:
                observer.on_dip_switch_2bit_status_changed(self._status)
            except Exception:
                logger.error("通知观察者时出错", exc_info=True)
        if self._callback is not None:
            try:
                self._callback(self._status)
            except Exception:
                logger.error("回调函数执行出错", exc_info=True)

    def _on_event(self, channel: int) -> None:
        """GPIO 中断回调.

        Args:
            channel: 触发中断的 GPIO 通道.
        """
        changed = False
        for i, pin in enumerate(self._pins):
            new_val = GPIO.input(pin)
            new_status = bool(new_val) if self._active_level else not new_val
            if new_status != self._status[i]:
                self._status[i] = new_status
                changed = True

        if changed:
            self._notify_observers()

    @override
    def __repr__(self) -> str:
        return (
            f"DipSwitch2Bit(pins={self._pins}, status={self._status})"
        )