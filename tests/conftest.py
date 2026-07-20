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

"""pytest 共享 fixtures 和配置.

为 SAKS SDK 测试套件提供共用的夹具，包括：
- GPIO 引脚编号常量
- 设备实例的快速创建
- 临时文件系统模拟支持
"""

from __future__ import annotations

import pytest

from sakshat._gpio import GPIO


# ── GPIO 常量快捷引用 ──────────────────────────────────────────────

@pytest.fixture
def gpio_high() -> int:
    """GPIO.HIGH 常量 (1)."""
    return GPIO.HIGH


@pytest.fixture
def gpio_low() -> int:
    """GPIO.LOW 常量 (0)."""
    return GPIO.LOW


@pytest.fixture
def gpio_out() -> int:
    """GPIO.OUT 常量 (0)."""
    return GPIO.OUT


@pytest.fixture
def gpio_in() -> int:
    """GPIO.IN 常量 (1)."""
    return GPIO.IN


# ── 引脚常量 ────────────────────────────────────────────────────────

@pytest.fixture
def valid_pin() -> int:
    """一个有效的引脚编号 (12, BUZZER)."""
    return 12


@pytest.fixture
def invalid_pin() -> int:
    """一个无效的引脚编号 (负数)."""
    return -1


@pytest.fixture
def chip_pins() -> dict[str, int]:
    """74HC595 芯片的标准引脚配置."""
    return {"ds": 6, "shcp": 19, "stcp": 13}


@pytest.fixture
def tm1637_pins() -> dict[str, int]:
    """TM1637 芯片的标准引脚配置."""
    return {"di": 25, "clk": 5}


@pytest.fixture
def switch_pins() -> dict[str, int]:
    """拨码开关的标准引脚配置."""
    return {"switch1": 21, "switch2": 26}


@pytest.fixture
def tact_pins() -> list[int]:
    """轻触开关的标准引脚列表."""
    return [20, 16]


# ── DS18B20 温度传感器模拟文件系统 ─────────────────────────────────

@pytest.fixture
def ds18b20_device_dir(tmp_path):
    """创建模拟的 DS18B20 设备目录，返回目录路径.

    模拟 OneWire sysfs 接口，包含一个 w1_slave 文件，
    内容为有效的温度读数 (23.5°C).
    """
    device_path = tmp_path / "28-0000047c31ff"
    device_path.mkdir(parents=True, exist_ok=True)
    slave_file = device_path / "w1_slave"
    slave_file.write_text(
        "71 01 4b 46 7f ff 0c 10 d8 : crc=d8 YES\n"
        "71 01 4b 46 7f ff 0c 10 d8 t=23500\n"
    )

    def _get_device_dir() -> str:
        return str(tmp_path)

    return _get_device_dir


@pytest.fixture
def ds18b20_invalid_device_dir(tmp_path):
    """创建模拟的 DS18B20 设备目录，包含无效的 CRC 读数."""
    device_path = tmp_path / "28-0000047c31ff"
    device_path.mkdir(parents=True, exist_ok=True)
    slave_file = device_path / "w1_slave"
    slave_file.write_text(
        "71 01 4b 46 7f ff 0c 10 d8 : crc=d8 NO\n"
        "71 01 4b 46 7f ff 0c 10 d8 t=23500\n"
    )

    def _get_device_dir() -> str:
        return str(tmp_path)

    return _get_device_dir


@pytest.fixture
def ds18b20_missing_device_dir(tmp_path):
    """创建空的模拟设备目录 (无传感器)."""
    # 目录为空，不创建任何设备子目录

    def _get_device_dir() -> str:
        return str(tmp_path)

    return _get_device_dir