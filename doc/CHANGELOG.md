# CHANGELOG

SAKS SDK 所有重要的版本变更记录均记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

---

## [2.2.0] - 2026-07

### 新增

- **温度双通道交替显示**：`13_temp_dual_display.py` — 在数码管上以 "C12.3"/"U12.3" 格式交替显示 DS18B20 环境温度和 CPU 温度，每 5 秒切换一次，LED 进度条指示剩余时间
- **滚动文字显示**：`14_scrolling_text.py` — 在 4 位数码管上实现滚动文字跑马灯效果，支持 A-Z/0-9 全部字符
- **二进制计数器**：`15_binary_counter.py` — 8 路 LED 作为 8-bit 二进制计数器，数码管同步显示十进制值，支持拨码开关调速和按键交互
- **反应速度测试**：`16_reaction_game.py` — 按键反应速度小游戏，5 轮计时，显示平均反应时间，毫秒级精度

### 修复

- **API 文档修正**：`doc/API.md` 中 DigitalDisplay 的 `CHAR_MAP` 描述从 "数字 0-9、字母 A-F/H/L/P/U" 修正为实际的大写字母 A-F/H/L/P/U (0x77-0x3E) 及小写变体 o/n/r/t/y，并补充说明数字段码在 `_SEGMENT_CODE` 内部表中
- **API 文档修正**：`doc/API.md` 的类描述从 "支持数字 0-9、负号、小数点、空白" 更新为区分 `show()` 和 `show_char()` 各自支持的字符集
- **API 文档修正**：修正示例代码中 `CHAR_MAP` 的打印输出为实际支持的字符

---

## [2.1.0] - 2026-07

### 新增

- **DigitalDisplay 段码级控制 API**：新增一系列底层段码控制方法，支持逐段操作数码管显示
  - `show_segment(digit, code)` - 按十六进制段码控制单个数码管
  - `show_segments(digit, segments)` - 按段名称字符串（如 `"def"`）控制单个数码管
  - `show_char(digit, char)` - 在单个数码管上显示单个字符
  - `show_raw(codes)` - 用原始 4 位段码数组直接控制全部数码管
  - `segment_to_bits(code)` - 静态方法，将段码解码为人类可读的段名称字符串
  - `segments_to_code(*segments)` - 静态方法，将段名称编码为十六进制段码
  - `SEGMENT_MAP` - 类属性：段名称到位掩码的映射字典
  - `CHAR_MAP` - 类属性：字符到段码的映射字典
- **深度解析示例脚本**：新增 6 个深入解析示例（7-12）
  - `07_segment_deep_dive.py` - 数码管段码深度解析
  - `08_74hc595_deep_dive.py` - 74HC595 芯片深度解析
  - `09_tm1637_deep_dive.py` - TM1637 芯片深度解析
  - `10_buzzer_deep_dive.py` - 蜂鸣器深度解析
  - `11_led_deep_dive.py` - LED 深度解析
  - `12_ds18b20_deep_dive.py` - DS18B20 深度解析

### 变更

- **环境检查**：`examples/main.py` 启动时自动检查 Python 版本、操作系统、RPi.GPIO 安装状态、sakshat 包和树莓派型号
- **文档重组**：文档文件（README.md、API.md、CHANGELOG.md、MIGRATION.md、PROJECT_STRUCTURE.md）移至 `doc/` 目录，根目录保留精简的快速入门 README

---

## [2.0.0] - 2026-07

### 重大变更

v2.0.0 是 SAKS SDK 的一次全面重写，从基于 Python 2 的旧代码库迁移到现代 Python 3.13+ 架构。
**此版本不向后兼容 v0.x 系列。**

### 新增

- **Python 3.13+ 支持**：最低要求 Python 3.13，充分利用现代 Python 特性
- **异常体系**：新增统一的异常层次结构
  - `SAKSError` - 所有异常基类
  - `SAKSGPIOError` - GPIO 操作失败
  - `SAKSInitError` - 外设初始化失败
  - `SAKSHardwareError` - 硬件通信异常
  - `SAKSTimeoutError` - 操作超时
  - `SAKSValidationError` - 参数验证失败
