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

"""DS18B20 温度传感器测试 (模拟文件系统)."""

from __future__ import annotations

import os

import pytest

from sakshat import DS18B20


class TestDS18B20Init:
    """测试 DS18B20 初始化."""

    def test_init_default_pin(self) -> None:
        """默认引脚初始化."""
        sensor = DS18B20()
        assert sensor is not None

    def test_init_with_custom_pin(self) -> None:
        """自定义引脚初始化."""
        sensor = DS18B20(pin=17)
        assert sensor is not None

    def test_init_pin_zero(self) -> None:
        """引脚 0 初始化."""
        sensor = DS18B20(pin=0)
        assert sensor is not None


class TestDS18B20IsExist:
    """测试 DS18B20.is_exist 属性."""

    def test_is_exist_no_device(self, ds18b20_missing_device_dir, monkeypatch) -> None:
        """无设备时 is_exist 返回 False."""
        monkeypatch.setattr(DS18B20, "_BASE_DIR", ds18b20_missing_device_dir())
        sensor = DS18B20()
        assert sensor.is_exist is False

    def test_is_exist_with_device(self, ds18b20_device_dir, monkeypatch) -> None:
        """有设备时 is_exist 返回 True."""
        monkeypatch.setattr(DS18B20, "_BASE_DIR", ds18b20_device_dir())
        sensor = DS18B20()
        assert sensor.is_exist is True


class TestDS18B20Temperature:
    """测试 DS18B20.temperature 属性."""

    def test_temperature_valid_reading(self, ds18b20_device_dir, monkeypatch) -> None:
        """有效温度读数返回正确值."""
        monkeypatch.setattr(DS18B20, "_BASE_DIR", ds18b20_device_dir())
        sensor = DS18B20()
        temp = sensor.temperature
        assert temp == pytest.approx(23.5, rel=0.01)

    def test_temperature_no_device(self, ds18b20_missing_device_dir, monkeypatch) -> None:
        """无设备时返回 -128.0."""
        monkeypatch.setattr(DS18B20, "_BASE_DIR", ds18b20_missing_device_dir())
        sensor = DS18B20()
        temp = sensor.temperature
        assert temp == -128.0

    def test_temperature_invalid_crc(self, ds18b20_invalid_device_dir, monkeypatch) -> None:
        """无效 CRC 时返回 -128.0."""
        monkeypatch.setattr(DS18B20, "_BASE_DIR", ds18b20_invalid_device_dir())
        sensor = DS18B20()
        temp = sensor.temperature
        assert temp == -128.0

    def test_temperature_type(self, ds18b20_device_dir, monkeypatch) -> None:
        """温度值类型为 float."""
        monkeypatch.setattr(DS18B20, "_BASE_DIR", ds18b20_device_dir())
        sensor = DS18B20()
        temp = sensor.temperature
        assert isinstance(temp, float)


class TestDS18B20GetTemperatureF:
    """测试 DS18B20.get_temperature_f() 方法."""

    def test_fahrenheit_valid(self, ds18b20_device_dir, monkeypatch) -> None:
        """有效读数时华氏温度正确."""
        monkeypatch.setattr(DS18B20, "_BASE_DIR", ds18b20_device_dir())
        sensor = DS18B20()
        temp_f = sensor.get_temperature_f()
        expected = 23.5 * 9.0 / 5.0 + 32.0
        assert temp_f == pytest.approx(expected, rel=0.01)

    def test_fahrenheit_no_device(self, ds18b20_missing_device_dir, monkeypatch) -> None:
        """无设备时华氏温度返回 -128.0."""
        monkeypatch.setattr(DS18B20, "_BASE_DIR", ds18b20_missing_device_dir())
        sensor = DS18B20()
        temp_f = sensor.get_temperature_f()
        assert temp_f == -128.0


class TestDS18B20TemperatureEdgeCases:
    """测试温度读取的边缘情况."""

    def test_negative_temperature(self, tmp_path, monkeypatch) -> None:
        """负温度读数."""
        device_path = tmp_path / "28-0000047c31ff"
        device_path.mkdir(parents=True, exist_ok=True)
        slave_file = device_path / "w1_slave"
        slave_file.write_text(
            "a1 00 4b 46 7f ff 0c 10 d8 : crc=d8 YES\n"
            "a1 00 4b 46 7f ff 0c 10 d8 t=-5500\n"
        )
        monkeypatch.setattr(DS18B20, "_BASE_DIR", str(tmp_path))
        sensor = DS18B20()
        temp = sensor.temperature
        assert temp == pytest.approx(-5.5, rel=0.01)

    def test_zero_temperature(self, tmp_path, monkeypatch) -> None:
        """零度温度读数."""
        device_path = tmp_path / "28-0000047c31ff"
        device_path.mkdir(parents=True, exist_ok=True)
        slave_file = device_path / "w1_slave"
        slave_file.write_text(
            "71 01 4b 46 7f ff 0c 10 d8 : crc=d8 YES\n"
            "71 01 4b 46 7f ff 0c 10 d8 t=0\n"
        )
        monkeypatch.setattr(DS18B20, "_BASE_DIR", str(tmp_path))
        sensor = DS18B20()
        temp = sensor.temperature
        assert temp == 0.0

    def test_high_temperature(self, tmp_path, monkeypatch) -> None:
        """高温读数."""
        device_path = tmp_path / "28-0000047c31ff"
        device_path.mkdir(parents=True, exist_ok=True)
        slave_file = device_path / "w1_slave"
        slave_file.write_text(
            "71 01 4b 46 7f ff 0c 10 d8 : crc=d8 YES\n"
            "71 01 4b 46 7f ff 0c 10 d8 t=85000\n"
        )
        monkeypatch.setattr(DS18B20, "_BASE_DIR", str(tmp_path))
        sensor = DS18B20()
        temp = sensor.temperature
        assert temp == pytest.approx(85.0, rel=0.01)

    def test_malformed_temperature(self, tmp_path, monkeypatch) -> None:
        """格式错误的温度数据返回 -128.0."""
        device_path = tmp_path / "28-0000047c31ff"
        device_path.mkdir(parents=True, exist_ok=True)
        slave_file = device_path / "w1_slave"
        slave_file.write_text(
            "71 01 4b 46 7f ff 0c 10 d8 : crc=d8 YES\n"
            "71 01 4b 46 7f ff 0c 10 d8 t=invalid\n"
        )
        monkeypatch.setattr(DS18B20, "_BASE_DIR", str(tmp_path))
        sensor = DS18B20()
        temp = sensor.temperature
        assert temp == -128.0

    def test_missing_t_line(self, tmp_path, monkeypatch) -> None:
        """缺少 t= 行时返回 -128.0."""
        device_path = tmp_path / "28-0000047c31ff"
        device_path.mkdir(parents=True, exist_ok=True)
        slave_file = device_path / "w1_slave"
        slave_file.write_text(
            "71 01 4b 46 7f ff 0c 10 d8 : crc=d8 YES\n"
            "71 01 4b 46 7f ff 0c 10 d8\n"
        )
        monkeypatch.setattr(DS18B20, "_BASE_DIR", str(tmp_path))
        sensor = DS18B20()
        temp = sensor.temperature
        assert temp == -128.0


