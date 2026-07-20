#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAKS SDK 示例 12: DS18B20 温度传感器深度解析.

本示例深入讲解 DS18B20 数字温度传感器的工作原理、OneWire 协议、
数据格式解析、温度换算公式，以及 DS18B20 类的使用方法。

DS18B20 是 Maxim Integrated (原 Dallas Semiconductor) 生产的
数字温度传感器，采用 OneWire 单总线通信协议，仅需一根数据线即可
实现与主控的双向通信。

硬件要求: 树莓派 + SAKS 扩展板 + DS18B20 传感器
前置条件: 需要启用 OneWire 接口
    sudo modprobe w1-gpio
    sudo modprobe w1-therm

运行方式: python3 examples/12_ds18b20_deep_dive.py
"""

import time
import sys
import signal
import os
import glob

from sakshat import DS18B20, SAKSHardwareError


# ============================================================================
# 第一部分: DS18B20 传感器原理说明
# ============================================================================

def print_sensor_theory() -> None:
    """打印 DS18B20 传感器原理说明."""
    print("=" * 66)
    print("  DS18B20 数字温度传感器 - 深度解析")
    print("=" * 66)

    print("""
[1] 传感器概述
    DS18B20 是 Maxim Integrated 生产的数字温度传感器，采用
    OneWire (单总线) 通信协议，仅需一根数据线即可实现双向通信。

    核心特性:
    - 测温范围: -55°C 至 +125°C
    - 精度: ±0.5°C (在 -10°C 至 +85°C 范围内)
    - 分辨率: 9 位至 12 位可编程
    - 唯一 64 位 ROM 序列号，支持单总线上挂载多个传感器
    - 寄生供电模式，无需外部电源 (仅需数据线上拉)
    - 数字输出，无需 ADC 转换

[2] 精度说明

    分辨率与转换时间:
    +----------+----------+------------------+------------------+
    | 分辨率   | 位宽     | 最小分辨率        | 最大转换时间      |
    +----------+----------+------------------+------------------+
    | 9-bit    | 0.5°C    | 0.5°C            | 93.75 ms         |
    | 10-bit   | 0.25°C   | 0.25°C           | 187.5 ms         |
    | 11-bit   | 0.125°C  | 0.125°C          | 375 ms           |
    | 12-bit   | 0.0625°C | 0.0625°C         | 750 ms           |
    +----------+----------+------------------+------------------+

    默认分辨率: 12-bit，精度 0.0625°C

[3] 设备识别

    DS18B20 在 OneWire 总线上的设备文件以 "28-" 为前缀。
    这是由其家族码决定的: 0x28 代表 DS18B20。

    设备文件路径:
      /sys/bus/w1/devices/28-XXXXXXXXXXXX/w1_slave

    其中 28-XXXXXXXXXXXX 是传感器的唯一 64 位 ROM ID。

    其他常见 OneWire 设备前缀:
    - 28- : DS18B20 数字温度传感器
    - 10- : DS18S20 高精度温度传感器
    - 22- : DS1822 经济型温度传感器
    - 3B- : DS1825 带地址引脚的传感器

[4] 原始数据格式 (w1_slave 文件)

    读取 w1_slave 文件会得到两行数据:

    第一行 - CRC 校验行:
      XX XX XX XX XX XX XX XX XX : crc=XX YES

    第二行 - 温度数据行:
      XX XX XX XX XX XX XX XX XX t=XXXXX

    完整示例:
      25 01 4b 46 7f ff 0c 10 8e : crc=8e YES
      25 01 4b 46 7f ff 0c 10 8e t=28625

    字段说明:
    - 前 9 个字节: 传感器暂存器 (Scratchpad) 的十六进制数据
    - crc=XX: 循环冗余校验值
    - YES: 校验通过 (读取有效)
    - t=XXXXX: 原始温度值 (需除以 1000 得到摄氏度)

    暂存器字节布局:
    +--------+-------------------------------------+
    | 字节   | 内容                                 |
    +--------+-------------------------------------+
    | Byte 0 | 温度 LSB (低 8 位)                    |
    | Byte 1 | 温度 MSB (高 8 位)                    |
    | Byte 2 | TH 寄存器 (高温报警阈值)               |
    | Byte 3 | TL 寄存器 (低温报警阈值)               |
    | Byte 4 | 配置寄存器 (分辨率设置)                |
    | Byte 5 | 保留 (0xFF)                           |
    | Byte 6 | 保留 (0x0C 或 0x10)                    |
    | Byte 7 | 保留 (0x10)                            |
    | Byte 8 | CRC 校验值                             |
    +--------+-------------------------------------+

