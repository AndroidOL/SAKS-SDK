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

"""LED 控制模块.

提供单个 LED 和 LED 阵列 (LedRow) 的控制功能，包括开关、闪烁、呼吸灯等效果。

Example:
    >>> from sakshat import Led, LedRow
    >>> led = Led(pin=6)
    >>> led.on()
    >>> led.flash(0.5)
    >>> row = LedRow([6, 19, 13])
    >>> row.set_row([True, False, True])
"""

from __future__ import annotations

import time
import logging
from threading import Event, Thread
import sys

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

from sakshat._exceptions import SAKSValidationError
from sakshat._gpio import GPIO

logger = logging.getLogger(__name__)


class Led:
    """单个 LED 控制类.

    支持基本的开关操作、闪烁和 PWM 呼吸灯效果。

    Attributes:
        is_on: LED 当前是否亮起.
        pin: LED 连接的 GPIO 引脚编号.
    """

    def __init__(self, pin: int, *, active_level: int = GPIO.HIGH) -> None:
        """初始化 LED.

        Args:
            pin: GPIO 引脚编号 (BCM 编号).
            active_level: 有效电平，GPIO.HIGH 或 GPIO.LOW.

        Raises:
            SAKSValidationError: 引脚编号无效时抛出.
        """
        if pin < 0:
            raise SAKSValidationError(f"无效的引脚编号: {pin}")
        self._pin: int = pin
        self._active_level: int = active_level
        self._is_on: bool = False
        self._pwm: object | None = None
        self._pulse_active: bool = False
        self._pulse_stop: Event = Event()

    @property
    def is_on(self) -> bool:
        """LED 当前是否亮起."""
        return self._is_on

    @property
    def pin(self) -> int:
        """LED 连接的 GPIO 引脚编号."""
        return self._pin

    def on(self) -> None:
        """打开 LED."""
        if not self._pulse_active:
            GPIO.output(self._pin, self._active_level)
            self._is_on = True

    def off(self) -> None:
        """关闭 LED，同时停止呼吸灯效果."""
        if self._pulse_active:
            self._stop_pulse()
        GPIO.output(self._pin, not self._active_level)
        self._is_on = False

    def flash(self, seconds: float) -> None:
        """让 LED 亮起指定时间后自动熄灭.

        Args:
            seconds: 持续时间 (秒)，必须为正数.

        Raises:
            SAKSValidationError: 当 seconds <= 0 时抛出.
        """
        if seconds <= 0:
            raise SAKSValidationError(f"持续时间必须为正数，收到: {seconds}")
        self.on()
        time.sleep(seconds)
        self.off()

    def flash_pattern(
        self, on_time: float, off_time: float, repeat: int
    ) -> None:
        """按指定节奏重复闪烁.

        Args:
            on_time: 每次亮起时间 (秒).
            off_time: 两次亮起之间的间隔 (秒).
            repeat: 重复次数.

        Raises:
            SAKSValidationError: 当参数无效时抛出.
        """
        if on_time <= 0:
            raise SAKSValidationError(f"亮起时间必须为正数，收到: {on_time}")
        if off_time <= 0:
            raise SAKSValidationError(f"间隔时间必须为正数，收到: {off_time}")
        if repeat <= 0:
            raise SAKSValidationError(f"重复次数必须为正整数，收到: {repeat}")
        for _ in range(repeat):
            self.flash(on_time)
            time.sleep(off_time)

    def pulse(self, *, frequency: int = 50, step_delay: float = 0.01) -> None:
        """启动呼吸灯效果 (LED 亮度渐变).

        使用 PWM 实现 LED 亮度从暗到亮再到暗的循环渐变。

        Args:
            frequency: PWM 频率 (Hz)，默认 50Hz.
            step_delay: 每步渐变延时 (秒)，值越小渐变越快.

        Note:
            调用 :meth:`off` 可以停止呼吸灯效果。
        """
        if self._pwm is None:
            self._pwm = GPIO.PWM(self._pin, frequency)
        else:
            self._pwm.ChangeFrequency(frequency)

        self._pwm.start(0)
        self._pulse_active = True
        self._is_on = True
        self._pulse_stop.clear()

        def _pulse_worker() -> None:
            while self._pulse_active and not self._pulse_stop.is_set():
                try:
                    for duty in range(0, 101, 1):
                        if self._pulse_stop.is_set():
                            return
                        self._pwm.ChangeDutyCycle(duty)
                        time.sleep(step_delay)
                    time.sleep(1)
                    for duty in range(100, -1, -1):
                        if self._pulse_stop.is_set():
                            return
                        self._pwm.ChangeDutyCycle(duty)
                        time.sleep(step_delay)
                except Exception:
                    logger.debug("呼吸灯线程异常", exc_info=True)
                    time.sleep(0.1)

        try:
            thread = Thread(target=_pulse_worker, daemon=True)
            thread.start()
        except Exception:
            logger.error("无法启动呼吸灯线程", exc_info=True)

    def _stop_pulse(self) -> None:
        """停止呼吸灯效果."""
        self._pulse_active = False
        self._pulse_stop.set()
        if self._pwm is not None:
            try:
                self._pwm.stop()
            except Exception:
                logger.debug("PWM stop 异常", exc_info=True)
            time.sleep(0.05)

    @override
    def __repr__(self) -> str:
        return f"Led(pin={self._pin}, is_on={self._is_on})"


