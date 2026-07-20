# PROJECT STRUCTURE

SAKS SDK 项目目录结构说明。

---

## 概述

SAKS SDK 项目包含两个版本的代码库：

- **`sakshat/`** - v2.1.0 现代化包（推荐使用）
- **根目录 `.py` 文件 + `entities/`** - v0.x 旧版代码（保留以兼容现有项目）

---

## 完整目录树

```
SAKS-SDK-master/
├── sakshat/                          # v2.0.0 核心包（推荐）
│   ├── __init__.py                   # 包入口，导出所有公共 API
│   ├── _buzzer.py                    # 蜂鸣器控制模块
│   ├── _core.py                      # SAKSHAT 主控制器
│   ├── _digital_display_tm1637.py    # TM1637 数码管显示模块
│   ├── _dip_switch.py                # 2 位拨码开关模块
│   ├── _ds18b20.py                   # DS18B20 温度传感器模块
│   ├── _exceptions.py                # 统一异常体系
│   ├── _gpio.py                      # GPIO 抽象层
│   ├── _ic_74hc595.py                # 74HC595 移位寄存器驱动
│   ├── _ic_tm1637.py                 # TM1637 数码管驱动芯片
│   ├── _led.py                       # LED 和 LED 阵列控制
│   ├── _led_74hc595.py               # 74HC595 LED 阵列控制
│   ├── _pins.py                      # SAKS 扩展板引脚定义
│   ├── _tact.py                      # 轻触开关模块
│   └── py.typed                      # PEP 561 类型标记文件
│
├── entities/                         # v0.x 旧版实体模块（兼容层）
│   ├── __init__.py                   # 实体模块聚合导出
│   ├── buzzer.py                     # 蜂鸣器（旧版）
│   ├── digital_display.py            # 数码管显示（旧版）
│   ├── digital_display_tm1637.py     # TM1637 数码管（旧版）
│   ├── dip_switch_2bit.py            # 拨码开关（旧版）
│   ├── ds18b20.py                    # 温度传感器（旧版）
│   ├── ic_74hc595.py                 # 74HC595 芯片（旧版）
│   ├── ic_tm1637.py                  # TM1637 芯片（旧版）
│   ├── led.py                        # LED 控制（旧版）
│   ├── led_74hc595.py                # 74HC595 LED（旧版）
│   └── tact.py                       # 轻触开关（旧版）
│
├── examples/                         # 示例代码
│   ├── main.py                       # 示例入口（含环境检查）
│   ├── 01_hello_saks.py              # 基础入门示例
│   ├── 02_digital_display.py         # 数码管显示示例
│   ├── 03_temperature_monitor.py     # 温度监控示例
│   ├── 04_button_interaction.py      # 按键交互示例
│   ├── 05_cpu_temperature_alarm.py   # CPU 温度报警示例
│   ├── 06_full_demo.py              # 综合演示示例
│   ├── 07_segment_deep_dive.py      # 数码管段码深度解析
│   ├── 08_74hc595_deep_dive.py      # 74HC595 芯片深度解析
│   ├── 09_tm1637_deep_dive.py       # TM1637 芯片深度解析
│   ├── 10_buzzer_deep_dive.py       # 蜂鸣器深度解析
│   ├── 11_led_deep_dive.py          # LED 深度解析
│   └── 12_ds18b20_deep_dive.py      # DS18B20 深度解析
│
├── doc/                              # 文档目录
│   ├── README.md                     # 完整项目说明
│   ├── API.md                        # API 参考文档
│   ├── CHANGELOG.md                  # 版本变更日志
│   ├── MIGRATION.md                  # 迁移指南
│   └── PROJECT_STRUCTURE.md          # 本文件 - 项目结构说明
│
├── sakshat.py                        # v0.x 旧版主控制器（兼容层）
├── sakspins.py                       # v0.x 旧版引脚定义（兼容层）
├── pyproject.toml                    # 项目构建和工具配置
├── README.md                         # 项目快速入门（精简版）
├── LICENSE                           # GPL v2.0 许可证
└── .gitignore                        # Git 忽略规则
```

---

## v2.1.0 包结构 (`sakshat/`)

### 设计理念

