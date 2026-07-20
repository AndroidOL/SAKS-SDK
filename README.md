# SAKS-SDK

树莓派瑞士军刀扩展板 (SAKS) 的 Python SDK，基于面向对象设计，封装了所有硬件操作逻辑。

## 快速安装

```bash
# 从 PyPI 安装
pip install sakshat

# 从源码安装
git clone https://github.com/spoonysonny/SAKS-SDK.git
cd SAKS-SDK
pip install -e .
```

> **注意**: 如在虚拟环境中使用，拨码开关和轻触开关的边沿检测（硬件中断）可能不可用，SDK 将自动降级为轮询模式。
> 如需完整边沿检测支持，请使用系统 Python 环境，或执行 `sudo apt install python3-lgpio` 安装 lgpio 系统包。
> 详情参见 [完整文档](doc/README.md#虚拟环境注意事项)。

## 快速开始

```python
from sakshat import SAKSHAT

with SAKSHAT() as saks:
    saks.buzzer.beep(0.5)
    saks.ledrow.set_row([True, False, True, False, True, False, True, False])
    saks.digital_display.show("12.34")
    print(f"温度: {saks.ds18b20.temperature:.1f}°C")
```

## 硬件要求

- 树莓派 3B/3B+/4B/5（或其他 40-pin GPIO 型号）
- SAKS 扩展板（瑞士军刀扩展板）
- DS18B20 温度传感器（可选）

## 文档

| 文档 | 说明 |
|------|------|
| [README](doc/README.md) | 完整项目说明与功能特性 |
| [API 参考](doc/API.md) | 完整 API 参考文档 |
| [变更日志](doc/CHANGELOG.md) | 版本变更历史 |
| [迁移指南](doc/MIGRATION.md) | 从 v0.x 迁移到 v2.x |
| [项目结构](doc/PROJECT_STRUCTURE.md) | 项目目录结构说明 |

## 许可证

GPL v2.0