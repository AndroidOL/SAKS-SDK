# MIGRATION GUIDE

从 SAKS SDK v0.x 迁移到 v2.0.0 的完整指南。

---

## 目录

- [概述](#概述)
- [Python 版本要求](#python-版本要求)
- [导入路径变更](#导入路径变更)
- [参数风格变更](#参数风格变更)
- [类名变更](#类名变更)
- [方法名变更](#方法名变更)
- [异常处理变更](#异常处理变更)
- [上下文管理器](#上下文管理器)
- [GPIO 抽象层](#gpio-抽象层)
- [完整迁移示例](#完整迁移示例)

---

## 概述

v2.0.0 是 SAKS SDK 的全面重写。核心变更包括：

- 包结构从 `entities/` 迁移到 `sakshat/` 命名空间包
- 所有构造函数参数从位置参数改为关键字仅参数（keyword-only）
- 类名从下划线风格改为驼峰风格（旧名保留为别名）
- 新增统一的异常体系
- 新增上下文管理器支持
- 最低 Python 版本要求提升至 3.13

旧版 `entities/` 目录和根目录下的 `sakshat.py`、`sakspins.py` 文件仍然保留在项目中，可以与现有代码兼容，但**强烈建议迁移到新的 `sakshat/` 包**。

---

## Python 版本要求

| 旧版 (v0.x) | 新版 (v2.0.0) |
|-------------|---------------|
| Python 2.7+ / 3.x | **Python 3.13+** |

v2.0.0 利用了 Python 3.13 的新特性，包括 `override` 装饰器、`from __future__ import annotations`、`type` 语句等。如果你仍在使用较旧版本的 Python，请先升级 Python 环境。

```bash
# 检查 Python 版本
python3 --version
# 必须 >= 3.13
```

---

## 导入路径变更

### 主控制器

| 旧版 (v0.x) | 新版 (v2.0.0) |
|-------------|---------------|
| `from sakshat import SAKSHAT` | `from sakshat import SAKSHAT` |

主控制器导入路径**保持不变**。

### 外设类

| 旧版 (v0.x) | 新版 (v2.0.0) |
|-------------|---------------|
| `from entities import Buzzer` | `from sakshat import Buzzer` |
| `from entities import Led` | `from sakshat import Led` |
| `from entities import LedRow` | `from sakshat import LedRow` |
| `from entities import Led74HC595` | `from sakshat import Led74HC595` |
| `from entities import IC_74HC595` | `from sakshat import IC_74HC595` 或 `from sakshat import IC74HC595` |
| `from entities import IC_TM1637` | `from sakshat import IC_TM1637` 或 `from sakshat import ICTM1637` |
| `from entities import DigitalDisplay` | `from sakshat import DigitalDisplay` |
| `from entities import DigitalDisplayTM1637` | `from sakshat import DigitalDisplayTM1637` 或 `from sakshat import DigitalDisplay` |
| `from entities import DS18B20` | `from sakshat import DS18B20` |
| `from entities import DipSwitch2Bit` | `from sakshat import DipSwitch2Bit` |
| `from entities import Tact` | `from sakshat import Tact` |
| `from entities import TactRow` | `from sakshat import TactRow` |

### 引脚定义

| 旧版 (v0.x) | 新版 (v2.0.0) |
|-------------|---------------|
| `from sakspins import SAKSPins` | `from sakshat import SAKSPins` |

### 异常类

| 旧版 (v0.x) | 新版 (v2.0.0) |
|-------------|---------------|
| （无统一异常体系） | `from sakshat import SAKSError` |

---

## 参数风格变更

### 构造函数：位置参数 -> 关键字仅参数

v2.0.0 中，所有构造函数的第二个及后续参数（除 `pin` 位置参数外）均改为**关键字仅参数**（keyword-only），必须显式指定参数名。

#### Buzzer

```python
# 旧版 (v0.x)
buzzer = Buzzer(12, GPIO.LOW)

# 新版 (v2.0.0)
buzzer = Buzzer(12, active_level=GPIO.LOW)
```

#### Led

```python
# 旧版 (v0.x)
led = Led(6, GPIO.HIGH)

# 新版 (v2.0.0)
led = Led(6, active_level=GPIO.HIGH)
```

#### LedRow

```python
# 旧版 (v0.x)
row = LedRow([6, 19, 13], GPIO.HIGH)

# 新版 (v2.0.0)
row = LedRow([6, 19, 13], active_level=GPIO.HIGH)
```

#### IC74HC595 / IC_74HC595

这是最显著的变更之一。旧版接受一个字典作为第一个参数，新版改为独立的关键字参数。

```python
# 旧版 (v0.x)
ic = IC_74HC595({'ds': 6, 'shcp': 19, 'stcp': 13})

# 新版 (v2.0.0) - 推荐使用新类名
ic = IC74HC595(ds=6, shcp=19, stcp=13)

# 新版 (v2.0.0) - 使用旧类名别名也可以
ic = IC_74HC595(ds=6, shcp=19, stcp=13)
```

#### Led74HC595

```python
# 旧版 (v0.x)
leds = Led74HC595({'ds': 6, 'shcp': 19, 'stcp': 13})

# 新版 (v2.0.0)
leds = Led74HC595(ds=6, shcp=19, stcp=13)
```

#### ICTM1637 / IC_TM1637

```python
# 旧版 (v0.x)
ic = IC_TM1637({'di': 25, 'clk': 5})

# 新版 (v2.0.0) - 推荐使用新类名
ic = ICTM1637(di=25, clk=5)

# 新版 (v2.0.0) - 使用旧类名别名也可以
ic = IC_TM1637(di=25, clk=5)
```

#### DigitalDisplay

```python
# 旧版 (v0.x)
display = DigitalDisplayTM1637({'di': 25, 'clk': 5}, GPIO.HIGH)

# 新版 (v2.0.0)
display = DigitalDisplay(di=25, clk=5, active_level=GPIO.HIGH)
```

#### DipSwitch2Bit

```python
# 旧版 (v0.x)
dip = DipSwitch2Bit([21, 26], GPIO.LOW)

# 新版 (v2.0.0)
dip = DipSwitch2Bit(switch1=21, switch2=26, active_level=GPIO.LOW)
```

#### Tact

```python
# 旧版 (v0.x)
tact = Tact(20, GPIO.LOW)

# 新版 (v2.0.0)
tact = Tact(20, active_level=GPIO.LOW)
```

#### TactRow

```python
# 旧版 (v0.x)
row = TactRow([20, 16], GPIO.LOW)

# 新版 (v2.0.0)
row = TactRow([20, 16], active_level=GPIO.LOW)
```

#### Led.pulse()

```python
# 旧版 (v0.x)
led.pulse(50, 0.01)

# 新版 (v2.0.0)
led.pulse(frequency=50, step_delay=0.01)
```

---

## 类名变更

v2.0.0 引入了新的驼峰风格类名，**旧有下划线类名保留为别名**，因此旧代码不会立即中断。

| 旧类名 (v0.x) | 新类名 (v2.0.0) | 状态 |
|--------------|----------------|------|
| `IC_74HC595` | `IC74HC595` | 旧名保留为别名 |
| `IC_TM1637` | `ICTM1637` | 旧名保留为别名 |
| `DigitalDisplayTM1637` | `DigitalDisplay` | 旧名保留为别名 |

**建议**：在新代码中使用新类名，旧类名将在未来主版本中移除。

```python
# 推荐 (v2.0.0)
from sakshat import IC74HC595, ICTM1637, DigitalDisplay

# 仍然可用 (兼容旧代码)
from sakshat import IC_74HC595, IC_TM1637, DigitalDisplayTM1637
```

---

## 方法名变更

### Buzzer

| 旧版 (v0.x) | 新版 (v2.0.0) | 说明 |
|-------------|---------------|------|
| `beepAction(on_time, off_time, repeat)` | `beep_pattern(on_time, off_time, repeat)` | 旧名已移除 |

### Led

| 旧版 (v0.x) | 新版 (v2.0.0) | 说明 |
|-------------|---------------|------|
| `flashAction(on_time, off_time, repeat)` | `flash_pattern(on_time, off_time, repeat)` | 旧名已移除 |

### ICTM1637 / IC_TM1637

| 旧版 (v0.x) | 新版 (v2.0.0) | 说明 |
|-------------|---------------|------|
| `set_command(command)` | `send_command(command)` | 发送命令字节 |
| `set_data(address, data)` | `write_data(address, data)` | 写入显示数据 |
| `set_bit(bit)` | （不再公开） | 移入内部方法 |
| `set_byte(data)` | （不再公开） | 移入内部方法 |
| `start_bus()` | `start_bus()` | 保持不变 |
| `stop_bus()` | `stop_bus()` | 保持不变 |

### 常量

| 旧版 (v0.x) | 新版 (v2.0.0) | 说明 |
|-------------|---------------|------|
| `IC_TM1637.CMD_DATA_MODE` | `ICTM1637.CMD_DATA_AUTO` | 自动地址增加模式 |
| `IC_TM1637.CMD_DATA_MODE_FIXED` | `ICTM1637.CMD_DATA_FIXED` | 固定地址模式 |

---

## 异常处理变更

### 旧版异常处理

v0.x 使用 Python 内置异常：

```python
# 旧版 (v0.x)
try:
    buzzer = Buzzer(-1, GPIO.LOW)  # 无效引脚
except ValueError as e:
    print(f"错误: {e}")

try:
    row.on_for_index(99)  # 索引越界
except IndexError as e:
    print(f"错误: {e}")
```

### 新版异常处理

v2.0.0 使用统一的 `SAKS*` 异常层次结构：

```python
# 新版 (v2.0.0)
from sakshat import SAKSError, SAKSValidationError, SAKSInitError, SAKSHardwareError

try:
    buzzer = Buzzer(-1, active_level=GPIO.LOW)  # 无效引脚
except SAKSValidationError as e:
    print(f"参数错误: {e}")

try:
    saks = SAKSHAT()  # 初始化可能失败
except SAKSInitError as e:
    print(f"初始化失败: {e}")

try:
    temp = saks.ds18b20.temperature
except SAKSHardwareError as e:
    print(f"硬件错误: {e}")
```

**异常层次结构：**

```
SAKSError
├── SAKSGPIOError       # GPIO 操作失败
├── SAKSInitError        # 外设初始化失败
├── SAKSHardwareError    # 硬件通信异常
├── SAKSTimeoutError     # 操作超时
└── SAKSValidationError  # 参数验证失败
```

**建议**：将 `except ValueError` 和 `except IndexError` 替换为相应的 `SAKS*` 异常类。如果需要在最外层捕获所有 SAKS 异常，使用 `except SAKSError`。

---

## 上下文管理器

v2.0.0 新增了 `SAKSHAT` 的上下文管理器支持，这是管理 GPIO 资源的推荐方式。

### 旧版方式

```python
# 旧版 (v0.x)
from sakshat import SAKSHAT

saks = SAKSHAT()
try:
    saks.buzzer.beep(0.5)
    saks.ledrow.set_row([True, False, True, False, True, False, True, False])
finally:
    saks.cleanup()
```

### 新版方式（推荐）

```python
# 新版 (v2.0.0)
from sakshat import SAKSHAT

with SAKSHAT() as saks:
    saks.buzzer.beep(0.5)
    saks.ledrow.set_row([True, False, True, False, True, False, True, False])
    # with 退出时自动调用 cleanup()
```

---

## GPIO 抽象层

v2.0.0 引入了一个 GPIO 抽象层，在非树莓派环境下（如开发机、CI/CD 环境）自动降级为模拟模式。

### 旧版方式

```python
# 旧版 (v0.x) - 每个模块独立处理 RPi.GPIO 导入
try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
    logger.warning("RPi.GPIO 未安装")
```

### 新版方式

```python
# 新版 (v2.0.0) - 统一抽象层
from sakshat._gpio import GPIO
# GPIO 在非树莓派环境下自动使用 _MockGPIO
```

**对于使用者**：此变更对上层 API 透明，你无需修改代码。当 RPi.GPIO 不可用时，所有 GPIO 操作会静默降级为日志输出，不会抛出异常。

---

## 完整迁移示例

### 迁移前 (v0.x)

```python
#!/usr/bin/env python3
from sakshat import SAKSHAT
from entities import Buzzer
from sakspins import SAKSPins as PINS
import entities
import RPi.GPIO as GPIO

# 创建 SAKS 实例
saks = SAKSHAT()

# 使用蜂鸣器
saks.buzzer.beepAction(0.02, 0.02, 30)

# 使用 LED
saks.ledrow.set_row([True, False, True, False, True, False, True, False])

# 直接创建外设
buzzer = entities.Buzzer(PINS.BUZZER, GPIO.LOW)
ic = entities.IC_74HC595({'ds': 6, 'shcp': 19, 'stcp': 13})

# 清理
saks.cleanup()
```

### 迁移后 (v2.0.0)

```python
#!/usr/bin/env python3
from sakshat import SAKSHAT, Buzzer, SAKSPins, IC74HC595
import RPi.GPIO as GPIO

# 使用 with 语句（推荐）
with SAKSHAT() as saks:
    # 使用蜂鸣器
    saks.buzzer.beep_pattern(0.02, 0.02, 30)

    # 使用 LED
    saks.ledrow.set_row([True, False, True, False, True, False, True, False])

    # 直接创建外设
    buzzer = Buzzer(SAKSPins.BUZZER, active_level=GPIO.LOW)
    ic = IC74HC595(ds=6, shcp=19, stcp=13)

# with 退出时自动清理，无需手动调用 cleanup()
```

### 迁移后 (v2.0.0，兼容旧写法)

如果不想一次性修改太多代码，也可以使用旧类名和兼容写法：

```python
#!/usr/bin/env python3
from sakshat import SAKSHAT, IC_74HC595, IC_TM1637, DigitalDisplayTM1637
import RPi.GPIO as GPIO

saks = SAKSHAT()

# 使用新的 beep_pattern 方法名
saks.buzzer.beep_pattern(0.02, 0.02, 30)

# 使用新的关键字参数风格
ic = IC_74HC595(ds=6, shcp=19, stcp=13)

saks.cleanup()
```

---

## 迁移检查清单

- [ ] 升级 Python 到 3.13 或更高版本
- [ ] 将 `from entities import ...` 改为 `from sakshat import ...`
- [ ] 将 `from sakspins import SAKSPins` 改为 `from sakshat import SAKSPins`
- [ ] 将所有构造函数参数改为关键字仅参数形式
- [ ] 将 `IC_74HC595({'ds':..., 'shcp':..., 'stcp':...})` 改为 `IC74HC595(ds=..., shcp=..., stcp=...)`
- [ ] 将 `IC_TM1637({'di':..., 'clk':...})` 改为 `ICTM1637(di=..., clk=...)`
- [ ] 将 `beepAction` 改为 `beep_pattern`
- [ ] 将 `flashAction` 改为 `flash_pattern`
- [ ] 将 `set_command` 改为 `send_command`（ICTM1637）
- [ ] 将 `set_data` 改为 `write_data`（ICTM1637）
- [ ] 将 `except ValueError` / `except IndexError` 改为相应的 `SAKS*` 异常
- [ ] 考虑使用 `with SAKSHAT() as saks:` 上下文管理器
- [ ] 测试所有功能是否正常工作

---

## 获取帮助

如果在迁移过程中遇到问题，请通过以下方式获取帮助：

- [GitHub Issues](https://github.com/spoonysonny/SAKS-SDK/issues)
- [树莓派实验室论坛](https://www.nxez.com)