class TestDS18B20Repr:
    """测试 DS18B20 __repr__."""

    def test_repr_no_device(self, ds18b20_missing_device_dir, monkeypatch) -> None:
        """无设备时的 __repr__."""
        monkeypatch.setattr(DS18B20, "_BASE_DIR", ds18b20_missing_device_dir())
        sensor = DS18B20()
        r = repr(sensor)
        assert "DS18B20" in r
        assert "is_exist=False" in r

    def test_repr_with_device(self, ds18b20_device_dir, monkeypatch) -> None:
        """有设备时的 __repr__."""
        monkeypatch.setattr(DS18B20, "_BASE_DIR", ds18b20_device_dir())
        sensor = DS18B20()
        r = repr(sensor)
        assert "is_exist=True" in r

    def test_repr_shows_pin(self, ds18b20_missing_device_dir, monkeypatch) -> None:
        """__repr__ 显示引脚编号."""
        monkeypatch.setattr(DS18B20, "_BASE_DIR", ds18b20_missing_device_dir())
        sensor = DS18B20(pin=4)
        r = repr(sensor)
        assert "pin=4" in r


class TestDS18B20MultipleSensors:
    """测试多传感器场景."""

    def test_multiple_devices_first_sensor(self, tmp_path, monkeypatch) -> None:
        """多个传感器时读取第一个."""
        # 创建两个传感器设备
        for dev_id in ["28-0000047c31ff", "28-0000047c32ff"]:
            device_path = tmp_path / dev_id
            device_path.mkdir(parents=True, exist_ok=True)
            slave_file = device_path / "w1_slave"
            if dev_id == "28-0000047c31ff":
                slave_file.write_text(
                    "71 01 4b 46 7f ff 0c 10 d8 : crc=d8 YES\n"
                    "71 01 4b 46 7f ff 0c 10 d8 t=23500\n"
                )
            else:
                slave_file.write_text(
                    "71 01 4b 46 7f ff 0c 10 d8 : crc=d8 YES\n"
                    "71 01 4b 46 7f ff 0c 10 d8 t=30000\n"
                )
        monkeypatch.setattr(DS18B20, "_BASE_DIR", str(tmp_path))
        sensor = DS18B20()
        assert sensor.is_exist is True
        temp = sensor.temperature
        assert temp == pytest.approx(23.5, rel=0.01)

    def test_get_temperature_f_with_index(self, tmp_path, monkeypatch) -> None:
        """通过索引读取第二个传感器."""
        for dev_id in ["28-0000047c31ff", "28-0000047c32ff"]:
            device_path = tmp_path / dev_id
            device_path.mkdir(parents=True, exist_ok=True)
            slave_file = device_path / "w1_slave"
            if dev_id == "28-0000047c31ff":
                slave_file.write_text(
                    "71 01 4b 46 7f ff 0c 10 d8 : crc=d8 YES\n"
                    "71 01 4b 46 7f ff 0c 10 d8 t=23500\n"
                )
            else:
                slave_file.write_text(
                    "71 01 4b 46 7f ff 0c 10 d8 : crc=d8 YES\n"
                    "71 01 4b 46 7f ff 0c 10 d8 t=30000\n"
                )
        monkeypatch.setattr(DS18B20, "_BASE_DIR", str(tmp_path))
        sensor = DS18B20()
        temp_f = sensor.get_temperature_f(index=1)
        expected = 30.0 * 9.0 / 5.0 + 32.0
        assert temp_f == pytest.approx(expected, rel=0.01)

    def test_oob_index_returns_invalid(self, ds18b20_device_dir, monkeypatch) -> None:
        """越界索引返回 -128.0."""
        monkeypatch.setattr(DS18B20, "_BASE_DIR", ds18b20_device_dir())
        sensor = DS18B20()
        temp = sensor.temperature  # 这里使用默认 index=0
        # 索引 5 超出范围应返回 -128.0
        temp_f = sensor.get_temperature_f(index=5)
        assert temp_f == -128.0