#!/usr/bin/env python3
"""
模块安装器 for Magisk/KernelSU/APatch
通过 ADB 在已 root 的 Android 设备上安装模块
"""

import argparse
import os
import sys
import subprocess
import tempfile
import zipfile
import re
import shutil
import time
from pathlib import Path
from typing import List, Optional, Tuple, Dict

# ANSI 颜色代码
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'  # No Color

class ModuleInstaller:
    """Magisk/KernelSU/APatch 模块安装器"""
    
    def __init__(self, module_path: str, device_serial: Optional[str] = None):
        self.module_path = Path(module_path)
        self.device_serial = device_serial
        self.root_method = None
        self.device = None
        self.module_info = {}
        
    def ui_print(self, text: str) -> None:
        """打印成功/信息消息"""
        print(f"{Colors.GREEN}{text}{Colors.NC}")
    
    def ui_error(self, text: str) -> None:
        """打印错误消息"""
        print(f"{Colors.RED}{text}{Colors.NC}")
    
    def ui_warning(self, text: str) -> None:
        """打印警告消息"""
        print(f"{Colors.YELLOW}{text}{Colors.NC}")
    
    def ui_info(self, text: str) -> None:
        """打印信息消息"""
        print(f"{Colors.BLUE}{text}{Colors.NC}")
    
    def ui_output(self, text: str) -> None:
        """打印原始输出（用于显示命令输出）"""
        print(f"{Colors.CYAN}{text}{Colors.NC}")
    
    def ui_title(self, text: str) -> None:
        """打印标题"""
        print(f"{Colors.MAGENTA}{text}{Colors.NC}")
    
    def print_title(self, title: str, subtitle: str = "") -> None:
        """打印标题框"""
        # 计算中文字符长度（中文算2个字符宽度）
        def get_display_len(text: str) -> int:
            """获取字符串显示宽度（中文算2，英文算1）"""
            length = 0
            for char in text:
                if '\u4e00' <= char <= '\u9fff':  # 中文字符范围
                    length += 2
                else:
                    length += 1
            return length
        
        title_len = get_display_len(title)
        sub_len = get_display_len(subtitle) if subtitle else 0
        max_len = max(title_len, sub_len) + 2
        bar = "*" * max_len
        
        self.ui_print(bar)
        self.ui_print(f" {title} ")
        if subtitle:
            self.ui_print(f" {subtitle} ")
        self.ui_print(bar)
    
    def print_module_info(self) -> None:
        """打印模块详细信息"""
        if not self.module_info:
            return
        
        self.ui_title("════════════════════════════════════════════════════════════")
        self.ui_title("                           模块信息                           ")
        self.ui_title("════════════════════════════════════════════════════════════")
        
        # 模块 ID
        if self.module_info.get('id'):
            print(f"  {Colors.CYAN}模块 ID:{Colors.NC} {self.module_info['id']}")
        
        # 模块名称
        if self.module_info.get('name'):
            print(f"  {Colors.CYAN}模块名称:{Colors.NC} {self.module_info['name']}")
        
        # 版本信息
        version_str = ""
        if self.module_info.get('version'):
            version_str += f"版本: {self.module_info['version']}"
        if self.module_info.get('versionCode'):
            if version_str:
                version_str += f" ({self.module_info['versionCode']})"
            else:
                version_str += f"版本号: {self.module_info['versionCode']}"
        if version_str:
            print(f"  {Colors.CYAN}{version_str}{Colors.NC}")
        
        # 作者
        if self.module_info.get('author'):
            print(f"  {Colors.CYAN}作者:{Colors.NC} {self.module_info['author']}")
        
        # 简介
        if self.module_info.get('description'):
            print(f"  {Colors.CYAN}简介:{Colors.NC}")
            # 格式化简介，每行不超过 60 个字符
            desc = self.module_info['description']
            words = desc.split()
            line = "    "
            for word in words:
                if len(line + word) > 64:  # 每行最多 60 字符加上缩进
                    print(line)
                    line = "    " + word
                else:
                    if line == "    ":
                        line += word
                    else:
                        line += " " + word
            if line != "    ":
                print(line)
        
        # 更新配置
        if self.module_info.get('updateJson'):
            print(f"  {Colors.CYAN}更新配置:{Colors.NC}")
            print(f"    {self.module_info['updateJson']}")
        
        # 其他可选字段
        
        if self.module_info.get('support'):
            print(f"  {Colors.CYAN}技术支持:{Colors.NC} {self.module_info['support']}")
        
        print()
    
    def abort(self, message: str) -> None:
        """终止脚本并显示错误"""
        self.ui_error(f"✗ {message}")
        sys.exit(1)
    
    def run_adb(self, args: List[str], check: bool = True, capture: bool = True) -> Optional[subprocess.CompletedProcess]:
        """执行 ADB 命令"""
        cmd = ["adb"]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        
        try:
            if capture:
                # 在 Windows 下使用 utf-8 编码
                if sys.platform == 'win32':
                    result = subprocess.run(cmd, capture_output=True, text=True, 
                                          encoding='utf-8', errors='ignore', check=check)
                else:
                    result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            else:
                # 不捕获输出，直接显示到终端
                # 设置编码为 utf-8 避免解码错误
                if sys.platform == 'win32':
                    result = subprocess.run(cmd, check=check, encoding='utf-8', errors='ignore')
                else:
                    result = subprocess.run(cmd, check=check)
            return result
        except subprocess.CalledProcessError as e:
            if check:
                self.abort(f"ADB 命令执行失败: {' '.join(cmd)}\n错误: {e.stderr}")
            return e
        except FileNotFoundError:
            self.abort("未找到 ADB 命令，请确保已安装 Android Debug Bridge 并添加到 PATH")
        except Exception as e:
            if check:
                self.abort(f"执行命令时出错: {e}")
            return None
    
    def run_su(self, command: str, check: bool = True, capture: bool = True) -> Optional[subprocess.CompletedProcess]:
        """以 root 权限执行命令"""
        return self.run_adb(["shell", "su", "-c", command], check, capture)
    
    def check_adb(self) -> None:
        """检查 ADB 是否可用"""
        try:
            subprocess.run(["adb", "version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.abort("未找到 ADB 命令，请确保已安装 Android Debug Bridge 并添加到 PATH")
    
    def get_devices(self) -> List[str]:
        """获取已连接的设备列表"""
        result = self.run_adb(["devices"], check=False)
        if not result or not result.stdout:
            return []
        
        devices = []
        for line in result.stdout.split('\n'):
            # 匹配设备序列号和状态
            match = re.match(r'^([a-zA-Z0-9_.:-]+)\s+device$', line.strip())
            if match:
                devices.append(match.group(1))
        
        return devices
    
    def select_device(self) -> str:
        """选择要使用的设备"""
        devices = self.get_devices()
        
        if not devices:
            self.abort("未检测到设备，请连接您的 Android 设备")
        
        if len(devices) == 1 and not self.device_serial:
            self.ui_info(f"✓ 检测到设备: {devices[0]}")
            return devices[0]
        
        if self.device_serial:
            # 检查指定的设备是否存在（支持部分匹配）
            if self.device_serial in devices:
                return self.device_serial
            
            # 如果没有精确匹配，尝试找到包含指定字符串的设备
            matches = [d for d in devices if self.device_serial in d]
            if len(matches) == 1:
                self.ui_warning(f"⚠ 使用设备: {matches[0]} (匹配自 '{self.device_serial}')")
                return matches[0]
            elif len(matches) > 1:
                self.ui_error(f"✗ 有多个设备匹配 '{self.device_serial}':")
                for match in matches:
                    print(f"  {match}")
                self.abort("请指定完整的设备序列号")
            else:
                self.abort(f"未找到设备 '{self.device_serial}'")
        
        # 多个设备且未指定
        self.ui_error("检测到多个设备:")
        for i, device in enumerate(devices, 1):
            print(f"  {i}. {device}")
        self.abort("请使用 -d 参数指定设备序列号")
    
    def check_root_method(self) -> str:
        """检查 root 方法和权限"""
        self.ui_info("正在检查 root 权限...")
        
        # 测试 root 权限
        result = self.run_su("echo test", check=False)
        if not result or "test" not in (result.stdout or ""):
            self.abort("设备未 root 或 root 权限被拒绝")
        
        self.ui_info("✓ Root 权限验证通过")
        
        # 检查 APatch
        result = self.run_su("which apd", check=False)
        if result and result.stdout and "apd" in result.stdout:
            version_result = self.run_su("apd -V", check=False)
            version = (version_result.stdout or "").split('\n')[0].strip()
            self.ui_info(f"✓ 检测到 APatch: {version}")
            return "APatch"
        
        # 检查 Magisk
        result = self.run_su("which magisk", check=False)
        if result and result.stdout and "magisk" in result.stdout:
            version_result = self.run_su("magisk -v", check=False)
            version = (version_result.stdout or "").split('\n')[0].strip()
            self.ui_info(f"✓ 检测到 Magisk: {version}")
            return "Magisk"
        
        # 检查 KernelSU
        result = self.run_su("which ksud", check=False)
        if result and result.stdout and "ksud" in result.stdout:
            version_result = self.run_su("ksud -V", check=False)
            version = (version_result.stdout or "").split('\n')[0].strip()
            self.ui_info(f"✓ 检测到 KernelSU: {version}")
            return "KernelSU"
        
        self.abort("设备已 root，但未找到 Magisk、KernelSU 或 APatch")
    
    def parse_module_prop(self, content: str) -> Dict[str, str]:
        """解析 module.prop 文件内容"""
        info = {}
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                info[key] = value
        
        return info
    
    def validate_module(self) -> Tuple[bool, Optional[str]]:
        """验证模块文件，返回 (是否成功, 模块ID)"""
        if not self.module_path.exists():
            self.abort(f"模块文件不存在: {self.module_path}")
        
        if not self.module_path.suffix.lower() == '.zip':
            self.ui_warning("⚠ 警告: 文件扩展名不是 .zip")
        
        module_id = None
        
        # 检查 ZIP 文件完整性
        try:
            with zipfile.ZipFile(self.module_path, 'r') as zip_ref:
                # 测试 ZIP 文件完整性
                bad_file = zip_ref.testzip()
                if bad_file:
                    self.abort(f"ZIP 文件损坏: {bad_file} 已损坏")
                
                # 检查 module.prop
                if 'module.prop' not in zip_ref.namelist():
                    self.abort("无效的模块: 在 ZIP 根目录未找到 module.prop")
                
                # 读取模块信息
                with zip_ref.open('module.prop') as prop_file:
                    content = prop_file.read().decode('utf-8', errors='ignore')
                    self.module_info = self.parse_module_prop(content)
                    
                    # 提取常用字段
                    module_id = self.module_info.get('id')
                    module_name = self.module_info.get('name')
                    module_version = self.module_info.get('version')
                    module_version_code = self.module_info.get('versionCode')
                    module_author = self.module_info.get('author')
                    module_description = self.module_info.get('description')
                    module_update_json = self.module_info.get('updateJson')
                    
                    # 显示模块信息
                    self.print_module_info()
        
        except zipfile.BadZipFile:
            self.abort("无效或损坏的 ZIP 文件")
        except Exception as e:
            self.abort(f"验证模块失败: {e}")
        
        return True, module_id
    
    def push_module(self) -> None:
        """推送模块到设备"""
        self.ui_info("正在推送模块到设备...")
        
        # 创建临时目录
        cache_dir = Path.home() / ".cache" / "module_installer"
        cache_dir.mkdir(parents=True, exist_ok=True)
        temp_zip = cache_dir / "module.zip"
        
        try:
            # 复制模块文件
            shutil.copy2(self.module_path, temp_zip)
            
            # 清理设备上的旧文件
            self.run_adb(["shell", "rm", "-rf", "/data/local/tmp/module.zip"], check=False)
            
            # 推送新文件
            result = self.run_adb(["push", str(temp_zip), "/data/local/tmp/module.zip"], check=False)
            if not result or result.returncode != 0:
                self.abort("推送模块到设备失败")
            
            self.ui_info("✓ 模块推送成功")
        
        finally:
            # 清理临时文件
            if temp_zip.exists():
                temp_zip.unlink()
    
    def get_module_id_from_device(self) -> Optional[str]:
        """从设备获取模块 ID"""
        return self.module_info.get('id')
    
    def install_module(self, module_id: Optional[str]) -> None:
        """安装模块并显示原始输出"""
        print()  # 添加空行
        self.ui_info(f"正在使用 {self.root_method} 安装模块...")
        self.ui_info("=" * 50)
        
        if self.root_method == "KernelSU":
            self.ui_output("执行命令: /data/adb/ksud module install /data/local/tmp/module.zip")
            print()  # 添加空行
            
            # 不捕获输出，直接显示到终端
            self.run_su("/data/adb/ksud module install /data/local/tmp/module.zip", 
                       check=False, capture=False)
        elif self.root_method == "APatch":
            self.ui_output("执行命令: /data/adb/apd module install /data/local/tmp/module.zip")
            print()  # 添加空行
            
            # 不捕获输出，直接显示到终端
            self.run_su("/data/adb/apd module install /data/local/tmp/module.zip", 
                       check=False, capture=False)
        else:
            self.ui_output("执行命令: magisk --install-module /data/local/tmp/module.zip")
            print()  # 添加空行
            
            # 不捕获输出，直接显示到终端
            self.run_su("magisk --install-module /data/local/tmp/module.zip", 
                       check=False, capture=False)
        
        self.ui_info("=" * 50)
        print()  # 添加空行
        
        # 清理临时文件
        self.run_adb(["shell", "rm", "-rf", "/data/local/tmp/module.zip"], check=False)
        
        # 等待安装完成
        time.sleep(2)
        
        # 检查安装结果
        self.ui_info("正在检查安装结果...")
        
        # 获取模块 ID 用于检查
        if not module_id:
            module_id = self.get_module_id_from_device()
        
        if module_id:
            # 检查模块是否已安装
            if self.root_method == "KernelSU":
                result = self.run_su("/data/adb/ksud module list", check=False)
                output = result.stdout if result and result.stdout else ""
            elif self.root_method == "APatch":
                result = self.run_su("/data/adb/apd module list", check=False)
                output = result.stdout if result and result.stdout else ""
            else:
                result = self.run_su("magisk --list", check=False)
                output = result.stdout if result and result.stdout else ""
            
            if module_id in output:
                self.ui_print("✓ 模块安装成功！")
                self.ui_warning("⚠ 请重启设备以应用更改")
            else:
                self.ui_warning("⚠ 模块可能未成功安装，请检查上面的错误信息")
                if "Failed to request license" in output or "license" in output.lower():
                    self.ui_warning("提示: 此模块需要联网验证授权，请确保设备已连接互联网")
                elif "magisk: not found" in output:
                    self.ui_warning(f"提示: 此模块可能需要 Magisk 环境，但当前使用的是 {self.root_method}")
                elif "ksud: not found" in output:
                    self.ui_warning(f"提示: 此模块可能需要 KernelSU 环境，但当前使用的是 {self.root_method}")
                elif "apd: not found" in output:
                    self.ui_warning(f"提示: 此模块可能需要 APatch 环境，但当前使用的是 {self.root_method}")
        else:
            self.ui_warning("⚠ 无法获取模块 ID 进行验证，请手动检查安装结果")
            self.ui_warning("如果看到错误信息，请根据错误提示解决问题")
    
    def ask_reboot(self) -> None:
        """询问是否重启设备"""
        print()
        response = input("是否现在重启设备？(y/N): ").strip().lower()
        
        if response in ['y', 'yes']:
            self.ui_info("正在重启设备...")
            self.run_adb(["reboot"], check=False)
            self.ui_print("✓ 设备正在重启，请等待设备重新启动")
        else:
            self.ui_info("请记得手动重启设备以应用模块更改")
    
    def confirm_installation(self) -> bool:
        """确认是否继续安装"""
        print()
        response = input("确认继续安装？(y/N): ").strip().lower()
        return response in ['y', 'yes']
    
    def run(self) -> None:
        """执行安装流程"""
        # 清屏
        os.system('clear' if os.name == 'posix' else 'cls')
        
        # 打印标题
        self.print_title("ModuleInstaller", "Magisk/KernelSU/APatch 模块安装工具")
        
        # 检查 ADB
        self.check_adb()
        
        # 验证模块（会显示模块信息）
        success, module_id = self.validate_module()
        if not success:
            return
        
        # 选择设备
        self.device = self.select_device()
        self.ui_info(f"当前设备: {self.device}")
        
        # 检查 root 方法
        self.root_method = self.check_root_method()
        # self.ui_info(f"Root 方式: {self.root_method}")
        
        # 确认安装
        if not self.confirm_installation():
            self.abort("用户取消安装")
        
        # 推送模块
        self.push_module()
        
        # 安装模块
        self.install_module(module_id)
        
        # 询问重启
        self.ask_reboot()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Magisk/KernelSU/APatch 模块安装器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python %(prog)s <ZipPath>                         # 在单个设备上安装
  python %(prog)s <ZipPath> -d 1234567890ABCDEF     # 在指定 USB 设备上安装
  python %(prog)s <ZipPath> -d 192.168.1.2:5555    # 在指定无线设备上安装
  python %(prog)s <ZipPath> -d www.baidu.com:5555  # 使用域名指定无线设备

环境要求:
  - 已安装 ADB 并添加到 PATH
  - 设备已连接并授权
  - 设备已 root (Magisk、KernelSU 或 APatch)
        """
    )
    
    parser.add_argument(
        'ZipPath',
        nargs='?',
        help='Magisk/KernelSU/APatch 模块 ZIP 文件路径'
    )
    
    parser.add_argument(
        '-d', '--device',
        help='ADB 设备序列号（支持 USB 和无线设备）'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='模块安装器 v2.1 (Python)',
        help='显示版本信息'
    )
    
    args = parser.parse_args()
    
    # 检查是否提供了模块文件
    if not args.ZipPath:
        parser.print_help()
        sys.exit(1)
    
    # 创建安装器并运行
    installer = ModuleInstaller(args.ZipPath, args.device)
    installer.run()


if __name__ == "__main__":
    main()