# SAKS-SDK

树莓派瑞士军刀扩展板 (SAKS) 的 Python SDK，基于面向对象设计，封装了所有硬件操作逻辑，
让创客们可以专注于功能实现，无需关心底层驱动细节。

## 硬件支持

- 树莓派 3B/3B+/4B/5 (及其他 40-pin GPIO 型号)
- SAKS 扩展板 (瑞士军刀扩展板)
- DS18B20 温度传感器 (可选)

## 虚拟环境注意事项

SDK 在虚拟环境中可以正常使用，但存在以下限制：

| 环境 | 边沿检测 (中断) | 推荐方案 |
|------|:---:|------|
| 系统 Python | ✅ 完全支持 | 安装 lgpio 后优先使用，否则回退 RPi.GPIO |
| 虚拟环境 (venv) | ⚠️ 降级为轮询 | 自动降级，程序正常运行但开关响应需通过 `poll()` 或 `is_on` 属性轮询 |

**原因**：lgpio 是 C 扩展，在虚拟环境中通过 pip 安装后无法正确访问 `/dev/gpiochip*` 字符设备。SDK 会自动检测虚拟环境并跳过 lgpio，避免冲突。

**解决方案**（三选一）：
1. **推荐**: 直接使用系统 Python（退出虚拟环境），无需额外操作
2. 安装 lgpio 系统包：`sudo apt install python3-lgpio`，然后 SDK 可在系统 Python 下使用 lgpio 后端
3. 继续使用虚拟环境：SDK 自动降级为轮询模式，开关功能正常但响应延迟略高（毫秒级，不影响典型使用场景）

```bash
# 查看当前后端状态
python -c "from sakshat._gpio import get_backend_info; print(get_backend_info())"
```

## 功能特性

| 外设         | 芯片/接口    | 说明                          |
|-------------|-------------|-------------------------------|
| 8 路 LED     | 74HC595     | 移位寄存器控制，仅需 3 个 GPIO 引脚 |
| 4 位数码管    | TM1637      | 两线串行接口，支持数字/小数点/负号   |
| 蜂鸣器       | GPIO 直连    | 支持单次蜂鸣和节奏蜂鸣            |
| DS18B20     | OneWire     | 数字温度传感器，精度 0.0625°C     |
| 2 位拨码开关  | GPIO 中断    | 支持状态变更事件通知              |
| 2 个轻触开关  | GPIO 中断    | 支持按压/释放事件通知             |

## 快速开始

### 安装依赖

```bash
# 安装 RPi.GPIO (树莓派通常已预装)
sudo apt-get install python3-rpi.gpio

# 启用 OneWire 接口 (使用 DS18B20 时需要)
sudo raspi-config  # Interfacing Options -> 1-Wire -> Enable
```

### 运行示例

```bash
cd SAKS-SDK
python3 examples/main.py
```

或者直接运行单个示例:

```bash
python3 examples/01_hello_saks.py         # 基础入门
python3 examples/02_digital_display.py     # 数码管显示
python3 examples/03_temperature_monitor.py # 温度监控
python3 examples/04_button_interaction.py  # 按键交互
python3 examples/05_cpu_temperature_alarm.py # CPU 温度报警
python3 examples/06_full_demo.py           # 综合演示
```

### 最简代码

```python
from sakshat import SAKSHAT

# 创建 SAKS 实例 (自动初始化 GPIO)
saks = SAKSHAT()

# 蜂鸣器响 0.5 秒
saks.buzzer.beep(0.5)

# LED 交替亮灭
saks.ledrow.set_row([True, False, True, False, True, False, True, False])

# 数码管显示 "12.34"
saks.digital_display.show("12.34")

# 读取温度
temp = saks.ds18b20.temperature
print(f"温度: {temp:.1f}°C")

# 退出前清理资源
saks.cleanup()
```

### 使用 with 语句 (推荐)

```python
from sakshat import SAKSHAT

with SAKSHAT() as saks:
    saks.buzzer.beep(0.5)
    saks.ledrow.set_row([True, False, True, False, True, False, True, False])
    # with 退出时自动清理 GPIO 资源
```

## API 参考

### SAKSHAT 主控制器

```python
from sakshat import SAKSHAT

saks = SAKSHAT()              # 初始化所有外设
saks.cleanup()                # 清理 GPIO 资源
saks.buzzer                   # 蜂鸣器实例
saks.ledrow                   # 8 路 LED 实例
saks.ds18b20                  # 温度传感器实例
saks.digital_display          # 数码管实例
saks.dip_switch               # 拨码开关实例
saks.tactrow                  # 轻触开关阵列实例
```

### Buzzer 蜂鸣器

```python
buzzer = saks.buzzer
buzzer.on()                            # 打开
buzzer.off()                           # 关闭
buzzer.beep(0.5)                       # 蜂鸣 0.5 秒
buzzer.beep_pattern(0.02, 0.02, 30)    # 快节奏蜂鸣 30 次
print(buzzer.is_on)                    # 查看状态
```

### Led74HC595 LED 阵列

```python
leds = saks.ledrow
leds.on()                              # 全部打开
leds.off()                             # 全部关闭
leds.on_for_index(0)                   # 打开第 1 个 LED
leds.off_for_index(2)                  # 关闭第 3 个 LED
leds.set_row([True, False, True, ...]) # 按数组设置 (None=不变)
print(leds.row_status)                 # 查看状态
print(leds.is_on(0))                   # 查看第 1 个 LED 状态
```

### DigitalDisplayTM1637 数码管

```python
display = saks.digital_display
display.show("1234")     # 显示 "1234"
display.show("12.34")    # 显示 "12.34" (小数点亮)
display.show("###1")     # 仅第 4 位显示 "1"
display.show("-1.5")     # 显示负号
display.on()             # 开启显示
display.off()            # 关闭显示
```

### DS18B20 温度传感器

```python
sensor = saks.ds18b20
print(sensor.is_exist)           # 传感器是否连接
print(sensor.temperature)        # 摄氏温度
print(sensor.get_temperature_f()) # 华氏温度
```

### 事件回调

```python
# 轻触开关回调
def on_tact(pin, status):
    if status:
        print(f"引脚 {pin} 被按下")

saks.tact_event_handler = on_tact

# 拨码开关回调
def on_dip_switch(status):
    print(f"拨码开关: {status}")

saks.dip_switch_status_changed_handler = on_dip_switch
```

## 引脚定义

| 功能         | BCM 引脚 | 说明           |
|-------------|---------|---------------|
| 74HC595 DS  | GPIO6   | 数据输入       |
| 74HC595 SHCP| GPIO19  | 移位时钟       |
| 74HC595 STCP| GPIO13  | 存储时钟       |
| TM1637 DI   | GPIO25  | 数据线         |
| TM1637 CLK  | GPIO5   | 时钟线         |
| BUZZER      | GPIO12  | 蜂鸣器         |
| TACT LEFT   | GPIO16  | 左轻触开关      |
| TACT RIGHT  | GPIO20  | 右轻触开关      |
| DIP SWITCH1 | GPIO21  | 拨码开关第 1 位 |
| DIP SWITCH2 | GPIO26  | 拨码开关第 2 位 |
| DS18B20     | GPIO4   | 温度传感器      |

## 许可证

GPL v2.0

## 链接

- GitHub: https://github.com/spoonysonny/SAKS-SDK
- 树莓派实验室: https://www.nxez.com
- SAKS 购买: http://link.nxez.com/spoony/cps-products-saks