[5] 温度换算公式

    温度值 = 原始数据 t=XXXXX / 1000

    示例:
    t=28625  -> 28625 / 1000 = 28.625°C
    t=31250  -> 31250 / 1000 = 31.250°C
    t=-1000  -> -1000 / 1000 = -1.000°C
    t=0      -> 0 / 1000     = 0.000°C
    t=125000 -> 125000 / 1000 = 125.000°C

    华氏温度转换公式:
    F = C * 1.8 + 32
    F = C * 9.0 / 5.0 + 32.0

    示例:
    28.625°C -> 28.625 * 9.0 / 5.0 + 32.0 = 83.525°F

[6] 重试机制说明

    SAKS SDK 的 DS18B20 类内置了重试机制:
    - MAX_RETRIES = 10 (最大重试 10 次)
    - RETRY_DELAY  = 0.2 秒 (每次重试间隔 200ms)
    - 每次读取循环检查 CRC 校验是否通过 ("YES")
    - 如果 CRC 校验失败，等待 RETRY_DELAY 后重试
    - 重试次数超过 MAX_RETRIES 后返回 -128.0

    重试流程:
    +---> 读取 w1_slave
    |     |
    |     +---> 检查 CRC 是否 "YES"
    |     |     |
    |     |     +---> YES: 解析 t= 值，返回温度
    |     |     |
    |     |     +---> NO: 等待 0.2s，重试次数 +1
    |     |           |
    |     |           +---> 次数 < 10: 回到第一步
    |     |           +---> 次数 >= 10: 返回 -128.0
    |     |
    |     +---> 读取失败 (文件不存在/IO错误): 返回 -128.0

[7] 无效温度标记

    -128.0 是 SAKS SDK 的特殊标记值，表示温度读取失败。
    这个值远低于 DS18B20 的测温范围下限 (-55°C)，因此不会与
    真实温度值混淆。

    返回 -128.0 的可能原因:
    - 传感器未连接
    - OneWire 内核模块未加载
    - GPIO 引脚接线错误
    - 传感器故障
    - 通信干扰导致 CRC 持续校验失败
