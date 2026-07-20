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

"""SAKS (Swiss Army Knife Shield) SDK for Raspberry Pi.

SAKS SDK 是树莓派瑞士军刀扩展板的 Python 驱动库，
提供对板上所有外设的面向对象封装。

Quick Start:
    >>> from sakshat import SAKSHAT
    >>> with SAKSHAT() as saks:
    ...     saks.buzzer.beep(0.5)
    ...     saks.digital_display.show("12.34")
"""

from __future__ import annotations

from sakshat._buzzer import Buzzer
from sakshat._core import SAKSHAT
from sakshat._digital_display_tm1637 import DigitalDisplay, DigitalDisplayTM1637
from sakshat._dip_switch import DipSwitch2Bit
from sakshat._ds18b20 import DS18B20
from sakshat._exceptions import (
    SAKSError,
    SAKSGPIOError,
    SAKSHardwareError,
    SAKSInitError,
    SAKSTimeoutError,
    SAKSValidationError,
)
from sakshat._ic_74hc595 import IC74HC595, IC_74HC595
from sakshat._ic_tm1637 import ICTM1637, IC_TM1637
from sakshat._led import Led, LedRow
from sakshat._led_74hc595 import Led74HC595
from sakshat._pins import SAKSPins
from sakshat._tact import Tact, TactRow

__version__ = "2.3.0"
__author__ = "Spoony"
__license__ = "GPL-2.0-only"

__all__ = [
    # 主控制器
    "SAKSHAT",
    # 引脚定义
    "SAKSPins",
    # 芯片驱动
    "IC74HC595",
    "IC_74HC595",
    "ICTM1637",
    "IC_TM1637",
    # 外设
    "Buzzer",
    "Led",
    "LedRow",
    "Led74HC595",
    "DigitalDisplay",
    "DigitalDisplayTM1637",
    "DS18B20",
    "DipSwitch2Bit",
    "Tact",
    "TactRow",
    # 异常
    "SAKSError",
    "SAKSGPIOError",
    "SAKSHardwareError",
    "SAKSInitError",
    "SAKSTimeoutError",
    "SAKSValidationError",
]