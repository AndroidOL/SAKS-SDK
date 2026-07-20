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

"""74HC595 移位寄存器驱动模块.

通过三线 SPI-like 接口 (DS/SHCP/STCP) 控制 74HC595 芯片，
实现 8 位并行输出的串行扩展。

引脚说明:
    DS   (SER)  - 串行数据输入
    SHCP (SRCLK) - 移位寄存器时钟
    STCP (RCLK)  - 存储寄存器时钟 (锁存)

Example:
    >>> from sakshat import IC74HC595
    >>> ic = IC74HC595(ds=6, shcp=19, stcp=13)
    >>> ic.set_data(0xFF)  # 所有输出置高
    >>> ic.clear()         # 所有输出清零
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

logger = logging.getLogger(__name__)


class IC74HC595:
    """74HC595 移位寄存器驱动类.

    通过 GPIO 模拟 SPI 时序控制 74HC595 芯片的 8 位并行输出。

    Attributes:
        data: 当前输出的 8 位数据 (0x00-0xFF).
    """

    def __init__(
        self,
        *,
        ds: int,
        shcp: int,
        stcp: int,
        active_level: int = GPIO.HIGH,
    ) -> None:
        """初始化 74HC595 芯片.

        Args:
            ds: 数据输入引脚 (BCM 编号).
            shcp: 移位时钟引脚 (BCM 编号).
            stcp: 存储时钟引脚 (BCM 编号).
            active_level: 有效电平，GPIO.HIGH 或 GPIO.LOW.

        Raises:
            SAKSValidationError: 引脚编号无效时抛出.
        """
        self._pins = {"ds": ds, "shcp": shcp, "stcp": stcp}
        self._active_level = active_level
        self._data: int = 0x00

    @property
    def data(self) -> int:
        """当前锁存的 8 位数据 (0x00-0xFF)."""
        return self._data

    def _pulse_shcp(self) -> None:
        """发送一个移位时钟脉冲."""
        GPIO.output(self._pins["shcp"], not self._active_level)
        GPIO.output(self._pins["shcp"], self._active_level)

    def _pulse_stcp(self) -> None:
        """发送一个存储时钟脉冲，将移位寄存器数据锁存到并行输出."""
        GPIO.output(self._pins["stcp"], not self._active_level)
        GPIO.output(self._pins["stcp"], self._active_level)

    def _write_bit(self, bit: int) -> None:
        """写入一个比特位到移位寄存器.

        Args:
            bit: 位值 (0 或 1).
        """
        GPIO.output(self._pins["ds"], bit)
        self._pulse_shcp()

    def set_data(self, data: int) -> None:
        """写入一个字节并锁存到并行输出.

        Args:
            data: 8 位数据 (0x00-0xFF).

        Raises:
            SAKSValidationError: 数据超出 8 位范围时抛出.
        """
        if not (0 <= data <= 0xFF):
            raise SAKSValidationError(
                f"数据必须在 0x00-0xFF 范围内，收到: {hex(data)}"
            )
        self._data = data
        for i in range(8):
            self._write_bit((data >> i) & 0x01)
        self._pulse_stcp()

    def clear(self) -> None:
        """将所有输出清零."""
        self.set_data(0x00)

    @override
    def __repr__(self) -> str:
        return (
            f"IC74HC595(ds={self._pins['ds']}, shcp={self._pins['shcp']}, "
            f"stcp={self._pins['stcp']}, data=0x{self._data:02X})"
        )


# 向后兼容别名
IC_74HC595 = IC74HC595