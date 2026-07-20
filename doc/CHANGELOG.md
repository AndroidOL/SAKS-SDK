# CHANGELOG

SAKS SDK 所有重要的版本变更记录均记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

---

## [2.3.1] - 2026-07

### 修复

- **lgpio 虚拟环境冲突**：lgpio 是 C 扩展，在虚拟环境中通过 pip 安装后无法正确访问 `/dev/gpiochip*` 设备，导致 GPIO 初始化失败。`_gpio.py` 新增 `_is_venv()` 检测，虚拟环境中自动跳过 lgpio 加载，直接使用 RPi.GPIO 后端
- **lgpio 改为可选依赖**：`pyproject.toml` 中 lgpio 从 `dependencies` 移至 `[project.optional-dependencies]`，不再强制安装。需要边沿检测的用户可通过 `sudo apt install python3-lgpio` 系统安装，或 `pip install sakshat[lgpio]` 安装

### 新增

- **`get_backend_info()` 函数**：`_gpio.py` 新增公开函数，返回当前 GPIO 后端信息（后端类型、lgpio/RPi.GPIO 可用性、虚拟环境状态），便于故障排查
- **虚拟环境使用说明**：README 新增虚拟环境注意事项，明确说明边沿检测在虚拟环境中的限制和解决方案

### 变更

- **版本号升级**：`__init__.py`、`pyproject.toml` 版本号更新为 2.3.1

---

## [2.3.0] - 2026-07

### 修复

- **lgpio 后端支持 (边沿检测终极修复)**：RPi.GPIO 使用已弃用的 sysfs GPIO 接口 (`/sys/class/gpio/`)，在较新内核 (6.x, Bookworm) 上 `add_event_detect` 抛出 `RuntimeError: Failed to add edge detection`。新增 `lgpio` 后端，使用现代 gpiochip 字符设备接口 (`/dev/gpiochip*`)，在较新内核上完全支持边沿检测。`_gpio.py` 自动选择最优后端：lgpio 优先 → RPi.GPIO 回退 → Mock 降级。新增 `_LgpioBackend` 类封装 lgpio API，兼容 RPi.GPIO 接口签名
- **GPIO 边沿检测降级轮询**：`DipSwitch2Bit` 和 `Tact` 在 `add_event_detect` 失败时自动降级为 GPIO 轮询模式，`is_on` 属性和 `poll()` 方法直接读取引脚电平。异常捕获从 `RuntimeError` 扩展为 `Exception`，兼容不同 GPIO 后端
- **初始化错误信息可见性**：`SAKSHAT.__init__` 中 `from None` 改为 `from e`，初始化失败时不再吞掉底层异常
- **部分初始化后 GPIO 泄漏**：`SAKSHAT` 新增 `_gpio_done` 标志位追踪 GPIO 初始化状态，即使外设创建失败也能正确释放 GPIO 资源
- **GPIO 清理警告消除**：`_gpio_init()` 中 `setwarnings(False)` 提前到 `cleanup()` 之前

### 新增

- **GPIO 诊断工具**：`tools/gpio_diag.py` — 检测当前环境 GPIO 边沿检测支持情况，自动测试 lgpio 和 RPi.GPIO 两个后端
- **lgpio 依赖**：`pyproject.toml` 新增 `lgpio>=0.2.2` 依赖 (Linux only)

### 变更

- **版本号统一**：`__init__.py`、`pyproject.toml`、`doc/API.md` 版本号统一更新
- **GPIO 抽象层增强**：`_gpio.py` 的 `GPIOProvider` 协议和 `_MockGPIO` 新增 `remove_event_detect` 方法

---

## [2.2.0] - 2026-07

### 新增

- **温度双通道交替显示**：`13_temp_dual_display.py` — 在数码管上以 "C12.3"/"U12.3" 格式交替显示 DS18B20 环境温度和 CPU 温度，每 5 秒切换一次，LED 进度条指示剩余时间
- **滚动文字显示**：`14_scrolling_text.py` — 在 4 位数码管上实现滚动文字跑马灯效果，支持 A-Z/0-9 全部字符
- **二进制计数器**：`15_binary_counter.py` — 8 路 LED 作为 8-bit 二进制计数器，数码管同步显示十进制值，支持拨码开关调速和按键交互
- **反应速度测试**：`16_reaction_game.py` — 按键反应速度小游戏，5 轮计时，显示平均反应时间，毫秒级精度
- **秒表计时器**：`17_stopwatch.py` — 高精度秒表，左键启停、右键复位，数码管显示 MM:SS 格式，LED 进度条指示已用时间
- **LED 扫描灯**：`18_led_scanner.py` — 四种 LED 扫描动画模式（骑士灯/波浪/乒乓/填充排空），拨码开关调速，按键切换模式
- **倒计时闹钟**：`19_countdown_timer.py` — 可设时倒计时器，拨码选择 30/60/90/120 秒，数码管显示 MM:SS，LED 进度条，到时蜂鸣报警
- **温度阈值报警器**：`20_temp_alarm.py` — CPU/DS18B20 双通道温度监控，拨码设定 50/60/70/80°C 阈值，LED 分区指示（绿/黄/橙/红），超温蜂鸣报警

### 修复

- **API 文档修正**：`doc/API.md` 中 DigitalDisplay 的 `CHAR_MAP` 描述从 "数字 0-9、字母 A-F/H/L/P/U" 修正为实际的大写字母 A-F/H/L/P/U (0x77-0x3E) 及小写变体 o/n/r/t/y，并补充说明数字段码在 `_SEGMENT_CODE` 内部表中
- **API 文档修正**：`doc/API.md` 的类描述从 "支持数字 0-9、负号、小数点、空白" 更新为区分 `show()` 和 `show_char()` 各自支持的字符集
- **API 文档修正**：修正示例代码中 `CHAR_MAP` 的打印输出为实际支持的字符
- **API 文档修正**：版本号统一为 v2.2.0；修复 `show_segments` 无效示例 `"a.dp"` → `"adp"`；修正 `SAKSHAT` 初始化错误描述范围；修正 `__exit__` 返回值类型标注；移除 CHAR_MAP 对私有属性 `_SEGMENT_CODE` 的引用
- **IC74HC595 引脚校验**：`sakshat/_ic_74hc595.py` 构造函数新增引脚编号校验，与其他类保持一致

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

[2.3.1]: https://github.com/spoonysonny/SAKS-SDK/releases/tag/v2.3.1
[2.3.0]: https://github.com/spoonysonny/SAKS-SDK/releases/tag/v2.3.0
[2.2.0]: https://github.com/spoonysonny/SAKS-SDK/releases/tag/v2.2.0
[2.1.0]: https://github.com/spoonysonny/SAKS-SDK/releases/tag/v2.1.0
[2.0.0]: https://github.com/spoonysonny/SAKS-SDK/releases/tag/v2.0.0
[0.3.0]: https://github.com/spoonysonny/SAKS-SDK/releases/tag/v0.3.0