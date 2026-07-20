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

"""SAKS 扩展板主控制器.

这是 SAKS SDK 的核心入口模块，负责初始化所有外设并协调它们的工作。
通过 SAKSHAT 类可以一站式访问蜂鸣器、LED、数码管、温度传感器、拨码开关和轻触开关。

Example:
    >>> from sakshat import SAKSHAT
    >>>
    >>> # 使用 with 语句 (推荐，自动释放资源)
    >>> with SAKSHAT() as saks:
    ...     saks.buzzer.beep(0.5)
    ...     saks.ledrow.set_row([True, False, True, False, True, False, True, False])
    ...
    >>> # 或手动清理
    >>> saks = SAKSHAT()
    >>> saks.buzzer.beep(0.5)
    >>> saks.cleanup()
"""

from __future__ import annotations

import atexit
import logging
from types import TracebackType
from typing import Callable
import sys

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

from sakshat._buzzer import Buzzer
from sakshat._digital_display_tm1637 import DigitalDisplay
from sakshat._dip_switch import DipSwitch2Bit
from sakshat._ds18b20 import DS18B20
from sakshat._exceptions import SAKSError
from sakshat._gpio import GPIO
from sakshat._led_74hc595 import Led74HC595
from sakshat._pins import SAKSPins
from sakshat._tact import TactRow

logger = logging.getLogger(__name__)


