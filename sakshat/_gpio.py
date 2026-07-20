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

"""GPIO 抽象层.

提供统一的 GPIO 操作接口，自动选择最优后端：

1. **lgpio** (推荐): 使用现代 gpiochip 字符设备接口 (/dev/gpiochip*)，
   在较新内核 (6.x, Bookworm) 上完全支持边沿检测。
   **注意**: lgpio 是可选依赖，仅在系统 Python 环境（非虚拟环境）中可用。
2. **RPi.GPIO** (回退): 使用已弃用的 sysfs 接口，在较新内核上边沿检测可能不可用。
3. **Mock** (降级): 当没有任何 GPIO 库可用时，静默降级为模拟模式。

所有 GPIO 资源管理遵循 RAII 原则，通过上下文管理器确保资源释放。
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import AbstractContextManager
from typing import Any, Protocol

logger = logging.getLogger(__name__)


def _is_venv() -> bool:
    """检测当前是否运行在虚拟环境中."""
    return (
        hasattr(sys, "real_prefix")
        or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
        or "VIRTUAL_ENV" in __import__("os").environ
    )


# ── 尝试导入 lgpio (现代 gpiochip 接口) ──────────────────────────────
# lgpio 是 C 扩展，在虚拟环境中通过 pip 安装后可能无法正确访问 /dev/gpiochip*
# 因此仅在系统 Python 环境中尝试加载
_LGPIO_MOD = None
if not _is_venv():
    try:
        import lgpio as _LGPIO_MOD  # type: ignore[import-untyped]
    except ImportError:
        logger.debug("lgpio 不可用，将尝试 RPi.GPIO 回退")
else:
    logger.debug("检测到虚拟环境，跳过 lgpio 加载，直接使用 RPi.GPIO")

# ── 尝试导入 RPi.GPIO (传统 sysfs 接口) ──────────────────────────────
try:
    import RPi.GPIO as _RPI_MOD  # type: ignore[import-untyped]
except ImportError:
    _RPI_MOD = None
    logger.debug("RPi.GPIO 不可用")


# ═══════════════════════════════════════════════════════════════════════
# GPIOProvider 协议
# ═══════════════════════════════════════════════════════════════════════


class GPIOProvider(Protocol):
    """GPIO 操作提供者协议."""

    BCM: int
    BOARD: int
    OUT: int
    IN: int
    HIGH: int
    LOW: int
    PUD_UP: int
    PUD_DOWN: int
    PUD_OFF: int
    BOTH: int
    RISING: int
    FALLING: int

    @staticmethod
    def setup(pin: int, mode: int, pull_up_down: int = 0) -> None: ...
    @staticmethod
    def output(pin: int, value: int) -> None: ...
    @staticmethod
    def input(pin: int) -> int: ...
    @staticmethod
    def add_event_detect(
        pin: int, edge: int, callback: object, bouncetime: int = 0
    ) -> None: ...
    @staticmethod
    def remove_event_detect(pin: int) -> None: ...
    @staticmethod
    def setmode(mode: int) -> None: ...
    @staticmethod
    def setwarnings(value: bool) -> None: ...
    @staticmethod
    def cleanup() -> None: ...
    @staticmethod
    def PWM(pin: int, frequency: int) -> object: ...


# ═══════════════════════════════════════════════════════════════════════
# lgpio 后端 (现代 gpiochip 接口)
# ═══════════════════════════════════════════════════════════════════════


class _LgpioBackend:
    """lgpio 后端封装，使用现代 gpiochip 字符设备接口.

    与 RPi.GPIO (已弃用的 sysfs 接口) 不同，lgpio 使用 /dev/gpiochip*
    字符设备，在较新内核 (6.x, Bookworm) 上完全支持边沿检测。

    实现了与 RPi.GPIO 兼容的 API，可直接替换使用。
    """

    # 常量定义 — 与 RPi.GPIO 保持一致
    BCM: int = 11
    BOARD: int = 10
    OUT: int = 0
    IN: int = 1
    HIGH: int = 1
    LOW: int = 0
    PUD_UP: int = 2
    PUD_DOWN: int = 1
    PUD_OFF: int = 0
    BOTH: int = 33
    RISING: int = 31
    FALLING: int = 32

    # lgpio 边沿常量映射
    _EDGE_MAP: dict[int, int] = {
        33: 3,  # BOTH → BOTH_EDGES
        31: 1,  # RISING → RISING_EDGE
        32: 2,  # FALLING → FALLING_EDGE
    }

    def __init__(self) -> None:
        self._handle: int | None = None
        self._chip: int = 0  # /dev/gpiochip0
        self._lgpio: Any = None
        self._callbacks: dict[int, Any] = {}
        self._pwm_objects: dict[int, _LgpioPWM] = {}

    def _ensure_handle(self) -> None:
        """确保 gpiochip 已打开 (懒初始化)."""
        if self._handle is None:
            if _LGPIO_MOD is None:
                raise RuntimeError("lgpio 模块不可用")
            self._lgpio = _LGPIO_MOD
            self._handle = _LGPIO_MOD.gpiochip_open(self._chip)
            logger.debug("lgpio: 已打开 gpiochip%d", self._chip)

    # ── 引脚配置 ──────────────────────────────────────────────────

    def setup(self, pin: int, mode: int, pull_up_down: int = 0) -> None:
        """配置引脚为输入或输出模式.

        Args:
            pin: GPIO 引脚编号 (BCM).
            mode: OUT 或 IN.
            pull_up_down: PUD_UP / PUD_DOWN / PUD_OFF.
        """
        self._ensure_handle()
        assert self._lgpio is not None
        assert self._handle is not None

        # 释放已有的引脚声明
        try:
            self._lgpio.gpio_free(self._handle, pin)
        except Exception:
            pass

        if mode == self.OUT:
            self._lgpio.gpio_claim_output(self._handle, pin, 0)
        else:
            flags = 0
            if pull_up_down == self.PUD_UP:
                flags = self._lgpio.SET_PULL_UP
            elif pull_up_down == self.PUD_DOWN:
                flags = self._lgpio.SET_PULL_DOWN
            self._lgpio.gpio_claim_input(self._handle, pin, flags)

    def output(self, pin: int, value: int) -> None:
        """设置引脚输出电平.

        Args:
            pin: GPIO 引脚编号.
            value: HIGH 或 LOW.
        """
        assert self._lgpio is not None
        assert self._handle is not None
        self._lgpio.gpio_write(self._handle, pin, value)

    def input(self, pin: int) -> int:
        """读取引脚输入电平.

        Args:
            pin: GPIO 引脚编号.

        Returns:
            0 (LOW) 或 1 (HIGH).
        """
        assert self._lgpio is not None
        assert self._handle is not None
        return self._lgpio.gpio_read(self._handle, pin)

    # ── 边沿检测 ──────────────────────────────────────────────────

    def add_event_detect(
        self,
        pin: int,
        edge: int,
        callback: object,
        bouncetime: int = 0,
    ) -> None:
        """注册 GPIO 边沿检测回调.

        使用 gpiochip 的 alert 机制，在较新内核上完全支持。
        与 RPi.GPIO 的 sysfs epoll 不同，lgpio 使用内核 gpiochip
        字符设备的 poll/read 机制，不依赖已弃用的 sysfs GPIO。

        Args:
            pin: GPIO 引脚编号.
            edge: BOTH / RISING / FALLING 边沿类型.
            callback: 回调函数，签名为 callback(channel).
            bouncetime: 去抖时间 (毫秒)，lgpio 中通过软件去抖实现.

        Raises:
            RuntimeError: 边沿检测注册失败时抛出.
        """
        self._ensure_handle()
        assert self._lgpio is not None
        assert self._handle is not None

        lgpio_edge = self._EDGE_MAP.get(edge)
        if lgpio_edge is None:
            raise ValueError(f"不支持的边沿类型: {edge}")

        # 释放已有声明，重新以 alert 模式声明
        try:
            self._lgpio.gpio_free(self._handle, pin)
        except Exception:
            pass

        self._lgpio.gpio_claim_alert(
            self._handle, pin, lgpio_edge, self._lgpio.SET_PULL_UP
        )

        # 软件去抖: 在回调包装中实现
        if bouncetime > 0:
            last_trigger: float = 0.0

            def _debounced(chip: int, gpio: int, level: int, timestamp: int) -> None:  # noqa: ARG001
                nonlocal last_trigger
                now = time.monotonic()
                if now - last_trigger < bouncetime / 1000.0:
                    return
                last_trigger = now
                callback(gpio)  # type: ignore[misc]

            wrapped = _debounced
        else:
            def _direct(chip: int, gpio: int, level: int, timestamp: int) -> None:  # noqa: ARG001
                callback(gpio)  # type: ignore[misc]

            wrapped = _direct

        cb = self._lgpio.callback(self._handle, pin, lgpio_edge, wrapped)
        self._callbacks[pin] = cb

    def remove_event_detect(self, pin: int) -> None:
        """取消引脚边沿检测.

        Args:
            pin: GPIO 引脚编号.
        """
        if pin in self._callbacks:
            try:
                self._callbacks[pin].cancel()
            except Exception:
                logger.debug("取消 lgpio 回调时出错", exc_info=True)
            del self._callbacks[pin]

    # ── 全局配置 ──────────────────────────────────────────────────

    def setmode(self, mode: int) -> None:  # noqa: ARG002
        """设置引脚编号模式 (lgpio 始终使用 BCM 编号，此方法为兼容性保留)."""
        pass

    def setwarnings(self, value: bool) -> None:  # noqa: ARG002
        """设置警告模式 (lgpio 不产生类似警告，此方法为兼容性保留)."""
        pass

    # ── 资源清理 ──────────────────────────────────────────────────

    def cleanup(self) -> None:
        """清理所有 GPIO 资源.

        关闭所有回调、PWM 和 gpiochip 句柄。
        可重复调用，不会产生副作用。
        """
        # 清理 PWM
        for pwm in list(self._pwm_objects.values()):
            try:
                pwm._stop_internal()
            except Exception:
                pass
        self._pwm_objects.clear()

        # 清理回调
        for pin, cb in list(self._callbacks.items()):
            try:
                cb.cancel()
            except Exception:
                pass
        self._callbacks.clear()

        # 关闭 gpiochip
        if self._handle is not None:
            assert self._lgpio is not None
            try:
                self._lgpio.gpiochip_close(self._handle)
            except Exception:
                logger.debug("关闭 gpiochip 时出错", exc_info=True)
            self._handle = None

    # ── PWM ───────────────────────────────────────────────────────

    def PWM(self, pin: int, frequency: int) -> _LgpioPWM:
        """创建 PWM 实例 (lgpio 硬件 PWM).

        Args:
            pin: GPIO 引脚编号 (需要支持硬件 PWM 的引脚).
            frequency: PWM 频率 (Hz).

        Returns:
            _LgpioPWM 实例，兼容 RPi.GPIO.PWM 接口.
        """
        self._ensure_handle()
        assert self._lgpio is not None
        assert self._handle is not None
        pwm = _LgpioPWM(self._lgpio, self._handle, pin, frequency)
        self._pwm_objects[pin] = pwm
        return pwm


class _LgpioPWM:
    """lgpio 硬件 PWM 封装，兼容 RPi.GPIO.PWM 接口."""

    def __init__(
        self, lgpio_mod: Any, handle: int, pin: int, frequency: int
    ) -> None:
        self._lgpio = lgpio_mod
        self._handle = handle
        self._pin = pin
        self._frequency = frequency
        self._duty_cycle: int = 0
        self._started: bool = False

    def start(self, duty_cycle: float) -> None:
        """启动 PWM 输出.

        Args:
            duty_cycle: 占空比 (0.0-100.0).
        """
        self._duty_cycle = int(duty_cycle)
        self._lgpio.tx_pwm(
            self._handle, self._pin, self._frequency, self._duty_cycle
        )
        self._started = True

    def stop(self) -> None:
        """停止 PWM 输出."""
        self._stop_internal()

    def _stop_internal(self) -> None:
        """内部停止方法 (不检查状态)."""
        if self._started:
            try:
                self._lgpio.tx_pwm(self._handle, self._pin, 0, 0)
            except Exception:
                pass
            self._started = False

    def ChangeDutyCycle(self, duty_cycle: float) -> None:
        """修改占空比.

        Args:
            duty_cycle: 新占空比 (0.0-100.0).
        """
        self._duty_cycle = int(duty_cycle)
        if self._started:
            self._lgpio.tx_pwm(
                self._handle, self._pin, self._frequency, self._duty_cycle
            )

    def ChangeFrequency(self, frequency: float) -> None:
        """修改 PWM 频率.

        Args:
            frequency: 新频率 (Hz).
        """
        self._frequency = int(frequency)
        if self._started:
            self._lgpio.tx_pwm(
                self._handle, self._pin, self._frequency, self._duty_cycle
            )


# ═══════════════════════════════════════════════════════════════════════
# Mock GPIO 实现
# ═══════════════════════════════════════════════════════════════════════


class _MockGPIO:
    """模拟 GPIO 实现，用于非树莓派环境."""

    BCM = 11
    BOARD = 10
    OUT = 0
    IN = 1
    HIGH = 1
    LOW = 0
    PUD_UP = 2
    PUD_DOWN = 1
    PUD_OFF = 0
    BOTH = 33
    RISING = 31
    FALLING = 32

    @staticmethod
    def setup(pin: int, mode: int, pull_up_down: int = 0) -> None:  # noqa: ARG004
        logger.debug("Mock GPIO.setup(pin=%d, mode=%d)", pin, mode)

    @staticmethod
    def output(pin: int, value: int) -> None:  # noqa: ARG004
        logger.debug("Mock GPIO.output(pin=%d, value=%d)", pin, value)

    @staticmethod
    def input(pin: int) -> int:  # noqa: ARG004
        return _MockGPIO.LOW

    @staticmethod
    def add_event_detect(
        pin: int, edge: int, callback: object, bouncetime: int = 0  # noqa: ARG004
    ) -> None:
        logger.debug("Mock GPIO.add_event_detect(pin=%d)", pin)

    @staticmethod
    def remove_event_detect(pin: int) -> None:  # noqa: ARG004
        logger.debug("Mock GPIO.remove_event_detect(pin=%d)", pin)

    @staticmethod
    def setmode(mode: int) -> None:  # noqa: ARG004
        logger.debug("Mock GPIO.setmode(mode=%d)", mode)

    @staticmethod
    def setwarnings(value: bool) -> None:  # noqa: ARG004
        logger.debug("Mock GPIO.setwarnings(value=%s)", value)

    @staticmethod
    def cleanup() -> None:
        logger.debug("Mock GPIO.cleanup()")

    @staticmethod
    def PWM(pin: int, frequency: int) -> object:  # noqa: ARG004
        """返回模拟 PWM 对象."""

        class _MockPWM:
            def start(self, duty_cycle: int) -> None: ...
            def stop(self) -> None: ...
            def ChangeDutyCycle(self, duty_cycle: int) -> None: ...
            def ChangeFrequency(self, frequency: int) -> None: ...

        return _MockPWM()


# ═══════════════════════════════════════════════════════════════════════
# 后端选择
# ═══════════════════════════════════════════════════════════════════════

# 优先级: lgpio (系统 Python) → RPi.GPIO → Mock
# 虚拟环境中跳过 lgpio，因为 C 扩展无法正确访问 /dev/gpiochip*

if _LGPIO_MOD is not None:
    try:
        _backend = _LgpioBackend()
        _backend._ensure_handle()  # 验证 gpiochip 可打开
        GPIO: GPIOProvider = _backend  # type: ignore[assignment]
        logger.info("GPIO 后端: lgpio (gpiochip 字符设备接口)")
    except Exception:
        logger.warning(
            "lgpio gpiochip 打开失败，回退到 RPi.GPIO。"
            "提示: 如在虚拟环境中，退出虚拟环境后可直接使用 RPi.GPIO。"
        )
        GPIO = _RPI_MOD if _RPI_MOD is not None else _MockGPIO()  # type: ignore[assignment]
elif _RPI_MOD is not None:
    GPIO = _RPI_MOD  # type: ignore[assignment]
    logger.info("GPIO 后端: RPi.GPIO (sysfs 接口)")
else:
    GPIO = _MockGPIO()  # type: ignore[assignment]
    logger.debug("GPIO 后端: Mock (无 GPIO 功能)")


def get_backend_info() -> dict[str, str]:
    """获取当前 GPIO 后端信息，用于调试和故障排查.

    Returns:
        包含 backend、lgpio_available、rpi_available、is_venv 等字段的字典.
    """
    info: dict[str, str] = {
        "backend": type(GPIO).__name__,
        "lgpio_available": str(_LGPIO_MOD is not None),
        "rpi_available": str(_RPI_MOD is not None),
        "is_venv": str(_is_venv()),
    }
    if _is_venv():
        info["hint"] = (
            "检测到虚拟环境，lgpio 已自动跳过。"
            "如需边沿检测支持，请退出虚拟环境使用系统 Python，"
            "或执行: sudo apt install python3-lgpio"
        )
    return info


# ═══════════════════════════════════════════════════════════════════════
# 上下文管理器
# ═══════════════════════════════════════════════════════════════════════


class GPIOContext(AbstractContextManager):
    """GPIO 资源管理上下文.

    确保 GPIO 资源在任何情况下都能被正确释放。
    支持重复调用 cleanup，不会产生副作用。

    Example:
        >>> with GPIOContext() as gpio:
        ...     gpio.setup(12, gpio.OUT)
        ...     gpio.output(12, gpio.HIGH)
    """

    def __init__(self) -> None:
        self._cleaned_up = False

    def __enter__(self) -> GPIOProvider:
        return GPIO

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> bool:
        self.cleanup()
        return False

    def cleanup(self) -> None:
        """清理 GPIO 资源，可重复调用."""
        if not self._cleaned_up:
            try:
                GPIO.cleanup()
            except Exception:
                logger.debug("GPIO cleanup 时发生异常", exc_info=True)
            finally:
                self._cleaned_up = True