v2.1.0 采用模块化设计，每个外设对应一个独立的模块文件。内部模块使用下划线前缀（`_`）标记为私有，公共 API 通过 `__init__.py` 统一导出。

### 模块说明

| 文件 | 说明 | 导出类 |
|------|------|--------|
| `__init__.py` | 包入口，聚合导出所有公共 API | `SAKSHAT`, `Buzzer`, `Led`, `LedRow`, `Led74HC595`, `IC74HC595`, `ICTM1637`, `DigitalDisplay`, `DS18B20`, `DipSwitch2Bit`, `Tact`, `TactRow`, `SAKSPins`, 所有异常类 |
| `_core.py` | SAKS 主控制器 | `SAKSHAT` |
| `_buzzer.py` | 蜂鸣器控制 | `Buzzer` |
| `_led.py` | LED 和 LED 阵列 | `Led`, `LedRow` |
| `_led_74hc595.py` | 74HC595 LED 阵列 | `Led74HC595` |
| `_ic_74hc595.py` | 74HC595 芯片驱动 | `IC74HC595`, `IC_74HC595`（别名） |
| `_ic_tm1637.py` | TM1637 芯片驱动 | `ICTM1637`, `IC_TM1637`（别名） |
| `_digital_display_tm1637.py` | 数码管显示 | `DigitalDisplay`, `DigitalDisplayTM1637`（别名） |
| `_ds18b20.py` | 温度传感器 | `DS18B20` |
| `_dip_switch.py` | 拨码开关 | `DipSwitch2Bit` |
| `_tact.py` | 轻触开关 | `Tact`, `TactRow` |
| `_pins.py` | 引脚定义 | `SAKSPins` |
| `_exceptions.py` | 异常体系 | `SAKSError`, `SAKSGPIOError`, `SAKSInitError`, `SAKSHardwareError`, `SAKSTimeoutError`, `SAKSValidationError` |
| `_gpio.py` | GPIO 抽象层 | `GPIO`, `GPIOContext`（内部使用） |
| `py.typed` | PEP 561 标记 | 无（空文件，标记该包提供类型信息） |

### 模块依赖关系

```
__init__.py
├── _core.py (SAKSHAT)
│   ├── _buzzer.py (Buzzer)
│   ├── _led_74hc595.py (Led74HC595)
│   │   └── _ic_74hc595.py (IC74HC595)
│   ├── _digital_display_tm1637.py (DigitalDisplay)
│   │   └── _ic_tm1637.py (ICTM1637)
│   ├── _ds18b20.py (DS18B20)
│   ├── _dip_switch.py (DipSwitch2Bit)
│   ├── _tact.py (Tact, TactRow)
│   ├── _pins.py (SAKSPins)
│   ├── _exceptions.py (异常类)
│   └── _gpio.py (GPIO)
├── _buzzer.py
├── _led.py (Led, LedRow)
├── _led_74hc595.py
├── _ic_74hc595.py
├── _ic_tm1637.py
├── _digital_display_tm1637.py
├── _ds18b20.py
├── _dip_switch.py
├── _tact.py
├── _pins.py
└── _exceptions.py
```

### 关键设计决策

1. **GPIO 抽象层** (`_gpio.py`)：所有模块通过统一的 `GPIO` 对象访问硬件，不再各自重复 `import RPi.GPIO`。当 RPi.GPIO 不可用时，自动降级为模拟模式。

2. **关键字仅参数**：所有构造函数中，除必要的位置参数外，其余参数均标记为 `*` 后的 keyword-only 参数，提高 API 可读性。

3. **向后兼容别名**：新类名（如 `IC74HC595`）与旧类名（如 `IC_74HC595`）共存，旧类名直接赋值为新类名引用。

4. **类型注解**：所有公共 API 均有完整的类型注解，`py.typed` 标记使下游项目可通过 `pyright`/`mypy` 进行类型检查。

---

## v0.x 兼容层

### 说明

以下文件保留在项目中以兼容旧版代码，但**不建议在新项目中使用**：

| 文件/目录 | 说明 |
|----------|------|
| `sakshat.py` | v0.x 主控制器，导入 `entities` 和 `sakspins` |
| `sakspins.py` | v0.x 引脚定义，`SAKSPins` 类 |
| `entities/` | v0.x 外设模块目录 |

