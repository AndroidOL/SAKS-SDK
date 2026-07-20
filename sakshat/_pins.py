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

"""SAKS 扩展板引脚定义 (BCM 编号).

本模块使用 :class:`enum.IntEnum` 定义 SAKS 扩展板上所有外设对应的
GPIO 引脚编号，所有编号均为 BCM (Broadcom) 编号方式。

分组说明:
    - 74HC595 组: 控制 8 路 LED 的移位寄存器芯片
    - TM1637 组:  控制 4 位数码管的显示驱动芯片
    - 输入设备组:  蜂鸣器、轻触开关、拨码开关
    - 扩展接口组:  红外、DS18B20 温度传感器、UART、I2C

Example:
    >>> from sakshat import SAKSPins
    >>> GPIO.setup(SAKSPins.BUZZER, GPIO.OUT)
    >>> SAKSPins.validate(12)
    True
"""

from __future__ import annotations

from enum import IntEnum


class SAKSPins(IntEnum):
    """SAKS 扩展板 GPIO 引脚定义 (BCM 编号).

    所有常量均为整数，可直接用于 RPi.GPIO 库的引脚操作。
    """

    # ---- 74HC595 移位寄存器 (控制 8 路 LED) ----
    IC_74HC595_DS: int = 6   # 数据输入 (SER)
    IC_74HC595_SHCP: int = 19  # 移位时钟 (SRCLK)
    IC_74HC595_STCP: int = 13  # 存储时钟 (RCLK)

    # ---- TM1637 数码管驱动芯片 ----
    IC_TM1637_DI: int = 25  # 数据输入/输出
    IC_TM1637_CLK: int = 5   # 时钟

    # ---- 蜂鸣器 ----
    BUZZER: int = 12

    # ---- 轻触开关 ----
    TACT_RIGHT: int = 20  # 右侧轻触开关
    TACT_LEFT: int = 16  # 左侧轻触开关

    # ---- 拨码开关 (2位) ----
    DIP_SWITCH_1: int = 21  # 拨码开关第 1 位
    DIP_SWITCH_2: int = 26  # 拨码开关第 2 位

    # ---- 扩展接口 ----
    IR_SENDER: int = 17  # 红外发射
    IR_RECEIVER: int = 9   # 红外接收
    DS18B20: int = 4   # DS18B20 温度传感器 (OneWire)
    UART_TXD: int = 14  # UART 发送
    UART_RXD: int = 15  # UART 接收
    I2C_SDA: int = 2   # I2C 数据线
    I2C_SCL: int = 3   # I2C 时钟线

    @classmethod
    def validate(cls, pin: int) -> bool:
        """验证给定的引脚编号是否在 SAKS 定义的引脚范围内.

        Args:
            pin: 要验证的引脚编号.

        Returns:
            True 表示引脚有效，False 表示无效.
        """
        return pin in cls._value2member_map_

    @classmethod
    def list_all(cls) -> dict[int, str]:
        """列出所有已定义的引脚及其用途.

        Returns:
            {引脚编号: 引脚名称} 的映射字典.
        """
        return {member.value: member.name for member in cls}