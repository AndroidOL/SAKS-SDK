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

"""SAKS SDK 统一异常体系.

所有 SAKS SDK 抛出的异常均继承自 :class:`SAKSError`，
便于上层统一捕获和处理。

Example:
    >>> from sakshat import SAKSError, SAKSInitError
    >>> try:
    ...     saks = SAKSHAT()
    ... except SAKSInitError as e:
    ...     print(f"初始化失败: {e}")
"""

from __future__ import annotations


class SAKSError(Exception):
    """SAKS SDK 所有异常的基类."""


class SAKSGPIOError(SAKSError):
    """GPIO 操作失败时抛出.

    包括引脚初始化失败、读写失败、GPIO 库不可用等场景。
    """


class SAKSInitError(SAKSError):
    """外设初始化失败时抛出.

    包括 GPIO 初始化失败、芯片通信失败、传感器未就绪等场景。
    """


class SAKSHardwareError(SAKSError):
    """硬件通信异常时抛出.

    包括传感器读取失败、芯片通信超时、设备未连接等场景。
    """


class SAKSTimeoutError(SAKSError):
    """操作超时时抛出.

    包括传感器读取超时、线程等待超时等场景。
    """


class SAKSValidationError(SAKSError):
    """参数验证失败时抛出.

    包括无效引脚编号、超出范围的数据、非法的显示字符串等场景。
    """