- **上下文管理器支持**：`SAKSHAT` 现在支持 `with` 语句，自动管理 GPIO 资源
- **GPIO 抽象层**：新增 `sakshat._gpio` 模块，隔离 RPi.GPIO 依赖，非树莓派环境下自动降级为模拟模式
- **类型注解**：完整的类型注解覆盖，支持 `pyright` strict 模式
- **现代化构建系统**：使用 `hatchling` 构建，`pyproject.toml` 配置
- **代码质量工具**：集成 `ruff` (linting/formatting)、`pyright` (类型检查)、`pytest` (测试)
- **Google 风格文档字符串**：所有公共 API 采用 Google 风格 docstring
- **`py.typed` 标记**：支持 PEP 561，提供类型信息给下游使用者
- **`SAKSPins` 增强**：新增 `validate()` 和 `list_all()` 类方法
- **`LedRow` 新增**：独立的 LED 阵列类，支持直接 GPIO 驱动
- **`TactRow` 新增**：轻触开关阵列类，批量管理多个开关
- **`DigitalDisplay` 新增**：简化的数码管显示类（原 `DigitalDisplayTM1637` 别名）
- **`IC74HC595` 新增**：新的芯片类名（原 `IC_74HC595` 保留为别名）
- **`ICTM1637` 新增**：新的芯片类名（原 `IC_TM1637` 保留为别名）

### 变更

- **包结构重构**：从 `entities/` 单层目录改为 `sakshat/` 命名空间包，内部模块使用下划线前缀
- **导入路径**：
  - 旧：`from entities import Buzzer` -> 新：`from sakshat import Buzzer`
  - 旧：`from sakspins import SAKSPins` -> 新：`from sakshat import SAKSPins`
  - 旧：`from sakshat import SAKSHAT` -> 新：`from sakshat import SAKSHAT`（保持不变）
- **参数风格**：所有构造函数参数从位置参数改为关键字仅参数（keyword-only）
  - 旧：`Buzzer(12, GPIO.LOW)` -> 新：`Buzzer(12, active_level=GPIO.LOW)`
  - 旧：`IC_74HC595({'ds':6, 'shcp':19, 'stcp':13})` -> 新：`IC74HC595(ds=6, shcp=19, stcp=13)`
- **类名变更**：
  - `IC_74HC595` -> `IC74HC595`（旧名保留为别名）
  - `IC_TM1637` -> `ICTM1637`（旧名保留为别名）
  - `DigitalDisplayTM1637` -> `DigitalDisplay`（旧名保留为别名）
- **方法名变更**：
  - `beepAction` -> `beep_pattern`（旧名已移除）
  - `flashAction` -> `flash_pattern`（旧名已移除）
  - `IC_TM1637.set_command` -> `ICTM1637.send_command`
  - `IC_TM1637.set_data` -> `ICTM1637.write_data`
  - `IC_TM1637.set_byte` -> 不再公开，改为内部方法
- **异常处理**：不再抛出普通 `ValueError`/`RuntimeError`/`IndexError`，统一使用 `SAKS*` 异常类
- **GPIO 处理**：不再在每个模块中重复 `import RPi.GPIO`，统一通过 `sakshat._gpio` 抽象层
- **`Led.pulse()` 参数**：所有参数改为关键字仅参数

### 移除

- **Python 2 支持**：不再兼容 Python 2.x
- **旧版 `beepAction` 别名**：在 v2.0.0 新代码中已移除（旧版 `entities/` 中仍保留）
- **旧版 `flashAction` 别名**：在 v2.0.0 新代码中已移除（旧版 `entities/` 中仍保留）
- **`IC_TM1637.set_bit` / `set_byte` 公开方法**：不再暴露为公开 API

### 已弃用

- `IC_74HC595` 类名：使用 `IC74HC595` 替代
- `IC_TM1637` 类名：使用 `ICTM1637` 替代
- `DigitalDisplayTM1637` 类名：使用 `DigitalDisplay` 替代
- 旧版 `entities/` 目录和根目录的 `sakshat.py`、`sakspins.py`：保留以兼容现有代码，但推荐使用 `sakshat/` 包

---

## [0.3.0] - 2016

### 新增

- 首个公开发布版本
- 基础 SAKS 扩展板驱动支持
- 74HC595 移位寄存器控制（8 路 LED）
- TM1637 数码管驱动（4 位数码管）
- 蜂鸣器控制（开关和节奏蜂鸣）
- DS18B20 温度传感器支持
- 2 位拨码开关（GPIO 中断 + 观察者模式）
- 2 个轻触开关（GPIO 中断 + 观察者模式）
- LED 呼吸灯效果（PWM）
- 事件回调机制
- 自动 GPIO 资源清理（atexit）

---

[2.1.0]: https://github.com/spoonysonny/SAKS-SDK/releases/tag/v2.1.0
[2.0.0]: https://github.com/spoonysonny/SAKS-SDK/releases/tag/v2.0.0
[0.3.0]: https://github.com/spoonysonny/SAKS-SDK/releases/tag/v0.3.0