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

"""74HC595 LED 阵列控制模块.

通过 74HC595 移位寄存器芯片控制 8 路 LED。
相比直接 GPIO 控制的 LedRow，此模块使用串行方式节省引脚。

Example:
    >>> from sakshat import Led74HC595
    >>> leds = Led74HC595(ds=6, shcp=19, stcp=13)
    >>> leds.set_row([True, False, True, False, True, False, True, False])
"""

from __future__ import annotations

import logging
import sys

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

from sakshat._exceptions import SAKSValidationError
from sakshat._gpio import GPIO
from sakshat._ic_74hc595 import IC74HC595

logger = logging.getLogger(__name__)


class Led74HC595:
    """通过 74HC595 芯片控制的 8 路 LED 阵列.

    使用移位寄存器方式，仅需 3 个 GPIO 引脚即可控制 8 个 LED。

    Attributes:
        ic: 底层 74HC595 芯片实例.
        row_status: 8 个 LED 的当前状态.
    """

    def __init__(
        self,
        *,
        ds: int,
        shcp: int,
        stcp: int,
        active_level: int = GPIO.HIGH,
    ) -> None:
        """初始化 74HC595 LED 阵列.

        Args:
            ds: 数据输入引脚 (BCM 编号).
            shcp: 移位时钟引脚 (BCM 编号).
            stcp: 存储时钟引脚 (BCM 编号).
            active_level: 有效电平.
        """
        self._ic: IC74HC595 = IC74HC595(
            ds=ds, shcp=shcp, stcp=stcp, active_level=active_level
        )

    @property
    def ic(self) -> IC74HC595:
        """底层 74HC595 芯片实例."""
        return self._ic

    def is_on(self, index: int) -> bool:
        """查询指定 LED 的状态.

        Args:
            index: LED 索引 (0-7).

        Returns:
            LED 是否亮起，越界返回 False.
        """
        if index < 0 or index >= 8:
            return False
        return bool(self._ic.data >> index & 0x01)

    @property
    def row_status(self) -> list[bool]:
        """返回 8 个 LED 的当前状态列表."""
        return [bool(self._ic.data >> i & 0x01) for i in range(8)]

    def on(self) -> None:
        """打开全部 8 个 LED."""
        self._ic.set_data(0xFF)

    def off(self) -> None:
        """关闭全部 8 个 LED."""
        self._ic.clear()

    def on_for_index(self, index: int) -> None:
        """打开指定索引的 LED.

        Args:
            index: LED 索引 (0-7).

        Raises:
            SAKSValidationError: 索引越界时抛出.
        """
        if index < 0 or index >= 8:
            raise SAKSValidationError(
                f"LED 索引 {index} 越界，有效范围: 0-7"
            )
        self._ic.set_data(self._ic.data | (0x01 << index))

    def off_for_index(self, index: int) -> None:
        """关闭指定索引的 LED.

        Args:
            index: LED 索引 (0-7).

        Raises:
            SAKSValidationError: 索引越界时抛出.
        """
        if index < 0 or index >= 8:
            raise SAKSValidationError(
                f"LED 索引 {index} 越界，有效范围: 0-7"
            )
        self._ic.set_data(self._ic.data & ~(0x01 << index))

    def set_row(self, status: list[bool | None]) -> None:
        """按状态列表设置 8 路 LED.

        Args:
            status: 最多 8 个元素的列表，True=亮，False=灭，None=不变.

        Example:
            >>> leds.set_row([True, False, True, False, True, False, True, False])
        """
        for i, s in enumerate(status):
            if i >= 8:
                break
            if s is None:
                continue
            if s:
                self.on_for_index(i)
            else:
                self.off_for_index(i)

    @override
    def __repr__(self) -> str:
        return f"Led74HC595(data=0x{self._ic.data:02X})"