""")


# ============================================================================
# 第二部分: 传感器检测与基本读取
# ============================================================================

def demo_sensor_detection() -> None:
    """演示传感器检测和基本读取."""
    print("=" * 66)
    print("  DS18B20 传感器检测与基本读取")
    print("=" * 66)

    # 创建 DS18B20 实例
    sensor = DS18B20()
    print(f"\n创建传感器实例: {sensor!r}")

    # 检查传感器是否存在
    print("\n[1] is_exist 检测:")
    print(f"  >>> sensor.is_exist")
    exists = sensor.is_exist
    print(f"  = {exists}")

    if exists:
        print("  传感器已连接，可以读取温度数据")
    else:
        print("  传感器未检测到。请检查:")
        print("    1. 传感器是否正确连接到 GPIO4 (BCM 编号)")
        print("    2. OneWire 内核模块是否已加载")
        print("       sudo modprobe w1-gpio")
        print("       sudo modprobe w1-therm")
        print("    3. 设备文件是否存在于 /sys/bus/w1/devices/")

    # 列出所有检测到的 OneWire 设备
    print("\n[2] 系统中的 OneWire 设备:")
    base_dir = "/sys/bus/w1/devices/"
    if os.path.isdir(base_dir):
        devices = sorted(glob.glob(os.path.join(base_dir, "28-*")))
        if devices:
            for i, dev in enumerate(devices):
                dev_id = os.path.basename(dev)
                print(f"  传感器 [{i}]: {dev_id}")
        else:
            print("  未找到任何 28- 前缀的设备")
    else:
        print(f"  {base_dir} 目录不存在，OneWire 可能未启用")

    # 读取温度
    print("\n[3] temperature 读取演示:")
    print("  >>> sensor.temperature")
    temp = sensor.temperature
    print(f"  = {temp}")

    if temp != -128.0:
        print(f"  当前温度: {temp:.4f}°C")
        print(f"  当前温度: {temp:.1f}°C (保留一位小数)")
    else:
        print("  温度读取失败 (传感器未连接或通信异常)")

    # 华氏温度
    print("\n[4] get_temperature_f() 华氏温度:")
    print("  >>> sensor.get_temperature_f()")
    temp_f = sensor.get_temperature_f()
    print(f"  = {temp_f}")

    if temp_f != -128.0:
        print(f"  当前温度: {temp_f:.2f}°F")
        print(f"  换算验证: {temp:.4f}°C * 9/5 + 32 = {temp_f:.2f}°F")
    else:
        print("  华氏温度读取失败")


# ============================================================================
# 第三部分: 原始数据格式解析
# ============================================================================

def demo_raw_data_parsing() -> None:
    """演示原始数据格式解析."""
    print("\n" + "=" * 66)
    print("  原始数据格式解析")
    print("=" * 66)

    print("""
[1] w1_slave 文件格式

    每次读取 w1_slave 文件会返回两行数据:

    第一行: 暂存器数据 + CRC 校验状态
    格式: HH HH HH HH HH HH HH HH HH : crc=XX YES/NO

    第二行: 暂存器数据 + 温度原始值
    格式: HH HH HH HH HH HH HH HH HH t=XXXXX

[2] 模拟数据解析示例

    假设 w1_slave 内容为:
    """)

    # 模拟原始数据
    raw_line1 = "25 01 4b 46 7f ff 0c 10 8e : crc=8e YES"
    raw_line2 = "25 01 4b 46 7f ff 0c 10 8e t=28625"

    print(f"    第一行: {raw_line1}")
    print(f"    第二行: {raw_line2}")

    # 解析演示
    print("\n    解析步骤:")
    print("    ---------------------------------------------------")

    # 解析暂存器
    scratchpad_hex = raw_line1.split(":")[0].strip().split()
    print(f"    暂存器数据 (hex): {scratchpad_hex}")

    # 温度 LSB 和 MSB
    temp_lsb = int(scratchpad_hex[0], 16)
    temp_msb = int(scratchpad_hex[1], 16)
    print(f"    Byte 0 (温度 LSB): 0x{temp_lsb:02X} = {temp_lsb}")
    print(f"    Byte 1 (温度 MSB): 0x{temp_msb:02X} = {temp_msb}")

    # 温度计算 (12-bit 模式)
    temp_raw = (temp_msb << 8) | temp_lsb
    if temp_raw > 0x7FFF:
        temp_raw = temp_raw - 0x10000  # 负温度处理
    temp_c = temp_raw / 16.0  # 12-bit 分辨率
    print(f"    原始温度值: {temp_raw} (组合: MSB<<8 | LSB)")
    print(f"    温度 (12-bit): {temp_raw} / 16 = {temp_c}°C")

    # CRC 检查
    crc_status = raw_line1.split("crc=")[1].split()[0]
    print(f"    CRC 状态: {crc_status}")

    # 温度行解析
    t_pos = raw_line2.find("t=")
    temp_raw_str = raw_line2[t_pos + 2:]
    temp_from_t = int(temp_raw_str) / 1000.0
    print(f"    t= 值: {temp_raw_str}")
    print(f"    温度 (sysfs): {temp_raw_str} / 1000 = {temp_from_t}°C")
    print(f"    温度 (sysfs): {temp_from_t:.4f}°C")
    print(f"    温度 (sysfs): {temp_from_t:.1f}°C (保留一位小数)")

    print("\n    总结: t=XXXXX / 1000 得到摄氏温度值")

    # 更多温度换算示例
    print("\n[3] 温度换算示例表:")
    print("    +-----------+-----------+-----------+-----------+")
    print("    | t=XXXXX   | 原始值    | 摄氏度    | 华氏度    |")
    print("    +-----------+-----------+-----------+-----------+")

    examples = [
        (28625, "28.625°C", "83.525°F"),
        (31250, "31.250°C", "88.250°F"),
        (25000, "25.000°C", "77.000°F"),
        (0, "0.000°C", "32.000°F"),
        (-1000, "-1.000°C", "30.200°F"),
        (-5500, "-5.500°C", "22.100°F"),
        (100000, "100.000°C", "212.000°F"),
        (-55000, "-55.000°C", "-67.000°F"),
        (125000, "125.000°C", "257.000°F"),
    ]
    for t_val, c_str, f_str in examples:
        print(f"    | {t_val:>9} | {t_val:>9} | {c_str:>9} | {f_str:>9} |")
    print("    +-----------+-----------+-----------+-----------+")


# ============================================================================
# 第四部分: 多点传感器 (多索引)
# ============================================================================

def demo_multi_sensor() -> None:
    """演示多传感器支持."""
    print("\n" + "=" * 66)
    print("  多点传感器 (多索引) 支持")
    print("=" * 66)

    print("""
