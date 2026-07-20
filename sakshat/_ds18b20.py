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

"""DS18B20 温度传感器模块.

通过 OneWire 接口读取 DS18B20 数字温度传感器的温度数据。

使用前需要确保系统已启用 OneWire 接口。
在树莓派上可通过 raspi-config 启用，或手动加载内核模块:
    sudo modprobe w1-gpio
    sudo modprobe w1-therm

Example:
    >>> from sakshat import DS18B20
    >>> sensor = DS18B20()
    >>> if sensor.is_exist:
    ...     print(f"当前温度: {sensor.temperature:.1f}°C")
"""

from __future__ import annotations

import glob
import logging
import os
import time
import sys

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

from sakshat._exceptions import SAKSHardwareError

logger = logging.getLogger(__name__)


class DS18B20:
    """DS18B20 数字温度传感器控制类.

    通过 sysfs 接口读取 OneWire 总线上的 DS18B20 传感器数据。

    Attributes:
        is_exist: 传感器是否连接可用.
        temperature: 当前温度 (摄氏度)，读取失败返回 -128.0.
    """

    _BASE_DIR: str = "/sys/bus/w1/devices/"
    _DEVICE_PREFIX: str = "28-"
    _MAX_RETRIES: int = 10
    _RETRY_DELAY: float = 0.2
    _INVALID_TEMP: float = -128.0

    def __init__(self, pin: int = 4) -> None:
        """初始化 DS18B20 传感器.

        Args:
            pin: OneWire 数据引脚 (BCM 编号)，默认 GPIO4.

        Note:
            初始化时会自动加载 w1-gpio 和 w1-therm 内核模块。
            如果系统未启用 OneWire，传感器将无法被检测到。
        """
        self._pin: int = pin
        self._load_kernel_modules()

    def _load_kernel_modules(self) -> None:
        """加载 OneWire 内核模块."""
        if not os.path.isdir(self._BASE_DIR):
            try:
                os.system("modprobe w1-gpio 2>/dev/null")  # noqa: S605
                os.system("modprobe w1-therm 2>/dev/null")  # noqa: S605
                time.sleep(0.5)
            except Exception:
                logger.warning("无法加载 OneWire 内核模块", exc_info=True)

    def _get_device_file(self, index: int = 0) -> str | None:
        """获取传感器设备文件路径.

        Args:
            index: 传感器索引 (支持多个传感器时使用).

        Returns:
            设备文件路径，未找到则返回 None.
        """
        pattern = os.path.join(self._BASE_DIR, self._DEVICE_PREFIX + "*")
        devices = sorted(glob.glob(pattern))
        if not devices or index >= len(devices):
            return None
        return os.path.join(devices[index], "w1_slave")

    @property
    def is_exist(self) -> bool:
        """传感器是否已连接并可用."""
        return self._get_device_file() is not None

    @property
    def temperature(self) -> float:
        """获取当前温度值 (摄氏度).

        Returns:
            摄氏温度值，读取失败返回 -128.0.
        """
        return self._read_temp()

    def _read_raw(self, index: int = 0) -> list[str] | None:
        """读取传感器原始数据.

        Args:
            index: 传感器索引.

        Returns:
            原始数据行列表，读取失败返回 None.
        """
        device_file = self._get_device_file(index)
        if not device_file:
            logger.warning("未找到 DS18B20 传感器 (索引: %d)", index)
            return None
        try:
            with open(device_file) as f:
                return f.readlines()
        except OSError as e:
            logger.error("读取 DS18B20 数据失败: %s", e)
            return None

    def _read_temp(self, index: int = 0) -> float:
        """读取并解析温度值 (带重试机制).

        Args:
            index: 传感器索引.

        Returns:
            摄氏温度值，多次重试失败返回 -128.0.
        """
        for _attempt in range(self._MAX_RETRIES):
            lines = self._read_raw(index)
            if not lines:
                return self._INVALID_TEMP

            if lines[0].strip().endswith("YES"):
                temp_pos = lines[1].find("t=")
                if temp_pos != -1:
                    try:
                        temp_raw = lines[1][temp_pos + 2:]
                        return float(temp_raw) / 1000.0
                    except (ValueError, IndexError) as e:
                        logger.error("解析温度值失败: %s", e)
                        return self._INVALID_TEMP

            time.sleep(self._RETRY_DELAY)

        logger.error(
            "DS18B20 温度读取失败: 超过最大重试次数 (%d)", self._MAX_RETRIES
        )
        return self._INVALID_TEMP

    def get_temperature_f(self, index: int = 0) -> float:
        """获取华氏温度.

        Args:
            index: 传感器索引.

        Returns:
            华氏温度值，读取失败返回 -128.0.
        """
        temp_c = self._read_temp(index)
        if temp_c == self._INVALID_TEMP:
            return self._INVALID_TEMP
        return temp_c * 9.0 / 5.0 + 32.0

    @override
    def __repr__(self) -> str:
        return f"DS18B20(pin={self._pin}, is_exist={self.is_exist})"