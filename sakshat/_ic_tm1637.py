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

"""TM1637 数码管驱动芯片模块.

通过两线接口 (DIO/CLK) 模拟 I2C-like 协议控制 TM1637 芯片，
用于驱动 4 位共阳极数码管。

通信时序:
    1. start_bus()  - 起始条件: CLK 高时 DIO 从高变低
    2. write_byte()  - 发送 8 位数据 (LSB 优先)
    3. stop_bus()   - 停止条件: CLK 高时 DIO 从低变高

Example:
    >>> from sakshat import ICTM1637
    >>> ic = ICTM1637(di=25, clk=5)
    >>> ic.send_command(0x8F)  # 开启显示
    >>> ic.write_data(0xC0, 0x3F)  # 在第 0 位显示数字 0
"""

from __future__ import annotations

import time
import logging
import sys

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

from sakshat._exceptions import SAKSValidationError
from sakshat._gpio import GPIO

logger = logging.getLogger(__name__)


class ICTM1637:
    """TM1637 数码管驱动芯片控制类.

    通过 GPIO 模拟 TM1637 的串行通信协议，控制 4 位数码管显示。

    Attributes:
        ADDRESSES: 4 位数码管的显示地址 (0xC0-0xC3).
        CMD_DISPLAY_ON: 开启显示命令 (最大亮度).
        CMD_DISPLAY_OFF: 关闭显示命令.
    """

    # 显示地址
    ADDRESSES: tuple[int, ...] = (0xC0, 0xC1, 0xC2, 0xC3)

    # 命令常量
    CMD_DATA_AUTO: int = 0x40      # 自动地址增加模式
    CMD_DATA_FIXED: int = 0x44     # 固定地址模式
    CMD_DISPLAY_OFF: int = 0x80    # 关闭显示
    CMD_DISPLAY_ON: int = 0x8F     # 开启显示 (最大亮度)

    def __init__(
        self,
        *,
        di: int,
        clk: int,
        active_level: int = GPIO.HIGH,
    ) -> None:
        """初始化 TM1637 芯片.

        Args:
            di: 数据输入/输出引脚 (BCM 编号).
            clk: 时钟引脚 (BCM 编号).
            active_level: 有效电平，GPIO.HIGH 或 GPIO.LOW.
        """
        self._pins = {"di": di, "clk": clk}
        self._active_level = active_level
        self._bus_delay_sec: float = 0.001

    def _bus_delay(self) -> None:
        """总线延时，确保信号稳定."""
        time.sleep(self._bus_delay_sec)

    def start_bus(self) -> None:
        """发送起始条件: CLK 高时 DIO 从高变低."""
        GPIO.output(self._pins["clk"], self._active_level)
        GPIO.output(self._pins["di"], self._active_level)
        self._bus_delay()
        GPIO.output(self._pins["di"], not self._active_level)
        self._bus_delay()
        GPIO.output(self._pins["clk"], not self._active_level)
        self._bus_delay()

    def stop_bus(self) -> None:
        """发送停止条件: CLK 高时 DIO 从低变高."""
        GPIO.output(self._pins["clk"], not self._active_level)
        self._bus_delay()
        GPIO.output(self._pins["di"], not self._active_level)
        self._bus_delay()
        GPIO.output(self._pins["clk"], self._active_level)
        self._bus_delay()
        GPIO.output(self._pins["di"], self._active_level)
        self._bus_delay()

    def _write_bit(self, bit: int) -> None:
        """写入一个比特位.

        Args:
            bit: 位值 (0 或 1).
        """
        GPIO.output(self._pins["clk"], not self._active_level)
        self._bus_delay()
        GPIO.output(self._pins["di"], bit)
        self._bus_delay()
        GPIO.output(self._pins["clk"], self._active_level)
        self._bus_delay()

    def write_byte(self, data: int) -> None:
        """写入一个字节 (LSB 优先).

        Args:
            data: 8 位数据 (0x00-0xFF).

        Raises:
            SAKSValidationError: 数据超出范围时抛出.
        """
        if not (0 <= data <= 0xFF):
            raise SAKSValidationError(
                f"数据必须在 0x00-0xFF 范围内，收到: {hex(data)}"
            )
        for i in range(8):
            self._write_bit((data >> i) & 0x01)
        # ACK 时钟位
        GPIO.output(self._pins["clk"], not self._active_level)
        self._bus_delay()
        GPIO.output(self._pins["di"], self._active_level)
        self._bus_delay()
        GPIO.output(self._pins["clk"], self._active_level)
        self._bus_delay()

    def send_command(self, command: int) -> None:
        """发送命令字节.

        Args:
            command: 命令码 (如 CMD_DISPLAY_ON 开启显示).
        """
        self.start_bus()
        self.write_byte(command)
        self.stop_bus()

    def write_data(self, address: int, data: int) -> None:
        """向指定地址写入数据.

        Args:
            address: 显示地址 (0xC0-0xC3 对应 4 个数码管).
            data: 段码数据 (控制数码管各段的亮灭).

        Raises:
            SAKSValidationError: 地址或数据无效时抛出.
        """
        if not (0xC0 <= address <= 0xC3):
            raise SAKSValidationError(
                f"地址必须在 0xC0-0xC3 范围内，收到: {hex(address)}"
            )
        if not (0 <= data <= 0xFF):
            raise SAKSValidationError(
                f"数据必须在 0x00-0xFF 范围内，收到: {hex(data)}"
            )
        self.start_bus()
        self.write_byte(address)
        self.write_byte(data)
        self.stop_bus()

    def clear(self) -> None:
        """关闭显示."""
        self.send_command(self.CMD_DISPLAY_OFF)

    @override
    def __repr__(self) -> str:
        return (
            f"ICTM1637(di={self._pins['di']}, clk={self._pins['clk']})"
        )


# 向后兼容别名
IC_TM1637 = ICTM1637