[1] OneWire 总线多传感器架构

    DS18B20 支持在单根 OneWire 总线上挂载多个传感器。
    每个传感器有唯一的 64 位 ROM ID，主控通过 ROM 命令
    选择特定传感器进行通信。

    物理连接:
    +-----+     +--------------+     +--------------+     +--------------+
    |     |     |  DS18B20 #0  |     |  DS18B20 #1  |     |  DS18B20 #2  |
    | RPi |-----|  ROM: 28-... |-----|  ROM: 28-... |-----|  ROM: 28-... |
    |     |     +--------------+     +--------------+     +--------------+
    +-----+          |                      |                      |
       |             +----------------------+----------------------+
       |                                |
       +-- 4.7K 上拉电阻到 3.3V -------+

    软件层面:
    /sys/bus/w1/devices/
      +-- 28-000005e2f1a3/
      |     +-- w1_slave
      +-- 28-000005e2f8b7/
      |     +-- w1_slave
      +-- 28-000005e3011c/
            +-- w1_slave

    SAKS SDK 通过 index 参数区分不同传感器:
    - index=0: 第一个传感器 (按设备 ID 字母排序)
    - index=1: 第二个传感器
    - index=2: 第三个传感器
""")

    # 创建传感器实例
    sensor = DS18B20()

    # 检测所有传感器
    print("[2] 扫描传感器:")
    base_dir = "/sys/bus/w1/devices/"
    if os.path.isdir(base_dir):
        devices = sorted(glob.glob(os.path.join(base_dir, "28-*")))
        if devices:
            print(f"  检测到 {len(devices)} 个传感器:")
            for i, dev in enumerate(devices):
                dev_id = os.path.basename(dev)
                print(f"    [{i}] {dev_id}")

            # 读取每个传感器的温度
            print(f"\n[3] 读取所有传感器温度 (使用 index 参数):")
            for i in range(len(devices)):
                print(f"  >>> sensor.temperature (index={i})")
                temp = sensor._read_temp(index=i)
                temp_f = sensor.get_temperature_f(index=i)
                if temp != -128.0:
                    print(f"  传感器 [{i}] ({devices[i]}): {temp:.4f}°C / {temp_f:.2f}°F")
                else:
                    print(f"  传感器 [{i}] ({devices[i]}): 读取失败")
                time.sleep(0.2)
        else:
            print("  未检测到任何传感器 (模拟演示)")
            print("\n[3] 多索引演示 (模拟):")
            print("  假设有 3 个传感器，分别通过 index=0,1,2 读取:")
            for idx in range(3):
                print(f"  >>> sensor._read_temp(index={idx})")
                print(f"  >>> sensor.get_temperature_f(index={idx})")
                print(f"  传感器 [{idx}]: temperature / temperature_f")
    else:
        print(f"  {base_dir} 目录不存在")
        print("  多传感器功能需要在已启用 OneWire 的树莓派上运行")


# ============================================================================
# 第五部分: 重试机制与错误处理
# ============================================================================

def demo_retry_and_error_handling() -> None:
    """演示重试机制和错误处理."""
    print("\n" + "=" * 66)
    print("  重试机制与错误处理")
    print("=" * 66)

    print("""
