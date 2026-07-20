# API Reference

SAKS SDK v2.3.0 完整 API 参考文档。

---

## 目录

- [主控制器](#主控制器)
  - [SAKSHAT](#sakshat)
- [引脚定义](#引脚定义)
  - [SAKSPins](#sakspins)
- [蜂鸣器](#蜂鸣器)
  - [Buzzer](#buzzer)
- [LED 控制](#led-控制)
  - [Led](#led)
  - [LedRow](#ledrow)
  - [Led74HC595](#led74hc595)
- [芯片驱动](#芯片驱动)
  - [IC74HC595](#ic74hc595)
  - [ICTM1637](#ictm1637)
- [数码管显示](#数码管显示)
  - [DigitalDisplay](#digitaldisplay)
- [温度传感器](#温度传感器)
  - [DS18B20](#ds18b20)
- [输入设备](#输入设备)
  - [DipSwitch2Bit](#dipswitch2bit)
  - [Tact](#tact)
  - [TactRow](#tactrow)
- [异常体系](#异常体系)
  - [SAKSError](#sakserror)
  - [SAKSGPIOError](#saksgpioerror)
  - [SAKSInitError](#saksiniterror)
  - [SAKSHardwareError](#sakshardwareerror)
  - [SAKSTimeoutError](#sakstimeouterror)
  - [SAKSValidationError](#saksvalidationerror)
- [GPIO 抽象层](#gpio-抽象层)
  - [GPIO](#gpio)
  - [GPIOContext](#gpiocontext)

---

## 主控制器

### SAKSHAT

SAKS 扩展板主控制器，初始化后提供对板上所有外设的统一访问入口。

**导入：**

```python
from sakshat import SAKSHAT
```

**构造函数：**

```python
SAKSHAT()
```

初始化 SAKS 扩展板。自动完成以下操作：
1. 设置 GPIO 模式为 BCM
2. 初始化所有输出引脚
3. 创建所有外设实例
4. 注册输入设备的事件回调
5. 注册程序退出时的自动清理（通过 `atexit`）

**Raises：**

- `SAKSError`：GPIO 初始化或外设创建失败时抛出。底层异常会被屏蔽，统一包装为 SAKSError。

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `buzzer` | `Buzzer` | 蜂鸣器控制 |
| `ledrow` | `Led74HC595` | 8 路 LED 控制（通过 74HC595） |
| `ds18b20` | `DS18B20` | 温度传感器 |
| `digital_display` | `DigitalDisplay` | 4 位数码管 |
| `dip_switch` | `DipSwitch2Bit` | 2 位拨码开关 |
| `tactrow` | `TactRow` | 2 个轻触开关 |

**回调属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `dip_switch_status_changed_handler` | `Callable[[list[bool]], None] \| None` | 拨码开关状态变更回调函数，签名为 `handler(status: list[bool]) -> None` |
| `tact_event_handler` | `Callable[[int, bool], None] \| None` | 轻触开关事件回调函数，签名为 `handler(pin: int, status: bool) -> None` |

**方法：**

| 方法 | 说明 |
|------|------|
| `cleanup()` | 清理 GPIO 资源，关闭所有输出设备并释放 GPIO 引脚。可重复调用，不会产生副作用。 |
| `__enter__()` | 支持 `with` 语句，返回 `self`。 |
| `__exit__(exc_type, exc_val, exc_tb) -> bool` | 退出 `with` 语句时自动调用 `cleanup()`。返回 `False` 表示不抑制异常。 |

**回调方法（由外设调用，不应直接调用）：**

| 方法 | 说明 |
|------|------|
| `on_dip_switch_2bit_status_changed(status: list[bool])` | 拨码开关状态变更回调，由 `DipSwitch2Bit` 调用。如果设置了 `dip_switch_status_changed_handler`，则转发调用。 |
| `on_tact_event(pin: int, status: bool)` | 轻触开关事件回调，由 `Tact` 调用。如果设置了 `tact_event_handler`，则转发调用。 |

**代码示例：**

```python
# 基本使用
from sakshat import SAKSHAT

saks = SAKSHAT()
saks.buzzer.beep(0.5)
saks.ledrow.set_row([True, False, True, False, True, False, True, False])
temp = saks.ds18b20.temperature
saks.digital_display.show("12.34")
saks.cleanup()

# 使用 with 语句（推荐）
with SAKSHAT() as saks:
    saks.buzzer.beep(0.5)
    saks.ledrow.set_row([True, False, True, False, True, False, True, False])
    # with 退出时自动清理

# 事件回调
def on_dip_switch(status):
    print(f"拨码开关: {status}")

def on_tact(pin, status):
    print(f"引脚 {pin} {'按下' if status else '释放'}")

saks = SAKSHAT()
saks.dip_switch_status_changed_handler = on_dip_switch
saks.tact_event_handler = on_tact
```

---

## 引脚定义

### SAKSPins

SAKS 扩展板 GPIO 引脚定义（BCM 编号）。继承自 `enum.IntEnum`，所有常量均为整数，可直接用于 RPi.GPIO 库的引脚操作。

**导入：**

```python
from sakshat import SAKSPins
```

**引脚常量：**

**74HC595 移位寄存器（控制 8 路 LED）：**

| 常量 | 值 | 说明 |
|------|-----|------|
| `IC_74HC595_DS` | 6 | 数据输入（SER） |
| `IC_74HC595_SHCP` | 19 | 移位时钟（SRCLK） |
| `IC_74HC595_STCP` | 13 | 存储时钟（RCLK） |

**TM1637 数码管驱动芯片：**

| 常量 | 值 | 说明 |
|------|-----|------|
| `IC_TM1637_DI` | 25 | 数据输入/输出 |
| `IC_TM1637_CLK` | 5 | 时钟 |

**蜂鸣器：**

| 常量 | 值 | 说明 |
|------|-----|------|
| `BUZZER` | 12 | 蜂鸣器 |

**轻触开关：**

| 常量 | 值 | 说明 |
|------|-----|------|
| `TACT_LEFT` | 16 | 左侧轻触开关 |
| `TACT_RIGHT` | 20 | 右侧轻触开关 |

**拨码开关（2 位）：**

| 常量 | 值 | 说明 |
|------|-----|------|
| `DIP_SWITCH_1` | 21 | 拨码开关第 1 位 |
| `DIP_SWITCH_2` | 26 | 拨码开关第 2 位 |

**扩展接口：**

| 常量 | 值 | 说明 |
|------|-----|------|
| `IR_SENDER` | 17 | 红外发射 |
| `IR_RECEIVER` | 9 | 红外接收 |
| `DS18B20` | 4 | DS18B20 温度传感器（OneWire） |
| `UART_TXD` | 14 | UART 发送 |
| `UART_RXD` | 15 | UART 接收 |
| `I2C_SDA` | 2 | I2C 数据线 |
| `I2C_SCL` | 3 | I2C 时钟线 |

**类方法：**

| 方法 | 说明 |
|------|------|
| `validate(pin: int) -> bool` | 验证给定的引脚编号是否在 SAKS 定义的引脚范围内。返回 `True` 表示有效，`False` 表示无效。 |
| `list_all() -> dict[int, str]` | 列出所有已定义的引脚及其用途。返回 `{引脚编号: 引脚名称}` 的映射字典。 |

**代码示例：**

```python
from sakshat import SAKSPins
import RPi.GPIO as GPIO

# 直接使用引脚常量
GPIO.setup(SAKSPins.BUZZER, GPIO.OUT)

# 验证引脚
SAKSPins.validate(12)   # True
SAKSPins.validate(99)   # False

# 列出所有引脚
all_pins = SAKSPins.list_all()
# {6: 'IC_74HC595_DS', 19: 'IC_74HC595_SHCP', ...}
```

---

## 蜂鸣器

### Buzzer

蜂鸣器控制类。管理单个蜂鸣器的开关状态，支持单次蜂鸣和节奏蜂鸣模式。

**导入：**

```python
from sakshat import Buzzer
```

**构造函数：**

```python
Buzzer(pin: int, *, active_level: int = GPIO.HIGH)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pin` | `int` | （必填） | GPIO 引脚编号（BCM 编号） |
| `active_level` | `int` | `GPIO.HIGH` | 触发电平。`GPIO.HIGH` 表示高电平触发，`GPIO.LOW` 表示低电平触发 |

**Raises：**

- `SAKSValidationError`：引脚编号无效时抛出。

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `is_on` | `bool` | 蜂鸣器当前是否处于开启状态（只读） |
| `pin` | `int` | 蜂鸣器连接的 GPIO 引脚编号（只读） |

**方法：**

| 方法 | 说明 |
|------|------|
| `on()` | 打开蜂鸣器 |
| `off()` | 关闭蜂鸣器 |
| `beep(seconds: float)` | 蜂鸣器响指定时长后自动关闭 |
| `beep_pattern(on_time: float, off_time: float, repeat: int)` | 按指定节奏重复蜂鸣 |

**`beep(seconds)`：**

蜂鸣器响指定时长后自动关闭。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `seconds` | `float` | 蜂鸣持续时间（秒），必须为正数 |

**Raises：**

- `SAKSValidationError`：当 `seconds <= 0` 时抛出。

**`beep_pattern(on_time, off_time, repeat)`：**

按指定节奏重复蜂鸣。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `on_time` | `float` | 每次蜂鸣持续时间（秒），必须为正数 |
| `off_time` | `float` | 两次蜂鸣之间的间隔时间（秒），必须为正数 |
| `repeat` | `int` | 重复次数，必须为正整数 |

**Raises：**

- `SAKSValidationError`：当参数无效时抛出。

**代码示例：**

```python
from sakshat import Buzzer
import RPi.GPIO as GPIO

# 创建蜂鸣器（低电平触发，SAKS 默认配置）
buzzer = Buzzer(12, active_level=GPIO.LOW)

# 开关控制
buzzer.on()
buzzer.off()

# 单次蜂鸣
buzzer.beep(0.5)  # 蜂鸣 0.5 秒

# 节奏蜂鸣
buzzer.beep_pattern(0.02, 0.02, 30)  # 快节奏蜂鸣 30 次

# 查看状态
print(buzzer.is_on)  # False
print(buzzer.pin)    # 12
```

---

## LED 控制

### Led

单个 LED 控制类。支持基本的开关操作、闪烁和 PWM 呼吸灯效果。

**导入：**

```python
from sakshat import Led
```

**构造函数：**

```python
Led(pin: int, *, active_level: int = GPIO.HIGH)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pin` | `int` | （必填） | GPIO 引脚编号（BCM 编号） |
| `active_level` | `int` | `GPIO.HIGH` | 有效电平，`GPIO.HIGH` 或 `GPIO.LOW` |

**Raises：**

- `SAKSValidationError`：引脚编号无效时抛出。

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `is_on` | `bool` | LED 当前是否亮起（只读） |
| `pin` | `int` | LED 连接的 GPIO 引脚编号（只读） |

**方法：**

| 方法 | 说明 |
|------|------|
| `on()` | 打开 LED |
| `off()` | 关闭 LED，同时停止呼吸灯效果 |
| `flash(seconds: float)` | 让 LED 亮起指定时间后自动熄灭 |
| `flash_pattern(on_time: float, off_time: float, repeat: int)` | 按指定节奏重复闪烁 |
| `pulse(*, frequency: int = 50, step_delay: float = 0.01)` | 启动呼吸灯效果（LED 亮度渐变） |

**`flash(seconds)`：**

让 LED 亮起指定时间后自动熄灭。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `seconds` | `float` | 持续时间（秒），必须为正数 |

**Raises：**

- `SAKSValidationError`：当 `seconds <= 0` 时抛出。

**`flash_pattern(on_time, off_time, repeat)`：**

按指定节奏重复闪烁。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `on_time` | `float` | 每次亮起时间（秒），必须为正数 |
| `off_time` | `float` | 两次亮起之间的间隔（秒），必须为正数 |
| `repeat` | `int` | 重复次数，必须为正整数 |

**Raises：**

- `SAKSValidationError`：当参数无效时抛出。

**`pulse(*, frequency=50, step_delay=0.01)`：**

启动呼吸灯效果（LED 亮度渐变）。使用 PWM 实现 LED 亮度从暗到亮再到暗的循环渐变。调用 `off()` 可以停止呼吸灯效果。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `frequency` | `int` | `50` | PWM 频率（Hz） |
| `step_delay` | `float` | `0.01` | 每步渐变延时（秒），值越小渐变越快 |

**注意：** 所有参数均为关键字仅参数。

**代码示例：**

```python
from sakshat import Led
import RPi.GPIO as GPIO

led = Led(6, active_level=GPIO.HIGH)

# 开关控制
led.on()
led.off()

# 闪烁
led.flash(0.5)  # 亮 0.5 秒后熄灭

# 节奏闪烁
led.flash_pattern(0.02, 0.02, 30)  # 快速闪烁 30 次

# 呼吸灯
led.pulse(frequency=50, step_delay=0.01)
# ... 一段时间后停止
led.off()
```

---

### LedRow

LED 阵列控制类。管理多个 LED 的集合，支持批量操作和按索引单独控制。

**导入：**

```python
from sakshat import LedRow
```

**构造函数：**

```python
LedRow(pins: list[int], *, active_level: int = GPIO.HIGH)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pins` | `list[int]` | （必填） | GPIO 引脚编号列表 |
| `active_level` | `int` | `GPIO.HIGH` | 有效电平 |

**Raises：**

- `SAKSValidationError`：当 `pins` 为空时抛出。

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `items` | `list[Led]` | 所有 LED 实例的列表（只读） |
| `row_status` | `list[bool]` | 每颗 LED 的当前状态列表（只读） |

**方法：**

| 方法 | 说明 |
|------|------|
| `is_on(index: int) -> bool` | 查询指定索引的 LED 状态。索引越界返回 `False` |
| `on()` | 打开所有 LED |
| `off()` | 关闭所有 LED |
| `on_for_index(index: int)` | 打开指定索引的 LED |
| `off_for_index(index: int)` | 关闭指定索引的 LED |
| `set_row(status: list[bool \| None])` | 按状态列表设置 LED 阵列 |

**`set_row(status)`：**

按状态列表设置 LED 阵列。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `status` | `list[bool \| None]` | 布尔值列表，`True` = 亮，`False` = 灭，`None` = 保持当前状态不变 |

**`on_for_index(index)` / `off_for_index(index)`：**

**Raises：**

- `SAKSValidationError`：索引越界时抛出。

**代码示例：**

```python
from sakshat import LedRow

row = LedRow([6, 19, 13], active_level=GPIO.HIGH)

# 批量操作
row.on()   # 全部打开
row.off()  # 全部关闭

# 按索引操作
row.on_for_index(0)   # 打开第 1 个 LED
row.off_for_index(2)  # 关闭第 3 个 LED

# 按数组设置
row.set_row([True, False, True, None, None, None, None, True])
# 第 1、3、8 个 LED 亮，第 2 个灭，其余不变

# 查询状态
print(row.is_on(0))     # 第 1 个 LED 是否亮
print(row.row_status)   # [True, False, True, ...]
```

---

### Led74HC595

通过 74HC595 芯片控制的 8 路 LED 阵列。使用移位寄存器方式，仅需 3 个 GPIO 引脚即可控制 8 个 LED。

**导入：**

```python
from sakshat import Led74HC595
```

**构造函数：**

```python
Led74HC595(*, ds: int, shcp: int, stcp: int, active_level: int = GPIO.HIGH)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ds` | `int` | （必填） | 数据输入引脚（BCM 编号） |
| `shcp` | `int` | （必填） | 移位时钟引脚（BCM 编号） |
| `stcp` | `int` | （必填） | 存储时钟引脚（BCM 编号） |
| `active_level` | `int` | `GPIO.HIGH` | 有效电平 |

**注意：** 所有参数均为关键字仅参数。

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `ic` | `IC74HC595` | 底层 74HC595 芯片实例（只读） |
| `row_status` | `list[bool]` | 8 个 LED 的当前状态列表（只读） |

**方法：**

| 方法 | 说明 |
|------|------|
| `is_on(index: int) -> bool` | 查询指定 LED 的状态。索引越界返回 `False` |
| `on()` | 打开全部 8 个 LED |
| `off()` | 关闭全部 8 个 LED |
| `on_for_index(index: int)` | 打开指定索引的 LED（0-7） |
| `off_for_index(index: int)` | 关闭指定索引的 LED（0-7） |
| `set_row(status: list[bool \| None])` | 按状态列表设置 8 路 LED |

**`on_for_index(index)` / `off_for_index(index)`：**

**Raises：**

- `SAKSValidationError`：索引越界时抛出。

**`set_row(status)`：**

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `status` | `list[bool \| None]` | 最多 8 个元素的列表，`True` = 亮，`False` = 灭，`None` = 不变 |

**代码示例：**

```python
from sakshat import Led74HC595

# SAKS 默认引脚配置
leds = Led74HC595(ds=6, shcp=19, stcp=13)

# 交替亮灭
leds.set_row([True, False, True, False, True, False, True, False])

# 流水灯
for i in range(8):
    leds.on_for_index(i)
    time.sleep(0.1)
    leds.off_for_index(i)

# 全部开关
leds.on()
leds.off()

# 查询状态
print(leds.is_on(0))     # 第 1 个 LED 是否亮
print(leds.row_status)   # [True, False, True, ...]
```

---

## 芯片驱动

### IC74HC595

74HC595 移位寄存器驱动类。通过 GPIO 模拟 SPI 时序控制 74HC595 芯片的 8 位并行输出。

**别名：** `IC_74HC595`（向后兼容）

**导入：**

```python
from sakshat import IC74HC595
# 或
from sakshat import IC_74HC595  # 向后兼容别名
```

**引脚说明：**
- `DS` (SER) - 串行数据输入
- `SHCP` (SRCLK) - 移位寄存器时钟
- `STCP` (RCLK) - 存储寄存器时钟（锁存）

**构造函数：**

```python
IC74HC595(*, ds: int, shcp: int, stcp: int, active_level: int = GPIO.HIGH)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ds` | `int` | （必填） | 数据输入引脚（BCM 编号） |
| `shcp` | `int` | （必填） | 移位时钟引脚（BCM 编号） |
| `stcp` | `int` | （必填） | 存储时钟引脚（BCM 编号） |
| `active_level` | `int` | `GPIO.HIGH` | 有效电平，`GPIO.HIGH` 或 `GPIO.LOW` |

**注意：** 所有参数均为关键字仅参数。

**Raises：**

- `SAKSValidationError`：引脚编号无效时抛出。

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `data` | `int` | 当前锁存的 8 位数据（`0x00`-`0xFF`）（只读） |

**方法：**

| 方法 | 说明 |
|------|------|
| `set_data(data: int)` | 写入一个字节并锁存到并行输出 |
| `clear()` | 将所有输出清零（等同于 `set_data(0x00)`） |

**`set_data(data)`：**

写入一个字节并锁存到并行输出。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `data` | `int` | 8 位数据（`0x00`-`0xFF`） |

**Raises：**

- `SAKSValidationError`：数据超出 8 位范围时抛出。

**代码示例：**

```python
from sakshat import IC74HC595

# 初始化（SAKS 默认引脚）
ic = IC74HC595(ds=6, shcp=19, stcp=13)

# 写入数据
ic.set_data(0xFF)  # 所有输出置高（8 个 LED 全亮）
ic.set_data(0x00)  # 所有输出置低（8 个 LED 全灭）
ic.set_data(0xAA)  # 交替亮灭（10101010）

# 清零
ic.clear()  # 等同于 set_data(0x00)

# 查看当前状态
print(hex(ic.data))  # 0x00
```

---

### ICTM1637

TM1637 数码管驱动芯片控制类。通过 GPIO 模拟 TM1637 的串行通信协议，控制 4 位数码管显示。

**别名：** `IC_TM1637`（向后兼容）

**导入：**

```python
from sakshat import ICTM1637
# 或
from sakshat import IC_TM1637  # 向后兼容别名
```

**通信时序：**
1. `start_bus()` - 起始条件：CLK 高时 DIO 从高变低
2. `write_byte()` - 发送 8 位数据（LSB 优先）
3. `stop_bus()` - 停止条件：CLK 高时 DIO 从低变高

**构造函数：**

```python
ICTM1637(*, di: int, clk: int, active_level: int = GPIO.HIGH)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `di` | `int` | （必填） | 数据输入/输出引脚（BCM 编号） |
| `clk` | `int` | （必填） | 时钟引脚（BCM 编号） |
| `active_level` | `int` | `GPIO.HIGH` | 有效电平，`GPIO.HIGH` 或 `GPIO.LOW` |

**注意：** 所有参数均为关键字仅参数。

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `ADDRESSES` | `tuple[int, ...]` | 4 位数码管的显示地址：`(0xC0, 0xC1, 0xC2, 0xC3)`（类属性） |
| `CMD_DATA_AUTO` | `int` | 自动地址增加模式命令：`0x40`（类属性） |
| `CMD_DATA_FIXED` | `int` | 固定地址模式命令：`0x44`（类属性） |
| `CMD_DISPLAY_OFF` | `int` | 关闭显示命令：`0x80`（类属性） |
| `CMD_DISPLAY_ON` | `int` | 开启显示命令（最大亮度）：`0x8F`（类属性） |

**方法：**

| 方法 | 说明 |
|------|------|
| `start_bus()` | 发送起始条件 |
| `stop_bus()` | 发送停止条件 |
| `write_byte(data: int)` | 写入一个字节（LSB 优先） |
| `send_command(command: int)` | 发送命令字节 |
| `write_data(address: int, data: int)` | 向指定地址写入数据 |
| `clear()` | 关闭显示 |

**`write_byte(data)`：**

写入一个字节，LSB 优先。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `data` | `int` | 8 位数据（`0x00`-`0xFF`） |

**Raises：**

- `SAKSValidationError`：数据超出范围时抛出。

**`send_command(command)`：**

发送命令字节。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `command` | `int` | 命令码（如 `CMD_DISPLAY_ON` 开启显示） |

**`write_data(address, data)`：**

向指定地址写入数据。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `address` | `int` | 显示地址（`0xC0`-`0xC3` 对应 4 个数码管） |
| `data` | `int` | 段码数据（控制数码管各段的亮灭） |

**Raises：**

- `SAKSValidationError`：地址或数据无效时抛出。

**代码示例：**

```python
from sakshat import ICTM1637

# 初始化（SAKS 默认引脚）
ic = ICTM1637(di=25, clk=5)

# 开启显示
ic.send_command(ic.CMD_DISPLAY_ON)

# 在第 0 位显示数字 0（段码 0x3F）
ic.write_data(ic.ADDRESSES[0], 0x3F)

# 关闭显示
ic.clear()
```

---

## 数码管显示

### DigitalDisplay

TM1637 4 位数码管显示控制类。通过 TM1637 芯片驱动 4 位共阳极数码管。`show()` 方法支持数字 0-9、负号 `-`、小数点 `.`、空白 `#`；`show_char()` 方法额外支持字母 A-F/H/L/P/U 及小写变体 o/n/r/t/y；`show_segment()` 和 `show_raw()` 提供段码级精细控制。

**别名：** `DigitalDisplayTM1637`（向后兼容）

**导入：**

```python
from sakshat import DigitalDisplay
# 或
from sakshat import DigitalDisplayTM1637  # 向后兼容别名
```

**显示格式说明：**
- `"1234"` - 显示 4 位数字
- `"12.34"` - 显示 "1234"，第 2 位小数点亮
- `"1.2.3.4."` - 显示 "1234"，所有小数点都亮
- `"###1"` - 前三位熄灭，第 4 位显示 "1"
- `"-1.5"` - 第 1 位显示负号，后面显示 "1.5"

**构造函数：**

```python
DigitalDisplay(*, di: int, clk: int, active_level: int = GPIO.HIGH)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `di` | `int` | （必填） | 数据输入/输出引脚（BCM 编号） |
| `clk` | `int` | （必填） | 时钟引脚（BCM 编号） |
| `active_level` | `int` | `GPIO.HIGH` | 有效电平 |

**注意：** 所有参数均为关键字仅参数。

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `is_on` | `bool` | 数码管是否处于显示状态（只读） |
| `numbers` | `list[str]` | 当前显示的字符列表（只读） |
| `ic` | `ICTM1637` | 底层 TM1637 芯片实例（只读） |
| `SEGMENT_MAP` | `dict[str, int]` | 段名称到位掩码的映射字典（类属性）。段名称：`a`(0x01), `b`(0x02), `c`(0x04), `d`(0x08), `e`(0x10), `f`(0x20), `g`(0x40), `dp`(0x80) |
| `CHAR_MAP` | `dict[str, int]` | 字符到段码的映射字典（类属性）。大写字母 A-F/H/L/P/U (0x77-0x3E) 及小写变体 o(0x5C)/n(0x54)/r(0x50)/t(0x78)/y(0x6E)。注意数字 0-9 不在此字典中，数字显示由 `show()` 和 `show_char()` 方法内部处理 |

**方法：**

| 方法 | 说明 |
|------|------|
| `on()` | 开启显示（最大亮度） |
| `off()` | 关闭显示 |
| `show(text: str)` | 在数码管上显示字符串 |
| `show_segment(digit: int, code: int)` | 按十六进制段码控制单个数码管 |
| `show_segments(digit: int, segments: str)` | 按段名称字符串控制单个数码管 |
| `show_char(digit: int, char: str)` | 在单个数码管上显示一个字符 |
| `show_raw(codes: list[int])` | 用原始 4 位段码数组控制全部数码管 |
| `segment_to_bits(code: int) -> str` | 将段码解码为人类可读的段名称字符串（静态方法） |
| `segments_to_code(*segments: str) -> int` | 将段名称编码为十六进制段码（静态方法） |

**`show(text)`：**

在数码管上显示字符串。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `text` | `str` | 显示字符串，支持格式见上方说明 |

**Raises：**

- `SAKSValidationError`：字符串为空时抛出。

**`show_segment(digit, code)`：**

按十六进制段码控制单个数码管。每个 bit 对应一个段：bit0=a, bit1=b, bit2=c, bit3=d, bit4=e, bit5=f, bit6=g, bit7=dp。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `digit` | `int` | 数码管位置（0-3），0 为最左位 |
| `code` | `int` | 段码（0x00-0xFF），控制各段的亮灭 |

**Raises：**

- `SAKSValidationError`：`digit` 超出范围或 `code` 无效时抛出。

**`show_segments(digit, segments)`：**

按段名称字符串控制单个数码管。段名称使用字符 a-g 和 dp（小数点），例如 `"def"` 点亮 d、e、f 段。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `digit` | `int` | 数码管位置（0-3） |
| `segments` | `str` | 段名称字符串，如 `"def"`、`"abcdefg"`、`"adp"` |

**Raises：**

- `SAKSValidationError`：`digit` 超出范围或包含无效段名称时抛出。

**`show_char(digit, char)`：**

在单个数码管上显示一个字符。通过 `CHAR_MAP` 查找对应的段码。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `digit` | `int` | 数码管位置（0-3） |
| `char` | `str` | 要显示的字符，如 `"A"`、`"F"`、`"H"`、`"-"` 等 |

**Raises：**

- `SAKSValidationError`：`digit` 超出范围或字符不在 `CHAR_MAP` 中时抛出。

**`show_raw(codes)`：**

用原始 4 位段码数组控制全部数码管，不经过任何解析转换。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `codes` | `list[int]` | 长度为 4 的段码数组，每个元素为 0x00-0xFF |

**Raises：**

- `SAKSValidationError`：`codes` 长度不为 4 或包含无效段码时抛出。

**`segment_to_bits(code)`（静态方法）：**

将段码解码为人类可读的段名称字符串。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `code` | `int` | 段码（0x00-0xFF） |

**返回值：**

- `str`：段名称字符串，如 `0x3F` 返回 `"abcdef"`。

**`segments_to_code(*segments)`（静态方法）：**

将段名称编码为十六进制段码。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `*segments` | `str` | 可变长度的段名称参数，如 `"a"`, `"b"`, `"c"` |

**返回值：**

- `int`：组合后的段码。

**Raises：**

- `SAKSValidationError`：包含无效段名称时抛出。

**代码示例：**

```python
from sakshat import DigitalDisplay

# 初始化（SAKS 默认引脚）
display = DigitalDisplay(di=25, clk=5)

# 显示数字
display.show("1234")   # 显示 "1234"
display.show("12.34")  # 显示 "12.34"（小数点亮）
display.show("###1")   # 仅第 4 位显示 "1"
display.show("-1.5")   # 第 1 位显示负号

# 段码控制
display.show_segment(0, 0x3F)        # 第 1 位显示数字 0（段码 0x3F）
display.show_segments(1, "def")      # 第 2 位点亮 d、e、f 段（显示类似 "L"）
display.show_char(2, "A")            # 第 3 位显示字母 A
display.show_raw([0x3F, 0x06, 0x5B, 0x4F])  # 原始段码显示 "1053"

# 段码编解码
print(DigitalDisplay.segment_to_bits(0x3F))   # "abcdef"
print(DigitalDisplay.segments_to_code("a", "b", "c", "d", "e", "f"))  # 63 (0x3F)

# 查看常量
print(DigitalDisplay.SEGMENT_MAP)  # {'a': 1, 'b': 2, 'c': 4, 'd': 8, 'e': 16, 'f': 32, 'g': 64, 'dp': 128}
print(DigitalDisplay.CHAR_MAP)     # {'A': 0x77, 'B': 0x7C, 'C': 0x39, 'D': 0x5E, 'E': 0x79, 'F': 0x71, 'H': 0x76, 'L': 0x38, 'P': 0x73, 'U': 0x3E, 'o': 0x5C, 'n': 0x54, 'r': 0x50, 't': 0x78, 'y': 0x6E}

# 开关控制
display.on()   # 开启显示
display.off()  # 关闭显示

# 查看状态
print(display.is_on)    # True
print(display.numbers)  # ['1', '2.', '3', '4']
```

---

## 温度传感器

### DS18B20

DS18B20 数字温度传感器控制类。通过 sysfs 接口读取 OneWire 总线上的 DS18B20 传感器数据。

**导入：**

```python
from sakshat import DS18B20
```

**使用前提：** 需要系统已启用 OneWire 接口。在树莓派上可通过 `raspi-config` 启用，或手动加载内核模块：

```bash
sudo modprobe w1-gpio
sudo modprobe w1-therm
```

**构造函数：**

```python
DS18B20(pin: int = 4)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pin` | `int` | `4` | OneWire 数据引脚（BCM 编号），默认 GPIO4 |

**注意：** 初始化时会自动尝试加载 `w1-gpio` 和 `w1-therm` 内核模块。如果系统未启用 OneWire，传感器将无法被检测到。

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `is_exist` | `bool` | 传感器是否已连接并可用（只读） |
| `temperature` | `float` | 当前温度值（摄氏度），读取失败返回 `-128.0`（只读） |

**方法：**

| 方法 | 说明 |
|------|------|
| `get_temperature_f(index: int = 0) -> float` | 获取华氏温度，读取失败返回 `-128.0` |

**`get_temperature_f(index=0)`：**

获取华氏温度。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `index` | `int` | `0` | 传感器索引（支持多个传感器时使用） |

**返回值：**

- `float`：华氏温度值，读取失败返回 `-128.0`。

**代码示例：**

```python
from sakshat import DS18B20

# 初始化传感器（默认 GPIO4）
sensor = DS18B20()

# 检查传感器是否连接
if sensor.is_exist:
    # 读取摄氏温度
    temp_c = sensor.temperature
    print(f"当前温度: {temp_c:.1f}°C")

    # 读取华氏温度
    temp_f = sensor.get_temperature_f()
    print(f"当前温度: {temp_f:.1f}°F")
else:
    print("DS18B20 传感器未连接")
```

---

## 输入设备

### DipSwitch2Bit

2 位拨码开关控制类。通过 GPIO 中断检测拨码开关状态变化，并通过观察者模式或回调函数通知。

**导入：**

```python
from sakshat import DipSwitch2Bit
```

**构造函数：**

```python
DipSwitch2Bit(*, switch1: int, switch2: int, active_level: int = GPIO.HIGH)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `switch1` | `int` | （必填） | 第 1 位开关的 GPIO 引脚（BCM 编号） |
| `switch2` | `int` | （必填） | 第 2 位开关的 GPIO 引脚（BCM 编号） |
| `active_level` | `int` | `GPIO.HIGH` | 有效电平（拨到 ON 时的电平） |

**注意：** 所有参数均为关键字仅参数。

**Raises：**

- `SAKSValidationError`：引脚编号无效时抛出。

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `is_on` | `list[bool]` | 两位开关的当前状态 `[bit1, bit2]`（只读） |

**方法：**

| 方法 | 说明 |
|------|------|
| `register(observer: object)` | 注册观察者对象。观察者需实现 `on_dip_switch_2bit_status_changed(status)` 方法 |
| `deregister(observer: object)` | 移除观察者对象 |
| `set_callback(callback: Callable[[list[bool]], None])` | 设置简化回调函数 |

**`set_callback(callback)`：**

设置简化回调函数。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `callback` | `Callable[[list[bool]], None]` | 回调函数，签名为 `callback(status: list[bool]) -> None` |

**代码示例：**

```python
from sakshat import DipSwitch2Bit
import RPi.GPIO as GPIO

# SAKS 默认配置
dip = DipSwitch2Bit(switch1=21, switch2=26, active_level=GPIO.LOW)

# 方式 1：回调函数
def on_switch_change(status):
    print(f"拨码开关状态: {status}")

dip.set_callback(on_switch_change)

# 方式 2：通过 SAKSHAT 设置回调
from sakshat import SAKSHAT
saks = SAKSHAT()
saks.dip_switch_status_changed_handler = on_switch_change

# 读取当前状态
print(dip.is_on)  # [False, True]
```

---

### Tact

单个轻触开关控制类。通过 GPIO 中断检测按压/释放事件。

**导入：**

```python
from sakshat import Tact
```

**构造函数：**

```python
Tact(pin: int, *, active_level: int = GPIO.HIGH)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pin` | `int` | （必填） | GPIO 引脚编号（BCM 编号） |
| `active_level` | `int` | `GPIO.HIGH` | 按下时的有效电平 |

**Raises：**

- `SAKSValidationError`：引脚编号无效时抛出。

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `is_on` | `bool` | 开关当前是否被按下（只读） |
| `pin` | `int` | 开关连接的 GPIO 引脚编号（只读） |

**方法：**

| 方法 | 说明 |
|------|------|
| `register(observer: object)` | 注册观察者对象。观察者需实现 `on_tact_event(pin, status)` 方法 |
| `deregister(observer: object)` | 移除观察者对象 |
| `set_callback(callback: Callable[[int, bool], None])` | 设置简化回调函数 |

**`set_callback(callback)`：**

设置简化回调函数。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `callback` | `Callable[[int, bool], None]` | 回调函数，签名为 `callback(pin: int, status: bool) -> None`。`status` 为 `True` 表示按下，`False` 表示释放 |

**代码示例：**

```python
from sakshat import Tact
import RPi.GPIO as GPIO

# SAKS 默认配置（低电平触发）
tact = Tact(20, active_level=GPIO.LOW)

# 设置回调
def on_press(pin, status):
    action = "按下" if status else "释放"
    print(f"引脚 {pin} {action}")

tact.set_callback(on_press)

# 读取状态
print(tact.is_on)  # True 表示按下
print(tact.pin)    # 20
```

---

### TactRow

轻触开关阵列控制类。管理多个轻触开关的集合，支持批量状态查询。

**导入：**

```python
from sakshat import TactRow
```

**构造函数：**

```python
TactRow(pins: list[int], *, active_level: int = GPIO.HIGH)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pins` | `list[int]` | （必填） | GPIO 引脚编号列表 |
| `active_level` | `int` | `GPIO.HIGH` | 按下时的有效电平 |

**Raises：**

- `SAKSValidationError`：当 `pins` 为空时抛出。

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `items` | `list[Tact]` | 所有轻触开关实例的列表（只读） |
| `row_status` | `list[bool]` | 每个开关的当前状态列表（只读） |

**方法：**

| 方法 | 说明 |
|------|------|
| `is_on(index: int) -> bool` | 查询指定开关状态。索引越界返回 `False` |

**代码示例：**

```python
from sakshat import TactRow
import RPi.GPIO as GPIO

# SAKS 默认配置（低电平触发）
row = TactRow([16, 20], active_level=GPIO.LOW)

# 查询状态
print(row.is_on(0))     # 第 1 个开关是否按下
print(row.row_status)   # [False, True]

# 遍历所有开关
for tact in row.items:
    tact.set_callback(lambda pin, status: print(f"引脚 {pin}: {status}"))
```

---

## 异常体系

所有 SAKS SDK 抛出的异常均继承自 `SAKSError`，便于上层统一捕获和处理。

**异常层次结构：**

```
SAKSError (Exception)
├── SAKSGPIOError        # GPIO 操作失败
├── SAKSInitError         # 外设初始化失败
├── SAKSHardwareError     # 硬件通信异常
├── SAKSTimeoutError      # 操作超时
└── SAKSValidationError   # 参数验证失败
```

**导入：**

```python
from sakshat import (
    SAKSError,
    SAKSGPIOError,
    SAKSInitError,
    SAKSHardwareError,
    SAKSTimeoutError,
    SAKSValidationError,
)
```

### SAKSError

SAKS SDK 所有异常的基类。

**基类：** `Exception`

**属性：** 继承自 `Exception`。

### SAKSGPIOError

GPIO 操作失败时抛出。包括引脚初始化失败、读写失败、GPIO 库不可用等场景。

**基类：** `SAKSError`

### SAKSInitError

外设初始化失败时抛出。包括 GPIO 初始化失败、芯片通信失败、传感器未就绪等场景。

**基类：** `SAKSError`

### SAKSHardwareError

硬件通信异常时抛出。包括传感器读取失败、芯片通信超时、设备未连接等场景。

**基类：** `SAKSError`

### SAKSTimeoutError

操作超时时抛出。包括传感器读取超时、线程等待超时等场景。

**基类：** `SAKSError`

### SAKSValidationError

参数验证失败时抛出。包括无效引脚编号、超出范围的数据、非法的显示字符串等场景。

**基类：** `SAKSError`

**代码示例：**

```python
from sakshat import SAKSHAT, SAKSError, SAKSInitError, SAKSValidationError

try:
    saks = SAKSHAT()
except SAKSInitError as e:
    print(f"初始化失败: {e}")
except SAKSError as e:
    print(f"SAKS 错误: {e}")

try:
    saks.buzzer.beep(-1.0)  # 无效参数
except SAKSValidationError as e:
    print(f"参数错误: {e}")
```

---

## GPIO 抽象层

### GPIO

统一的 GPIO 操作接口，隔离 RPi.GPIO 依赖。当 RPi.GPIO 不可用时（如开发/测试环境），所有操作静默降级为 no-op，不会抛出异常。

**注意：** 此接口为内部模块，通常不需要在应用代码中直接使用。在 SAKS SDK 中，`GPIO.HIGH`、`GPIO.LOW` 等常量在创建外设时仍然可用。

**导入：**（内部使用）

```python
from sakshat._gpio import GPIO
```

**常量：**

| 常量 | 值 | 说明 |
|------|-----|------|
| `GPIO.BCM` | 11 | BCM 引脚编号模式 |
| `GPIO.BOARD` | 10 | 物理引脚编号模式 |
| `GPIO.OUT` | 0 | 输出模式 |
| `GPIO.IN` | 1 | 输入模式 |
| `GPIO.HIGH` | 1 | 高电平 |
| `GPIO.LOW` | 0 | 低电平 |
| `GPIO.PUD_UP` | 2 | 上拉电阻 |
| `GPIO.PUD_DOWN` | 1 | 下拉电阻 |
| `GPIO.BOTH` | 33 | 双边沿触发 |
| `GPIO.RISING` | 31 | 上升沿触发 |
| `GPIO.FALLING` | 32 | 下降沿触发 |

**方法：**

| 方法 | 说明 |
|------|------|
| `GPIO.setup(pin, mode, pull_up_down=0)` | 设置引脚模式 |
| `GPIO.output(pin, value)` | 设置引脚输出电平 |
| `GPIO.input(pin) -> int` | 读取引脚输入电平 |
| `GPIO.add_event_detect(pin, edge, callback, bouncetime=0)` | 注册 GPIO 中断回调 |
| `GPIO.setmode(mode)` | 设置引脚编号模式 |
| `GPIO.setwarnings(value)` | 开关 GPIO 警告 |
| `GPIO.cleanup()` | 清理所有 GPIO 资源 |
| `GPIO.PWM(pin, frequency) -> object` | 创建 PWM 实例 |

**行为说明：**
- 当 RPi.GPIO 可用时，所有操作直接转发到 RPi.GPIO
- 当 RPi.GPIO 不可用时，使用 `_MockGPIO` 实现，所有操作仅记录日志，不会抛出异常

---

### GPIOContext

GPIO 资源管理上下文。确保 GPIO 资源在任何情况下都能被正确释放。支持重复调用 `cleanup()`，不会产生副作用。

**导入：**（内部使用）

```python
from sakshat._gpio import GPIOContext
```

**构造函数：**

```python
GPIOContext()
```

**方法：**

| 方法 | 说明 |
|------|------|
| `__enter__() -> GPIOProvider` | 进入上下文，返回 GPIO 提供者 |
| `__exit__(exc_type, exc_val, exc_tb) -> bool` | 退出上下文，自动调用 `cleanup()` |
| `cleanup()` | 清理 GPIO 资源，可重复调用 |

**代码示例：**

```python
from sakshat._gpio import GPIOContext

with GPIOContext() as gpio:
    gpio.setup(12, gpio.OUT)
    gpio.output(12, gpio.HIGH)
# 退出时自动清理
```