class LedRow:
    """LED 阵列控制类.

    管理多个 LED 的集合，支持批量操作和按索引单独控制。

    Attributes:
        items: 所有 LED 实例的列表.
        row_status: 每颗 LED 的当前状态列表.
    """

    def __init__(
        self, pins: list[int], *, active_level: int = GPIO.HIGH
    ) -> None:
        """初始化 LED 阵列.

        Args:
            pins: GPIO 引脚编号列表.
            active_level: 有效电平.

        Raises:
            SAKSValidationError: 当 pins 为空时抛出.
        """
        if not pins:
            raise SAKSValidationError("引脚列表不能为空")
        self._pins: list[int] = list(pins)
        self._active_level: int = active_level
        self._leds: list[Led] = [Led(p, active_level=active_level) for p in pins]

    def is_on(self, index: int) -> bool:
        """查询指定索引的 LED 状态.

        Args:
            index: LED 索引 (从 0 开始).

        Returns:
            LED 是否亮起，索引越界返回 False.
        """
        if index < 0 or index >= len(self._leds):
            return False
        return self._leds[index].is_on

    @property
    def row_status(self) -> list[bool]:
        """返回所有 LED 的当前状态列表."""
        return [led.is_on for led in self._leds]

    @property
    def items(self) -> list[Led]:
        """返回所有 LED 实例的列表."""
        return self._leds

    def on(self) -> None:
        """打开所有 LED."""
        for led in self._leds:
            led.on()

    def off(self) -> None:
        """关闭所有 LED."""
        for led in self._leds:
            led.off()

    def on_for_index(self, index: int) -> None:
        """打开指定索引的 LED.

        Args:
            index: LED 索引 (从 0 开始).

        Raises:
            SAKSValidationError: 索引越界时抛出.
        """
        if index < 0 or index >= len(self._leds):
            raise SAKSValidationError(
                f"LED 索引 {index} 越界，有效范围: 0-{len(self._leds) - 1}"
            )
        self._leds[index].on()

    def off_for_index(self, index: int) -> None:
        """关闭指定索引的 LED.

        Args:
            index: LED 索引 (从 0 开始).

        Raises:
            SAKSValidationError: 索引越界时抛出.
        """
        if index < 0 or index >= len(self._leds):
            raise SAKSValidationError(
                f"LED 索引 {index} 越界，有效范围: 0-{len(self._leds) - 1}"
            )
        self._leds[index].off()

    def set_row(self, status: list[bool | None]) -> None:
        """按状态列表设置 LED 阵列.

        Args:
            status: 布尔值列表，True=亮，False=灭，None=保持当前状态不变.

        Example:
            >>> row.set_row([True, False, True, None, None, None, None, True])
        """
        for i, s in enumerate(status):
            if i >= len(self._leds):
                break
            if s is None:
                continue
            if s:
                self._leds[i].on()
            else:
                self._leds[i].off()

    @override
    def __repr__(self) -> str:
        return f"LedRow(pins={self._pins}, status={self.row_status})"