[1] 重试机制详解

    SAKS SDK 内置了完整的重试机制:

    参数:
    - _MAX_RETRIES = 10  (最大重试次数)
    - _RETRY_DELAY  = 0.2 秒 (每次重试间隔)
    - _INVALID_TEMP = -128.0 (无效温度标记)

    重试触发条件:
    1. 读取 w1_slave 文件失败 (IO 错误)
    2. CRC 校验未通过 (第一行不以 "YES" 结尾)

    重试流程图:
    +-----------+
    | 开始读取   |
    +-----------+
          |
          v
    +-----------+
    | 打开文件   |--失败--> 返回 -128.0
    +-----------+
          |
          v
    +-----------+
    | 读取两行   |--失败--> 重试 (次数+1)
    +-----------+
          |
          v
    +------------------+
    | CRC 校验 = YES?  |
    +------------------+
       |           |
      是          否
       |           |
       v           v
    +--------+  +--------+
    | 解析 t= |  | 重试    |
    +--------+  +--------+
       |           |
       v           v
    +--------+  次数>=10?
    | 返回温度 |   |     |
    +--------+  是    否
                 |     |
                 v     v
              -128.0  等待 0.2s -> 重新读取

[2] 错误处理: 传感器未连接时

    当传感器未连接时:
    - is_exist 返回 False
    - temperature 返回 -128.0
    - get_temperature_f() 返回 -128.0
    - 不会抛出异常 (静默处理)
""")

    # 创建传感器实例
    sensor = DS18B20()

    print("[3] 实际测试:")
    print(f"  >>> sensor.is_exist = {sensor.is_exist}")

    if not sensor.is_exist:
        print("""
  传感器未连接时的行为:
  - sensor.temperature 返回 -128.0
  - sensor.get_temperature_f() 返回 -128.0
  - 不会抛出异常，程序可以继续运行

  建议的处理模式:
  >>> if sensor.is_exist:
  ...     temp = sensor.temperature
  ...     if temp != -128.0:
  ...         print(f"温度: {temp:.1f}°C")
  ... else:
  ...     print("传感器未连接，请检查接线")
""")
    else:
        print("  传感器已连接，正常模式")

    # 演示错误处理代码模式
    print("\n[4] 推荐的错误处理模式:")
    print("""
    # 模式 1: 先检查再读取
    sensor = DS18B20()
    if sensor.is_exist:
        temp = sensor.temperature
        if temp != -128.0:
            print(f"温度: {temp:.1f}°C")
        else:
            print("读取失败，请重试")
    else:
        print("传感器未连接")

    # 模式 2: try-except 捕获异常
    try:
        temp = sensor.temperature
        if temp == -128.0:
            raise SAKSHardwareError("温度读取失败")
        print(f"温度: {temp:.1f}°C")
    except SAKSHardwareError as e:
        print(f"硬件错误: {e}")

    # 模式 3: 带重试的应用层封装
    def read_temp_with_retry(sensor, max_retries=3):
        for _ in range(max_retries):
            temp = sensor.temperature
            if temp != -128.0:
                return temp
            time.sleep(1.0)
        return None

    temp = read_temp_with_retry(sensor)
    if temp is not None:
        print(f"温度: {temp:.1f}°C")
    else:
        print("多次重试后仍无法读取温度")
