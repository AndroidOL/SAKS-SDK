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

"""蜂鸣器控制模块.

提供对 SAKS 扩展板上蜂鸣器的开关控制和节奏蜂鸣功能。
支持有源蜂鸣器 (高电平触发) 和无源蜂鸣器 (低电平触发) 两种模式。

Example:
    >>> from sakshat import Buzzer
    >>> buzzer = Buzzer(pin=12)
    >>> buzzer.beep(0.5)       # 蜂鸣 0.5 秒
    >>> buzzer.beep_pattern(0.02, 0.02, 30)  # 快节奏蜂鸣 30 次
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


class Buzzer:
    """蜂鸣器控制类.

    管理单个蜂鸣器的开关状态，支持单次蜂鸣和节奏蜂鸣模式。

    Attributes:
        is_on: 蜂鸣器当前是否处于开启状态.
        pin: 蜂鸣器连接的 GPIO 引脚编号 (BCM).
    """

    def __init__(self, pin: int, *, active_level: int = GPIO.HIGH) -> None:
        """初始化蜂鸣器.

        Args:
            pin: GPIO 引脚编号 (BCM 编号).
            active_level: 触发电平，GPIO.HIGH 表示高电平触发，
                          GPIO.LOW 表示低电平触发.

        Raises:
            SAKSValidationError: 引脚编号无效时抛出.
        """
        if pin < 0:
            raise SAKSValidationError(f"无效的引脚编号: {pin}")
        self._pin: int = pin
        self._active_level: int = active_level
        self._is_on: bool = False

    @property
    def is_on(self) -> bool:
        """蜂鸣器当前是否处于开启状态."""
        return self._is_on

    @property
    def pin(self) -> int:
        """蜂鸣器连接的 GPIO 引脚编号."""
        return self._pin

    def on(self) -> None:
        """打开蜂鸣器."""
        GPIO.output(self._pin, self._active_level)
        self._is_on = True

    def off(self) -> None:
        """关闭蜂鸣器."""
        GPIO.output(self._pin, not self._active_level)
        self._is_on = False

    def beep(self, seconds: float) -> None:
        """蜂鸣器响指定时长后自动关闭.

        Args:
            seconds: 蜂鸣持续时间 (秒)，必须为正数.

        Raises:
            SAKSValidationError: 当 seconds <= 0 时抛出.
        """
        if seconds <= 0:
            raise SAKSValidationError(f"蜂鸣时长必须为正数，收到: {seconds}")
        self.on()
        time.sleep(seconds)
        self.off()

    def beep_pattern(
        self, on_time: float, off_time: float, repeat: int
    ) -> None:
        """按指定节奏重复蜂鸣.

        Args:
            on_time: 每次蜂鸣持续时间 (秒).
            off_time: 两次蜂鸣之间的间隔时间 (秒).
            repeat: 重复次数，必须为正整数.

        Raises:
            SAKSValidationError: 当参数无效时抛出.

        Example:
            >>> buzzer.beep_pattern(0.02, 0.02, 30)  # 快节奏蜂鸣 30 次
        """
        if on_time <= 0:
            raise SAKSValidationError(f"蜂鸣时间必须为正数，收到: {on_time}")
        if off_time <= 0:
            raise SAKSValidationError(f"间隔时间必须为正数，收到: {off_time}")
        if repeat <= 0:
            raise SAKSValidationError(f"重复次数必须为正整数，收到: {repeat}")
        for _ in range(repeat):
            self.beep(on_time)
            time.sleep(off_time)

    @override
    def __repr__(self) -> str:
        return f"Buzzer(pin={self._pin}, is_on={self._is_on})"