class SAKSHAT:
    """SAKS 扩展板主控制器.

    初始化后提供对板上所有外设的统一访问入口。

    Attributes:
        buzzer: 蜂鸣器控制.
        ledrow: 8 路 LED 控制 (通过 74HC595).
        ds18b20: 温度传感器.
        digital_display: 4 位数码管.
        dip_switch: 2 位拨码开关.
        tactrow: 2 个轻触开关.
    """

    def __init__(self) -> None:
        """初始化 SAKS 扩展板.

        自动完成以下操作:
        1. 设置 GPIO 模式为 BCM
        2. 初始化所有输出引脚
        3. 创建所有外设实例
        4. 注册输入设备的事件回调
        5. 注册程序退出时的自动清理

        Raises:
            SAKSError: GPIO 初始化失败时抛出.
        """
        self._initialized: bool = False

        # 事件回调
        self.dip_switch_status_changed_handler: Callable[[list[bool]], None] | None = None
        self.tact_event_handler: Callable[[int, bool], None] | None = None

        self._gpio_done: bool = False
        try:
            self._gpio_init()
            self._gpio_done = True
            self._init_peripherals()
            atexit.register(self._auto_cleanup)
            self._initialized = True
            logger.info("SAKS 扩展板初始化完成")
        except Exception as e:
            self.cleanup()
            raise SAKSError(
                f"SAKS 扩展板初始化失败: {e}"
            ) from e

    def _gpio_init(self) -> None:
        """初始化 GPIO 引脚."""
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        # 蜂鸣器
        GPIO.setup(SAKSPins.BUZZER, GPIO.OUT)
        GPIO.output(SAKSPins.BUZZER, GPIO.HIGH)

        # 芯片控制引脚
        chip_pins: list[int] = [
            SAKSPins.IC_TM1637_DI,
            SAKSPins.IC_TM1637_CLK,
            SAKSPins.IC_74HC595_DS,
            SAKSPins.IC_74HC595_SHCP,
            SAKSPins.IC_74HC595_STCP,
        ]
        for p in chip_pins:
            GPIO.setup(p, GPIO.OUT)
            GPIO.output(p, GPIO.LOW)

        # 输入设备引脚 (先输出高电平，再切换为输入上拉)
        input_pins: list[int] = [
            SAKSPins.BUZZER,
            SAKSPins.TACT_RIGHT,
            SAKSPins.TACT_LEFT,
            SAKSPins.DIP_SWITCH_1,
            SAKSPins.DIP_SWITCH_2,
        ]
        for p in input_pins:
            GPIO.setup(p, GPIO.OUT)
            GPIO.output(p, GPIO.HIGH)

        switch_pins: list[int] = [
            SAKSPins.TACT_RIGHT,
            SAKSPins.TACT_LEFT,
            SAKSPins.DIP_SWITCH_1,
            SAKSPins.DIP_SWITCH_2,
        ]
        for p in switch_pins:
            GPIO.setup(p, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def _init_peripherals(self) -> None:
        """初始化所有外设."""
        # 蜂鸣器 - 低电平触发
        self.buzzer: Buzzer = Buzzer(SAKSPins.BUZZER, active_level=GPIO.LOW)

        # 8 路 LED - 通过 74HC595 控制
        self.ledrow: Led74HC595 = Led74HC595(
            ds=SAKSPins.IC_74HC595_DS,
            shcp=SAKSPins.IC_74HC595_SHCP,
            stcp=SAKSPins.IC_74HC595_STCP,
            active_level=GPIO.HIGH,
        )

        # DS18B20 温度传感器
        self.ds18b20: DS18B20 = DS18B20(SAKSPins.DS18B20)

        # 4 位数码管 - 通过 TM1637 控制
        self.digital_display: DigitalDisplay = DigitalDisplay(
            di=SAKSPins.IC_TM1637_DI,
            clk=SAKSPins.IC_TM1637_CLK,
            active_level=GPIO.HIGH,
        )

        # 2 位拨码开关
        self.dip_switch: DipSwitch2Bit = DipSwitch2Bit(
            switch1=SAKSPins.DIP_SWITCH_1,
            switch2=SAKSPins.DIP_SWITCH_2,
            active_level=GPIO.LOW,
        )
        self.dip_switch.register(self)

        # 2 个轻触开关
        self.tactrow: TactRow = TactRow(
            [SAKSPins.TACT_LEFT, SAKSPins.TACT_RIGHT],
            active_level=GPIO.LOW,
        )
        for t in self.tactrow.items:
            t.register(self)

    def on_dip_switch_2bit_status_changed(self, status: list[bool]) -> None:
        """拨码开关状态变更回调 (由 DipSwitch2Bit 调用).

        Args:
            status: 两位开关的当前状态 [bit1, bit2].
        """
        if self.dip_switch_status_changed_handler is not None:
            try:
                self.dip_switch_status_changed_handler(status)
            except Exception:
                logger.error("拨码开关回调函数执行出错", exc_info=True)

    def on_tact_event(self, pin: int, status: bool) -> None:
        """轻触开关事件回调 (由 Tact 调用).

        Args:
            pin: 触发事件的引脚编号.
            status: 当前状态 (True=按下, False=释放).
        """
        if self.tact_event_handler is not None:
            try:
                self.tact_event_handler(pin, status)
            except Exception:
                logger.error("轻触开关回调函数执行出错", exc_info=True)

    def cleanup(self) -> None:
        """清理 GPIO 资源.

        关闭所有输出设备并释放 GPIO 引脚。
        可以重复调用，不会产生副作用。
        """
        if self._initialized:
            try:
                if hasattr(self, "digital_display"):
                    self.digital_display.off()
                if hasattr(self, "ledrow"):
                    self.ledrow.off()
                if hasattr(self, "buzzer"):
                    self.buzzer.off()
            except Exception:
                logger.debug("关闭设备时出错", exc_info=True)
        if self._gpio_done:
            try:
                GPIO.cleanup()
            except Exception:
                logger.debug("GPIO 清理时出错", exc_info=True)
            self._gpio_done = False
        self._initialized = False
        logger.info("SAKS 扩展板资源已清理")

    def _auto_cleanup(self) -> None:
        """程序退出时的自动清理."""
        self.cleanup()

    def __enter__(self) -> SAKSHAT:
        """支持 with 语句."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """退出 with 语句时自动清理."""
        self.cleanup()
        return False

    @override
    def __repr__(self) -> str:
        return f"SAKSHAT(initialized={self._initialized})"