""")


# ============================================================================
# 第六部分: 综合演示
# ============================================================================

def demo_comprehensive() -> None:
    """综合演示: 连续温度监测."""
    print("\n" + "=" * 66)
    print("  综合演示: 连续温度监测")
    print("=" * 66)

    sensor = DS18B20()

    print("\n[1] 传感器状态检查:")
    print(f"  is_exist: {sensor.is_exist}")
    print(f"  实例信息: {sensor!r}")

    if sensor.is_exist:
        print("\n[2] 连续读取温度 (3 次, 间隔 1 秒):")
        print("  +--------+-----------+-----------+")
        print("  | 次数   | 摄氏度    | 华氏度    |")
        print("  +--------+-----------+-----------+")

        for i in range(1, 4):
            temp_c = sensor.temperature
            temp_f = sensor.get_temperature_f()
            if temp_c != -128.0:
                print(f"  | {i:^6} | {temp_c:>8.3f} | {temp_f:>8.3f} |")
            else:
                print(f"  | {i:^6} | 读取失败  | 读取失败  |")
            time.sleep(1.0)
        print("  +--------+-----------+-----------+")
    else:
        print("\n[2] 传感器未连接，模拟温度数据演示:")
        print("""
  模拟数据演示 (假设传感器已连接):

  正常读取示例:
  +--------+-----------+-----------+--------------+
  | 次数   | t=XXXXX   | 摄氏度    | 华氏度        |
  +--------+-----------+-----------+--------------+
  |   1    |    28625  |  28.625°C |   83.525°F   |
  |   2    |    28500  |  28.500°C |   83.300°F   |
  |   3    |    28650  |  28.650°C |   83.570°F   |
  +--------+-----------+-----------+--------------+

  异常情况示例:
  +--------+-----------+-----------+-------------------+
  | 次数   | 状态      | 返回值    | 说明               |
  +--------+-----------+-----------+-------------------+
  |   1    | 正常      | 28.625    | CRC 校验通过       |
  |   2    | CRC 失败  | 重试中... | 第 1 次 CRC 失败   |
  |   2    | 重试成功  | 28.500    | 第 2 次读取成功    |
  |   3    | 传感器断开| -128.0    | 读取失败           |
  +--------+-----------+-----------+-------------------+
""")

    # 温度范围和精度总结
    print("\n[3] DS18B20 温度范围与精度总结:")
    print("""
  +------------------+------------------+------------------+
  | 参数             | 最小值           | 最大值           |
  +------------------+------------------+------------------+
  | 测温范围         | -55°C            | +125°C           |
  | 精度 (-10~85°C)  | -0.5°C           | +0.5°C           |
  | 精度 (全范围)    | -2.0°C           | +2.0°C           |
  | 分辨率 (12-bit)  | 0.0625°C         | 0.0625°C         |
  | 转换时间 (12-bit)| 750ms            | 750ms            |
  | 供电电压         | 3.0V             | 5.5V             |
  +------------------+------------------+------------------+

  SAKS SDK 特殊值:
  -128.0 = 无效温度 (传感器断开/读取失败/CRC 校验失败)
""")


# ============================================================================
# 主函数
# ============================================================================

def main() -> None:
    """主函数."""
    print_sensor_theory()
    demo_sensor_detection()
    demo_raw_data_parsing()
    demo_multi_sensor()
    demo_retry_and_error_handling()
    demo_comprehensive()

    print("\n" + "=" * 66)
    print("  DS18B20 深度解析示例完成!")
    print("=" * 66)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    main()