### 与 v2.1.0 的主要区别

| 特性 | v0.x (`entities/`) | v2.1.0 (`sakshat/`) |
|------|--------------------|---------------------|
| 导入路径 | `from entities import Buzzer` | `from sakshat import Buzzer` |
| 参数风格 | 位置参数 | 关键字仅参数 |
| 芯片类名 | `IC_74HC595`, `IC_TM1637` | `IC74HC595`, `ICTM1637`（旧名保留） |
| 异常类型 | `ValueError`, `RuntimeError`, `IndexError` | `SAKSValidationError`, `SAKSInitError` 等 |
| 类型注解 | 无 | 完整覆盖 |
| GPIO 管理 | 各模块独立导入 | 统一抽象层 |
| 上下文管理器 | 不支持 | 支持 `with` 语句 |

---

## 示例代码 (`examples/`)

| 文件 | 说明 | 涉及功能 |
|------|------|----------|
| `main.py` | 示例入口，列出所有可用示例，含环境检查 | - |
| `01_hello_saks.py` | 基础入门 | 蜂鸣器、LED 流水灯、LED 交替闪烁 |
| `02_digital_display.py` | 数码管显示 | 数码管数字显示、倒计时 |
| `03_temperature_monitor.py` | 温度监控 | DS18B20 温度读取、数码管显示 |
| `04_button_interaction.py` | 按键交互 | 轻触开关、拨码开关、事件回调 |
| `05_cpu_temperature_alarm.py` | CPU 温度报警 | 系统温度读取、LED 报警、蜂鸣器 |
| `06_full_demo.py` | 综合演示 | 所有外设的综合使用 |
| `07_segment_deep_dive.py` | 数码管段码深度解析 | 段码控制、字母显示、段码编解码 |
| `08_74hc595_deep_dive.py` | 74HC595 芯片深度解析 | 移位寄存器原理、位操作 |
| `09_tm1637_deep_dive.py` | TM1637 芯片深度解析 | 通信协议、原始数据写入 |
| `10_buzzer_deep_dive.py` | 蜂鸣器深度解析 | PWM 与节奏控制 |
| `11_led_deep_dive.py` | LED 深度解析 | 扫描、PWM 与呼吸灯 |
| `12_ds18b20_deep_dive.py` | DS18B20 深度解析 | OneWire 协议与 CRC 校验 |

---

## 配置文件

### `pyproject.toml`

项目构建和开发工具配置文件。

**主要配置项：**

| 配置区域 | 说明 |
|----------|------|
| `[build-system]` | 构建系统配置，使用 `hatchling` |
| `[project]` | 项目元数据：名称 `sakshat`、版本 `2.1.0`、Python 要求 `>=3.13`、依赖 `RPi.GPIO>=0.7.1` |
| `[project.optional-dependencies]` | 开发依赖：`pytest`、`ruff`、`pyright` |
| `[tool.hatch.build.targets.wheel]` | 打包配置，仅包含 `sakshat` 包 |
| `[tool.ruff]` | Ruff linting 配置，目标 Python 3.13，Google 风格 docstring |
| `[tool.pyright]` | Pyright 类型检查配置，strict 模式 |
| `[tool.pytest.ini_options]` | Pytest 测试配置 |

### `.gitignore`

标准 Python 项目 Git 忽略规则，包括：
- `__pycache__/`、`*.pyc` - 字节码文件
- `build/`、`dist/`、`*.egg-info/` - 构建产物
- `.coverage`、`htmlcov/` - 测试覆盖率
- `.idea/` - IDE 配置

---

## 许可证

本项目采用 **GNU General Public License v2.0 (GPL-2.0-only)** 许可证。

详细条款见 [LICENSE](LICENSE) 文件。

---

## 相关文档

- [README.md](README.md) - 完整项目概述和快速开始
- [CHANGELOG.md](CHANGELOG.md) - 版本变更历史
- [MIGRATION.md](MIGRATION.md) - 从 v0.x 迁移到 v2.x 的指南
- [API.md](API.md) - 完整 API 参考文档