import io
import os
import time
import socket
import threading
from typing import Dict, Callable, Optional, List, Union, Tuple, Any
import paramiko
from tqdm import tqdm
from paramiko.ssh_exception import SSHException, AuthenticationException

from .basic import set_logging
from .constants import TIMEOUT, RETRY_TIMES


class SFTPClient:
    """
    SFTP客户端类，提供安全的文件传输协议操作

    支持多服务器配置管理、断点续传、进度监控、错误重试等功能。
    适用于需要安全可靠地进行文件上传下载的场景。

    Features:
        - ✅ 多服务器配置管理
        - ✅ 连接池和自动重连
        - ✅ 断点续传（上传/下载）
        - ✅ 进度监控和可视化
        - ✅ 批量文件传输
        - ✅ 递归目录操作
        - ✅ 文件完整性验证
        - ✅ 指数退避重试机制
        - ✅ 分批处理避免连接超时

    Example:
        >>> # 初始化SFTP客户端
        >>> sftp_configs = {
        ...     "sftp_server1": {
        ...         "host": "10.141.1.120",
        ...         "port": 22,
        ...         "username": "root",
        ...         "password": "admin"
        ...     },
        ...     "sftp_server2": {
        ...         "host": "10.141.1.121",
        ...         "port": 22,
        ...         "username": "user",
        ...         "password": "pass123"
        ...     }
        ... }
        >>> client = SFTPClient(sftp_configs, verbose=True)
        >>>
        >>> # 检查连接
        >>> if client.is_connected("sftp_server1"):
        ...     print("连接正常")
        >>>
        >>> # 批量下载文件
        >>> remote_files = ["/remote/file1.txt", "/remote/file2.jpg"]
        >>> success, total = client.download_file_list(
        ...     sftp_name="sftp_server1",
        ...     remote_path_list=remote_files,
        ...     local_path_list="/local/downloads",
        ...     batch_size=20
        ... )
        >>> print(f"下载完成: {success}/{total}")
        >>>
        >>> # 批量上传文件
        >>> local_files = ["/local/file1.txt", "/local/file2.jpg"]
        >>> remote_destinations = ["/remote/upload/file1.txt", "/remote/upload/file2.jpg"]
        >>> success, total = client.upload_file_list(
        ...     sftp_name="sftp_server1",
        ...     local_path_list=local_files,
        ...     remote_path_list=remote_destinations
        ... )
        >>>
        >>> # 可视化下载
        >>> client.download_file_visualization(
        ...     sftp_name="sftp_server1",
        ...     remote_path="/remote/large_file.zip",
        ...     local_path="/local/large_file.zip"
        ... )
        >>>
        >>> # 列出目录内容
        >>> files = client.list_dir("/remote/directory", "sftp_server1")
        >>> for file in files:
        ...     print(file)
        >>>
        >>> # 获取目录下所有文件
        >>> all_files = client.get_dir_file_list("sftp_server1", "/remote/project")
        >>> print(f"找到 {len(all_files)} 个文件")
        >>>
        >>> # 关闭连接
        >>> client.close()
    """

    def __init__(self, sftp_configs: Dict[str, dict], verbose=False, max_connections=5):
        """
        初始化SFTP客户端

        Args:
            sftp_configs (Dict[str, dict]): SFTP配置字典
                Example:
                    {
                        "server1": {
                            "host": "10.141.1.120",
                            "port": 22,
                            "username": "root",
                            "password": "admin",  # 直接密码（不推荐）
                            "password_env": "SFTP_PASSWORD",  # 从环境变量获取密码（推荐）
                            "timeout": 30,  # 连接超时时间
                            "retry_times": 3,  # 重试次数
                            "private_key": "/path/to/key.pem",  # SSH私钥路径
                            "passphrase": "optional passphrase",  # 私钥密码
                            "passphrase_env": "SFTP_PASSPHRASE",  # 从环境变量获取私钥密码
                            "keepalive": 30  # 心跳间隔
                        }
                    }
            verbose (bool, optional): 是否启用详细日志输出
            max_connections (int, optional): 最大并行连接数

        Example:
            >>> sftp = SFTPClient(sftp_configs, verbose=True)
        """
        self._configs = sftp_configs
        self._connections = {}  # 连接池
        self._transports = {}  # 传输层池
        self.logger = set_logging("SFTPClient", verbose=verbose)
        self.max_connections = max_connections
        self._current_sftp_name = None
        self._lock = threading.RLock()  # 线程安全锁，支持递归调用
        
        # 验证和标准化配置
        if not sftp_configs:
            self.logger.warning("警告: 未提供SFTP配置")
        else:
            for name, config in sftp_configs.items():
                # 验证必要参数
                if 'host' not in config:
                    self.logger.error(f"配置 '{name}' 缺少必要参数: host")
                    continue
                if 'port' not in config:
                    config['port'] = 22  # 默认端口
                    self.logger.info(f"配置 '{name}' 使用默认端口: 22")
                if 'username' not in config:
                    self.logger.error(f"配置 '{name}' 缺少必要参数: username")
                    continue
                
                # 密码管理：从环境变量获取密码
                if 'password_env' in config:
                    password_env = config['password_env']
                    password = os.environ.get(password_env)
                    if password:
                        config['password'] = password
                        self.logger.info(f"配置 '{name}' 从环境变量获取密码: {password_env}")
                    else:
                        self.logger.warning(f"配置 '{name}' 环境变量 '{password_env}' 未设置")
                
                # 设置默认值
                config.setdefault('timeout', 30)  # 默认超时30秒
                config.setdefault('retry_times', 3)  # 默认重试3次
                config.setdefault('keepalive', 30)  # 默认心跳30秒
                config.setdefault('private_key', None)  # 默认无私钥
                config.setdefault('passphrase', None)  # 默认无私钥密码
                
                # 私钥密码管理：从环境变量获取
                if 'passphrase_env' in config:
                    passphrase_env = config['passphrase_env']
                    passphrase = os.environ.get(passphrase_env)
                    if passphrase:
                        config['passphrase'] = passphrase
                        self.logger.info(f"配置 '{name}' 从环境变量获取私钥密码: {passphrase_env}")
                
                # 加载私钥
                if config.get('private_key'):
                    try:
                        from paramiko import RSAKey
                        private_key_path = config['private_key']
                        if os.path.exists(private_key_path):
                            config['pkey'] = RSAKey.from_private_key_file(
                                private_key_path,
                                password=config.get('passphrase')
                            )
                            self.logger.info(f"配置 '{name}' 成功加载私钥")
                        else:
                            self.logger.error(f"配置 '{name}' 私钥文件不存在: {private_key_path}")
                    except Exception as e:
                        self.logger.error(f"配置 '{name}' 加载私钥失败: {e}")
                
                # 验证认证方式
                if 'password' not in config and 'pkey' not in config:
                    self.logger.error(f"配置 '{name}' 缺少认证方式: password 或 private_key")
                
                # 清理敏感信息，避免日志泄露
                if 'password' in config:
                    config['_password_masked'] = True
                if 'passphrase' in config:
                    config['_passphrase_masked'] = True

    def _create_transport(self, config: dict) -> paramiko.Transport:
        """
        创建优化的Transport连接

        Args:
            config (dict): SFTP配置

        Returns:
            paramiko.Transport: 传输层对象
        """
        transport = paramiko.Transport((config['host'], config['port']))

        # 优化连接参数，减少MAC校验问题
        transport.default_window_size = 2147483647  # 最大窗口大小
        transport.packetizer.REKEY_BYTES = 1024 * 1024 * 1024  # 1GB后重新协商密钥
        transport.packetizer.REKEY_PACKETS = 1000000  # 减少重新协商频率

        # 设置keepalive（使用配置中的值）
        keepalive = config.get('keepalive', 30)
        transport.set_keepalive(keepalive)

        # 禁用压缩，减少计算压力
        transport.use_compression(False)

        # 安全配置 - 使用更兼容的设置
        # 启用多种密钥交换算法，提高兼容性
        try:
            if hasattr(transport, 'kex_algorithms'):
                transport.kex_algorithms = [
                    'diffie-hellman-group-exchange-sha256',
                    'diffie-hellman-group14-sha256',
                    'diffie-hellman-group16-sha512',
                    'diffie-hellman-group18-sha512'
                ]
        except Exception as e:
            self.logger.debug(f"设置密钥交换算法失败: {e}")
        
        # 使用更兼容的加密算法
        try:
            if hasattr(transport, 'ciphers'):
                transport.ciphers = [
                    'aes128-ctr', 'aes192-ctr', 'aes256-ctr',
                    'aes128-gcm@openssh.com', 'aes256-gcm@openssh.com'
                ]
        except Exception as e:
            self.logger.debug(f"设置加密算法失败: {e}")
        
        # 使用更兼容的MAC算法
        try:
            if hasattr(transport, 'mac_algorithms'):
                transport.mac_algorithms = [
                    'hmac-sha2-256', 'hmac-sha2-512',
                    'hmac-sha1', 'hmac-md5'
                ]
        except Exception as e:
            self.logger.debug(f"设置MAC算法失败: {e}")

        return transport

    def _get_connection(self, sftp_name: str, retry_count: int = None) -> Optional[paramiko.SFTPClient]:
        """获取SFTP连接，支持自动重连"""
        for attempt in range(3):  # 最多尝试3次
            with self._lock:
                # 检查连接池大小
                if len(self._connections) > self.max_connections:
                    # 关闭最旧的连接
                    oldest_name = next(iter(self._connections))
                    self.logger.info(f"连接池已满，关闭最旧的连接: {oldest_name}")
                    self._close_connection(oldest_name)

                if sftp_name in self._connections:
                    try:
                        # 测试连接是否有效
                        self._connections[sftp_name].listdir('.')
                        self.logger.debug(f"复用现有连接: {sftp_name}")
                        return self._connections[sftp_name]
                    except (SSHException, EOFError, socket.error):
                        # 连接已失效，清理
                        self.logger.warning(f"连接已失效，重新连接: {sftp_name}")
                        self._close_connection(sftp_name)

                if sftp_name not in self._configs:
                    self.logger.error(f"SFTP配置 '{sftp_name}' 不存在")
                    return None

                config = self._configs[sftp_name]
                actual_retry_count = retry_count if retry_count is not None else config.get('retry_times', 3)

            # 尝试创建新连接
            try:
                self.logger.info(f"尝试连接到 {sftp_name} ({config['host']}:{config['port']}) 第{attempt + 1}次...")
                transport = self._create_transport(config)
                transport.connect(
                    username=config['username'],
                    password=config.get('password'),
                    pkey=config.get('pkey')
                )
                sftp = paramiko.SFTPClient.from_transport(transport)
                
                # 重新获取锁，将新连接添加到池
                with self._lock:
                    self._connections[sftp_name] = sftp
                    self.logger.info(f"成功连接到 {sftp_name}")
                    return sftp
            except Exception as e:
                self.logger.error(f"连接失败: {e}")
                time.sleep(1)  # 短暂暂停后重试

        return None

    def _close_connection(self, sftp_name: str):
        """关闭指定连接"""
        with self._lock:
            if sftp_name in self._connections:
                try:
                    self._connections[sftp_name].close()
                except:
                    pass
                finally:
                    del self._connections[sftp_name]

            if sftp_name in self._transports:
                try:
                    self._transports[sftp_name].close()
                except:
                    pass
                finally:
                    del self._transports[sftp_name]

    def close(self):
        """
        关闭所有连接

        Example:
            >>> client.close()
        """
        with self._lock:
            for sftp_name in list(self._connections.keys()):
                self._close_connection(sftp_name)

    def is_connected(self, sftp_name: str) -> bool:
        """
        检查是否能够连接到指定的SFTP服务器

        Args:
            sftp_name (str): SFTP配置名称

        Returns:
            bool: 连接是否成功

        Example:
            >>> if client.is_connected("server1"):
            ...     print("连接正常")
        """
        try:
            sftp = self._get_connection(sftp_name, retry_count=1)
            if sftp:
                return True
        except:
            pass
        return False

    def _file_exists(self, path: str, sftp_name: str = None) -> bool:
        """
        检查远程文件是否存在

        Args:
            path (str): 远程文件路径
            sftp_name (str, optional): SFTP配置名称

        Returns:
            bool: 文件是否存在

        Example:
            >>> if client._file_exists("/remote/file.txt", "server1"):
            ...     print("文件存在")
        """
        if not path:
            return False

        def operation(sftp):
            try:
                sftp.stat(path)
                return True
            except FileNotFoundError:
                return False
            except Exception:
                return False

        result = self._safe_sftp_op(operation, sftp_name)
        return result if result is not None else False

    def is_dir(self, remote_path: str, sftp_name: str = None) -> bool:
        """
        判断远程路径是否为目录

        Args:
            remote_path (str): 远程路径
            sftp_name (str, optional): SFTP配置名称

        Returns:
            bool: 是否为目录

        Example:
            >>> if client.is_dir("/remote/directory", "server1"):
            ...     print("这是一个目录")
        """

        def operation(sftp):
            try:
                return sftp.stat(remote_path).st_mode & 0o40000 != 0
            except:
                return False

        return self._safe_sftp_op(operation, sftp_name) or False

    def list_dir(self, remote_dir: str, sftp_name: str = None) -> List[str]:
        """
        列出远程目录内容

        Args:
            remote_dir (str): 远程目录路径
            sftp_name (str, optional): SFTP配置名称

        Returns:
            List[str]: 目录内容列表

        Example:
            >>> files = client.list_dir("/remote/directory", "server1")
            >>> for file in files:
            ...     print(file)
        """

        def operation(sftp):
            return sftp.listdir(remote_dir)

        return self._safe_sftp_op(operation, sftp_name) or []

    def get_dir_file_list(self, sftp_name: str, sftp_dir: str) -> List[str]:
        """
        递归获取SFTP目录下的所有文件列表

        Args:
            sftp_name (str): SFTP配置名称
            sftp_dir (str): 远程目录路径

        Returns:
            List[str]: 完整的文件路径列表

        Example:
            >>> file_list = client.get_dir_file_list("server1", "/remote/project")
            >>> print(f"找到 {len(file_list)} 个文件")
        """
        file_list = []

        def recursive_list(current_dir: str, sftp):
            try:
                for item in sftp.listdir(current_dir):
                    full_path = os.path.join(current_dir, item)
                    try:
                        if sftp.stat(full_path).st_mode & 0o40000:  # 是目录
                            recursive_list(full_path, sftp)
                        else:  # 是文件
                            file_list.append(full_path)
                    except:
                        continue
            except:
                pass

        sftp = self._get_connection(sftp_name)
        if sftp:
            recursive_list(sftp_dir, sftp)

        return file_list

    def download_file(self, sftp_name: str, remote_path: str, local_path: str,
                      progress_callback: Optional[Callable[[int, int], None]] = None,
                      max_retries: int = 3) -> bool:
        """
        下载单个大文件（支持断点续传和重试）

        Args:
            sftp_name (str): SFTP配置名称
            remote_path (str): 远程文件路径
            local_path (str): 本地保存路径
            progress_callback (Optional[Callable[[int, int], None]], optional): 进度回调函数
                - 参数1: 已传输字节数
                - 参数2: 总字节数
            max_retries (int, optional): 最大重试次数，默认为3

        Returns:
            bool: 是否下载成功

        Example:
            >>> def progress_callback(transferred, total):
            ...     print(f"进度: {transferred}/{total} bytes ({transferred/total*100:.1f}%)")
            >>>
            >>> success = client.download_file(
            ...     sftp_name="server1",
            ...     remote_path="/remote/data.zip",
            ...     local_path="/local/data.zip",
            ...     progress_callback=progress_callback
            ... )
        """
        for attempt in range(max_retries):
            try:
                sftp = self._get_connection(sftp_name)
                if not sftp:
                    continue

                # 获取文件信息
                file_stat = sftp.stat(remote_path)
                remote_size = file_stat.st_size

                if remote_size == 0:
                    self.logger.warning(f"远程文件大小为0: {os.path.basename(remote_path)}")
                    # 删除可能的空文件
                    if os.path.exists(local_path):
                        os.remove(local_path)
                    return False

                # 创建本地目录
                local_dir = os.path.dirname(local_path)
                if local_dir and not os.path.exists(local_dir):
                    os.makedirs(local_dir, exist_ok=True)

                # 检查是否需要断点续传
                downloaded = 0
                if os.path.exists(local_path):
                    local_size = os.path.getsize(local_path)
                    if local_size == remote_size:
                        return True
                    elif 0 < local_size < remote_size:
                        downloaded = local_size
                        self.logger.info(f"检测到部分文件，从 {local_size} 字节续传: {os.path.basename(remote_path)}")

                # 下载文件 - 分块下载优化
                chunk_size = 8192 * 10  # 80KB chunks
                total_transferred = downloaded
                
                if downloaded > 0:
                    # 断点续传
                    self.logger.info(f"开始断点续传: {os.path.basename(remote_path)} (已下载 {downloaded}/{remote_size} 字节)")
                    with open(local_path, 'ab') as f:
                        with sftp.open(remote_path, 'rb') as remote_file:
                            remote_file.seek(downloaded)
                            while total_transferred < remote_size:
                                chunk = remote_file.read(chunk_size)
                                if not chunk:
                                    break
                                f.write(chunk)
                                total_transferred += len(chunk)
                                if progress_callback:
                                    progress_callback(total_transferred, remote_size)
                else:
                    # 全新下载
                    self.logger.info(f"开始全新下载: {os.path.basename(remote_path)} (总大小: {remote_size} 字节)")
                    with open(local_path, 'wb') as f:
                        with sftp.open(remote_path, 'rb') as remote_file:
                            while True:
                                chunk = remote_file.read(chunk_size)
                                if not chunk:
                                    break
                                f.write(chunk)
                                total_transferred += len(chunk)
                                if progress_callback:
                                    progress_callback(total_transferred, remote_size)

                # 验证文件完整性
                final_size = os.path.getsize(local_path)
                if final_size == remote_size:
                    return True
                else:
                    self.logger.error(f"文件大小不匹配: {final_size}/{remote_size}")
                    if os.path.exists(local_path):
                        os.remove(local_path)

            except Exception as e:
                # 使用统一的异常处理方法
                should_retry = self._handle_exception(e, "下载", remote_path, attempt, max_retries)
                if should_retry:
                    self._close_connection(sftp_name)
                else:
                    # 下载失败时删除部分文件
                    if os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                            self.logger.info(f"已删除部分下载的文件: {local_path}")
                        except Exception as remove_error:
                            self.logger.warning(f"删除部分文件失败: {remove_error}")
                    if not isinstance(e, (SSHException, EOFError, socket.error, paramiko.SSHException)):
                        break

        return False

    def download_file_list(self, sftp_name: str, remote_path_list: List[str],
                           local_path_list: Union[str, List[str]],
                           progress_callback: Optional[Callable[[int, int, str], None]] = None,
                           batch_size: int = 20, max_workers: int = 1) -> Tuple[int, int]:
        """
        批量下载多个文件（支持断点续传和分批处理）

        Args:
            sftp_name (str): SFTP配置名称
            remote_path_list (List[str]): 远程文件路径列表
            local_path_list (Union[str, List[str]]): 本地保存路径
                - str: 所有文件保存到该目录
                - list: 每个文件对应的本地保存路径
            progress_callback (Optional[Callable[[int, int, str], None]], optional): 进度回调函数
                - 参数1: 当前文件索引
                - 参数2: 总文件数
                - 参数3: 当前文件名
            batch_size (int, optional): 每批处理文件数，默认为20
            max_workers (int, optional): 最大并行工作线程数，默认为1

        Returns:
            tuple: (成功下载数量, 总文件数量)

        Example:
            >>> def progress_callback(current, total, filename):
            ...     print(f"[{current}/{total}] 处理: {filename}")
            >>>
            >>> # 方式1: 所有文件保存到同一目录
            >>> success, total = client.download_file_list(
            ...     sftp_name="server1",
            ...     remote_path_list=["/remote/file1.txt", "/remote/file2.jpg"],
            ...     local_path_list="/local/downloads",
            ...     progress_callback=progress_callback,
            ...     max_workers=4
            ... )
            >>>
            >>> # 方式2: 每个文件指定保存路径
            >>> success, total = client.download_file_list(
            ...     sftp_name="server1",
            ...     remote_path_list=["/remote/file1.txt", "/remote/file2.jpg"],
            ...     local_path_list=["/local/file1.txt", "/local/file2.jpg"],
            ...     max_workers=2
            ... )
        """
        # 处理local_path_list的不同形式
        if isinstance(local_path_list, str):
            download_tasks = [
                (remote_path, os.path.join(local_path_list, os.path.basename(remote_path)))
                for remote_path in remote_path_list
            ]
        elif isinstance(local_path_list, list):
            if len(local_path_list) != len(remote_path_list):
                raise ValueError("local_path_list长度必须与remote_path_list相同")
            download_tasks = list(zip(remote_path_list, local_path_list))
        else:
            raise TypeError("local_path_list必须是字符串或列表")

        return self._batch_download_with_resilience(
            sftp_name=sftp_name,
            download_tasks=download_tasks,
            batch_size=batch_size,
            progress_callback=progress_callback,
            max_workers=max_workers
        )

    def upload_file(self, sftp_name: str, local_path: str, remote_path: str,
                    progress_callback: Optional[Callable[[int, int], None]] = None,
                    max_retries: int = 3) -> bool:
        """
        上传单个大文件（支持断点续传）

        Args:
            sftp_name (str): SFTP配置名称
            local_path (str): 本地文件路径
            remote_path (str): 远程保存路径
            progress_callback (Optional[Callable[[int, int], None]], optional): 进度回调函数
                - 参数1: 已传输字节数
                - 参数2: 总字节数
            max_retries (int, optional): 最大重试次数，默认为3

        Returns:
            bool: 是否上传成功

        Example:
            >>> success = client.upload_file(
            ...     sftp_name="server1",
            ...     local_path="/local/data.zip",
            ...     remote_path="/remote/data.zip"
            ... )
        """
        temp_path = remote_path + '.part'
        
        for attempt in range(max_retries):
            try:
                sftp = self._get_connection(sftp_name)
                if not sftp:
                    continue

                # 检查本地文件
                if not os.path.exists(local_path):
                    self.logger.error(f"本地文件不存在: {local_path}")
                    return False

                local_size = os.path.getsize(local_path)
                if local_size == 0:
                    self.logger.warning(f"本地文件为空: {local_path}")
                    return False

                # 创建远程目录
                remote_dir = os.path.dirname(remote_path)
                if remote_dir:
                    try:
                        sftp.stat(remote_dir)
                    except:
                        # 递归创建目录
                        parts = remote_dir.strip('/').split('/')
                        current_path = ''
                        for part in parts:
                            if part:
                                current_path = f"{current_path}/{part}" if current_path else f"/{part}"
                                try:
                                    sftp.stat(current_path)
                                except:
                                    sftp.mkdir(current_path)

                # 检查断点续传
                uploaded = 0
                try:
                    remote_stat = sftp.stat(remote_path)
                    if remote_stat.st_size == local_size:
                        self.logger.info(f"🔄 文件已存在且完整，跳过上传: {os.path.basename(remote_path)}")
                        return True
                    elif remote_stat.st_size > 0 and remote_stat.st_size < local_size:
                        uploaded = remote_stat.st_size
                        self.logger.info(f"⏩ 检测到部分上传文件，尝试从字节 {uploaded} 续传")
                except:
                    pass

                # 上传文件
                chunk_size = 1024 * 1024  # 1MB chunks

                with open(local_path, 'rb') as f:
                    if uploaded > 0:
                        f.seek(uploaded)

                    if uploaded == 0:
                        # 全新上传
                        sftp.putfo(f, temp_path, file_size=local_size,
                                   callback=progress_callback)
                    else:
                        # 断点续传
                        with sftp.open(temp_path, 'ab') as remote_file:
                            while True:
                                chunk = f.read(chunk_size)
                                if not chunk:
                                    break
                                remote_file.write(chunk)
                                if progress_callback:
                                    progress_callback(f.tell(), local_size)

                # 验证并重命名
                try:
                    temp_size = sftp.stat(temp_path).st_size
                    if temp_size == local_size:
                        # 可选：使用哈希值进一步验证文件完整性
                        try:
                            # 计算本地文件哈希值
                            local_hash = self._calculate_file_hash(local_path)
                            if local_hash:
                                # 计算远程临时文件哈希值
                                remote_hash = self._calculate_remote_file_hash(sftp, temp_path)
                                if remote_hash:
                                    if local_hash == remote_hash:
                                        self.logger.info(f"文件哈希值验证通过: {os.path.basename(remote_path)}")
                                        sftp.rename(temp_path, remote_path)
                                        self.logger.info(f"✅ 文件上传成功: {remote_path}")
                                        return True
                                    else:
                                        raise RuntimeError(f"文件哈希值不匹配: 本地={local_hash}, 远程={remote_hash}")
                        except Exception as hash_error:
                            # 哈希值验证失败，仅使用大小验证
                            self.logger.warning(f"文件哈希值验证失败: {hash_error}，仅使用大小验证")
                            
                        # 大小验证通过，重命名文件
                        sftp.rename(temp_path, remote_path)
                        self.logger.info(f"✅ 文件上传成功: {remote_path}")
                        return True
                    else:
                        raise RuntimeError(f"临时文件大小不匹配: {temp_size}/{local_size}")
                except Exception as e:
                    try:
                        sftp.remove(temp_path)
                    except:
                        pass
                    raise e

            except Exception as e:
                # 使用统一的异常处理方法
                should_retry = self._handle_exception(e, "上传", local_path, attempt, max_retries)
                if should_retry:
                    self._close_connection(sftp_name)
                else:
                    # 清理临时文件
                    try:
                        sftp = self._get_connection(sftp_name)
                        if sftp:
                            if self._file_exists(temp_path, sftp_name):
                                sftp.remove(temp_path)
                                self.logger.info(f"已清理临时文件: {temp_path}")
                    except Exception as cleanup_error:
                        self.logger.warning(f"清理临时文件失败: {cleanup_error}")
                    if not isinstance(e, (SSHException, EOFError, socket.error, paramiko.SSHException)):
                        break

        return False

    def upload_file_list(self, sftp_name: str, local_path_list: Union[str, List[str]],
                         remote_path_list: List[str],
                         progress_callback: Optional[Callable[[int, int, str], None]] = None,
                         batch_size: int = 20, max_workers: int = 1) -> Tuple[int, int]:
        """
        批量上传多个文件

        Args:
            sftp_name (str): SFTP配置名称
            local_path_list (Union[str, List[str]]): 本地文件路径列表
                - str: 目录路径，会上传该目录下所有与远程文件名对应的文件
                - list: 每个文件对应的本地路径
            remote_path_list (List[str]): 远程保存路径列表
            progress_callback (Optional[Callable[[int, int, str], None]], optional): 进度回调函数
                - 参数1: 当前文件索引
                - 参数2: 总文件数
                - 参数3: 当前文件名
            batch_size (int, optional): 每批处理文件数
            max_workers (int, optional): 最大并行工作线程数，默认为1

        Returns:
            tuple: (成功上传数量, 总文件数量)

        Example:
            >>> # 方式1: 上传指定文件到指定位置
            >>> success, total = client.upload_file_list(
            ...     sftp_name="server1",
            ...     local_path_list=["/local/file1.txt", "/local/file2.jpg"],
            ...     remote_path_list=["/remote/file1.txt", "/remote/file2.jpg"]
            ... )
            >>>
            >>> # 方式2: 上传目录下所有文件
            >>> success, total = client.upload_file_list(
            ...     sftp_name="server1",
            ...     local_path_list="/local/uploads",
            ...     remote_path_list=["/remote/file1.txt", "/remote/file2.jpg"]
            ... )
            >>>
            >>> # 方式3: 多线程上传
            >>> success, total = client.upload_file_list(
            ...     sftp_name="server1",
            ...     local_path_list=local_files,
            ...     remote_path_list=remote_paths,
            ...     max_workers=4
            ... )
        """
        # 处理local_path_list的不同形式
        if isinstance(local_path_list, str):
            upload_tasks = []
            for remote_path in remote_path_list:
                filename = os.path.basename(remote_path)
                local_path = os.path.join(local_path_list, filename)
                upload_tasks.append((local_path, remote_path))
        elif isinstance(local_path_list, list):
            if len(local_path_list) != len(remote_path_list):
                raise ValueError("local_path_list长度必须与remote_path_list相同")
            upload_tasks = list(zip(local_path_list, remote_path_list))
        else:
            raise TypeError("local_path_list必须是字符串或列表")

        total_files = len(upload_tasks)
        success_count = 0
        failed_files = []

        # 分批处理
        for batch_start in range(0, total_files, batch_size):
            batch_end = min(batch_start + batch_size, total_files)
            batch = upload_tasks[batch_start:batch_end]

            self.logger.info(f"上传批次 {batch_start // batch_size + 1}/{(total_files + batch_size - 1) // batch_size} "
                             f"({batch_start + 1}-{batch_end}/{total_files})")

            batch_success, batch_failed = self._process_upload_batch(
                sftp_name, batch, batch_start, total_files, progress_callback, max_workers
            )

            success_count += batch_success
            failed_files.extend(batch_failed)

            self.logger.info(f"批次完成: {batch_success}/{len(batch)} 成功")

            # 每批次完成后重置连接
            if batch_end < total_files:
                self.logger.info("重置连接以保持稳定性...")
                self._close_connection(sftp_name)
                time.sleep(1)

        if failed_files:
            self.logger.warning(f"上传失败文件: {len(failed_files)} 个")
            for local_path, _ in failed_files:
                self.logger.warning(f"  - {os.path.basename(local_path)}")

        return success_count, total_files

    def _process_upload_batch(self, sftp_name: str, batch: List[Tuple[str, str]],
                             batch_start: int, total_files: int, progress_callback: Optional[Callable],
                             max_workers: int) -> Tuple[int, List[Tuple[str, str]]]:
        """
        处理单个上传批次（内部方法）
        
        Args:
            sftp_name (str): SFTP配置名称
            batch (List[Tuple[str, str]]): 上传任务批次
            batch_start (int): 批次开始索引
            total_files (int): 总文件数
            progress_callback (Optional[Callable]): 进度回调函数
            max_workers (int): 最大并行工作线程数
            
        Returns:
            Tuple[int, List[Tuple[str, str]]]: (成功数量, 失败任务列表)
        """
        import concurrent.futures
        from concurrent.futures import ThreadPoolExecutor

        batch_success = 0
        batch_failed = []

        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=min(max_workers, len(batch))) as executor:
            # 提交任务
            future_to_task = {}
            for idx, (local_path, remote_path) in enumerate(batch, 1):
                file_idx = batch_start + idx
                filename = os.path.basename(local_path)
                future = executor.submit(
                    self._process_single_upload,
                    sftp_name, local_path, remote_path, file_idx, total_files, progress_callback
                )
                future_to_task[future] = (local_path, remote_path, filename)

            # 收集结果
            for future in concurrent.futures.as_completed(future_to_task):
                local_path, remote_path, filename = future_to_task[future]
                try:
                    success = future.result()
                    if success:
                        batch_success += 1
                    else:
                        batch_failed.append((local_path, remote_path))
                except Exception as e:
                    self.logger.error(f"处理文件 {filename} 时出错: {e}")
                    batch_failed.append((local_path, remote_path))
                    if progress_callback:
                        progress_callback(batch_start + len(batch_failed), total_files, f"❌ 异常: {filename}")

        return batch_success, batch_failed

    def _process_single_upload(self, sftp_name: str, local_path: str, remote_path: str,
                              file_idx: int, total_files: int, progress_callback: Optional[Callable] = None) -> bool:
        """
        处理单个上传任务（用于并行处理）
        """
        filename = os.path.basename(local_path)

        if progress_callback:
            progress_callback(file_idx, total_files, f"开始上传: {filename}")

        try:
            # 检查本地文件是否存在
            if not os.path.exists(local_path):
                self.logger.error(f"本地文件不存在: {local_path}")
                if progress_callback:
                    progress_callback(file_idx, total_files, f"❌ 失败: {filename}")
                return False

            # 上传文件
            if self.upload_file(sftp_name, local_path, remote_path, max_retries=3):
                if progress_callback:
                    progress_callback(file_idx, total_files, f"✅ 完成: {filename}")
                return True
            else:
                if progress_callback:
                    progress_callback(file_idx, total_files, f"❌ 失败: {filename}")
                return False

        except Exception as e:
            self.logger.error(f"处理文件 {filename} 时出错: {e}")
            if progress_callback:
                progress_callback(file_idx, total_files, f"❌ 异常: {filename}")
            return False

    def download_file_visualization(self, sftp_name: str, remote_path: str, local_path: str):
        """
        下载文件可视化（带进度条显示）

        Args:
            sftp_name (str): SFTP配置名称
            remote_path (str): 远程文件路径
            local_path (str): 本地保存路径

        Example:
            >>> client.download_file_visualization(
            ...     sftp_name="server1",
            ...     remote_path="/remote/large_file.zip",
            ...     local_path="/local/large_file.zip"
            ... )
        """
        self._visualization(
            sftp_name=sftp_name,
            remote_path=remote_path,
            local_path=local_path,
            processor=self.download_file,
            operation='download'
        )

    def upload_file_visualization(self, sftp_name: str, local_path: str, remote_path: str):
        """
        上传文件可视化（带进度条显示）

        Args:
            sftp_name (str): SFTP配置名称
            local_path (str): 本地文件路径
            remote_path (str): 远程保存路径

        Example:
            >>> client.upload_file_visualization(
            ...     sftp_name="server1",
            ...     local_path="/local/large_file.zip",
            ...     remote_path="/remote/large_file.zip"
            ... )
        """
        self._visualization(
            sftp_name=sftp_name,
            remote_path=remote_path,
            local_path=local_path,
            processor=self.upload_file,
            operation='upload'
        )

    def download_directory(self, sftp_name: str, remote_dir: str, local_dir: str, 
                          progress_callback: Optional[Callable] = None, 
                          batch_size: int = 20) -> Tuple[int, int]:
        """
        下载整个目录

        Args:
            sftp_name (str): SFTP配置名称
            remote_dir (str): 远程目录路径
            local_dir (str): 本地保存目录
            progress_callback (Optional[Callable], optional): 进度回调函数
            batch_size (int, optional): 每批处理文件数

        Returns:
            Tuple[int, int]: (成功下载数量, 总文件数量)

        Example:
            >>> success, total = client.download_directory(
            ...     sftp_name="server1",
            ...     remote_dir="/remote/data",
            ...     local_dir="/local/data"
            ... )
            >>> print(f"下载完成: {success}/{total}")
        """
        # 获取目录下所有文件
        all_files = self.get_dir_file_list(sftp_name, remote_dir)
        
        if not all_files:
            self.logger.warning(f"远程目录为空: {remote_dir}")
            return 0, 0
        
        # 构建下载任务
        download_tasks = []
        for remote_path in all_files:
            # 保持相对路径结构
            relative_path = os.path.relpath(remote_path, remote_dir)
            local_path = os.path.join(local_dir, relative_path)
            download_tasks.append((remote_path, local_path))
        
        # 批量下载
        return self._batch_download_with_resilience(
            sftp_name=sftp_name,
            download_tasks=download_tasks,
            batch_size=batch_size,
            progress_callback=progress_callback
        )

    def upload_directory(self, sftp_name: str, local_dir: str, remote_dir: str, 
                        progress_callback: Optional[Callable] = None, 
                        batch_size: int = 20) -> Tuple[int, int]:
        """
        上传整个目录

        Args:
            sftp_name (str): SFTP配置名称
            local_dir (str): 本地目录路径
            remote_dir (str): 远程保存目录
            progress_callback (Optional[Callable], optional): 进度回调函数
            batch_size (int, optional): 每批处理文件数

        Returns:
            Tuple[int, int]: (成功上传数量, 总文件数量)

        Example:
            >>> success, total = client.upload_directory(
            ...     sftp_name="server1",
            ...     local_dir="/local/data",
            ...     remote_dir="/remote/data"
            ... )
            >>> print(f"上传完成: {success}/{total}")
        """
        import glob
        
        # 获取目录下所有文件
        local_files = []
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                local_files.append(local_path)
        
        if not local_files:
            self.logger.warning(f"本地目录为空: {local_dir}")
            return 0, 0
        
        # 构建上传任务
        upload_tasks = []
        for local_path in local_files:
            # 保持相对路径结构
            relative_path = os.path.relpath(local_path, local_dir)
            remote_path = os.path.join(remote_dir, relative_path).replace('\\', '/')
            upload_tasks.append((local_path, remote_path))
        
        # 批量上传
        total_files = len(upload_tasks)
        success_count = 0
        
        for batch_start in range(0, total_files, batch_size):
            batch_end = min(batch_start + batch_size, total_files)
            batch = upload_tasks[batch_start:batch_end]
            
            self.logger.info(f"上传批次 {batch_start // batch_size + 1}/{(total_files + batch_size - 1) // batch_size}")
            
            for local_path, remote_path in batch:
                filename = os.path.basename(local_path)
                if progress_callback:
                    progress_callback(batch_start + 1, total_files, f"上传: {filename}")
                
                if self.upload_file(sftp_name, local_path, remote_path):
                    success_count += 1
                    if progress_callback:
                        progress_callback(batch_start + 1, total_files, f"✅ 完成: {filename}")
                else:
                    if progress_callback:
                        progress_callback(batch_start + 1, total_files, f"❌ 失败: {filename}")
        
        return success_count, total_files

    def delete_file(self, sftp_name: str, remote_path: str) -> bool:
        """
        删除远程文件

        Args:
            sftp_name (str): SFTP配置名称
            remote_path (str): 远程文件路径

        Returns:
            bool: 是否删除成功

        Example:
            >>> if client.delete_file("server1", "/remote/file.txt"):
            ...     print("文件删除成功")
        """
        def operation(sftp):
            sftp.remove(remote_path)
            return True

        result = self._safe_sftp_op(operation, sftp_name)
        return result if result is not None else False

    def rename_file(self, sftp_name: str, old_path: str, new_path: str) -> bool:
        """
        重命名远程文件

        Args:
            sftp_name (str): SFTP配置名称
            old_path (str): 原文件路径
            new_path (str): 新文件路径

        Returns:
            bool: 是否重命名成功

        Example:
            >>> if client.rename_file("server1", "/remote/old.txt", "/remote/new.txt"):
            ...     print("文件重命名成功")
        """
        def operation(sftp):
            sftp.rename(old_path, new_path)
            return True

        result = self._safe_sftp_op(operation, sftp_name)
        return result if result is not None else False

    def create_directory(self, sftp_name: str, remote_dir: str, recursive: bool = True) -> bool:
        """
        创建远程目录

        Args:
            sftp_name (str): SFTP配置名称
            remote_dir (str): 远程目录路径
            recursive (bool, optional): 是否递归创建父目录

        Returns:
            bool: 是否创建成功

        Example:
            >>> if client.create_directory("server1", "/remote/new/dir", recursive=True):
            ...     print("目录创建成功")
        """
        if recursive:
            # 递归创建目录
            parts = remote_dir.strip('/').split('/')
            current_path = ''
            for part in parts:
                if part:
                    current_path = f"{current_path}/{part}" if current_path else f"/{part}"
                    if not self._file_exists(current_path, sftp_name):
                        def operation(sftp):
                            sftp.mkdir(current_path)
                            return True
                        result = self._safe_sftp_op(operation, sftp_name)
                        if not result:
                            return False
            return True
        else:
            # 直接创建目录
            def operation(sftp):
                sftp.mkdir(remote_dir)
                return True
            result = self._safe_sftp_op(operation, sftp_name)
            return result if result is not None else False

    def delete_directory(self, sftp_name: str, remote_dir: str, recursive: bool = False) -> bool:
        """
        删除远程目录

        Args:
            sftp_name (str): SFTP配置名称
            remote_dir (str): 远程目录路径
            recursive (bool, optional): 是否递归删除目录内容

        Returns:
            bool: 是否删除成功

        Example:
            >>> if client.delete_directory("server1", "/remote/old/dir", recursive=True):
            ...     print("目录删除成功")
        """
        if recursive:
            # 递归删除目录内容
            def recursive_delete(sftp, path):
                for item in sftp.listdir(path):
                    item_path = os.path.join(path, item).replace('\\', '/')
                    try:
                        if sftp.stat(item_path).st_mode & 0o40000:
                            # 是目录
                            recursive_delete(sftp, item_path)
                        else:
                            # 是文件
                            sftp.remove(item_path)
                    except:
                        continue
                sftp.rmdir(path)
                return True

            result = self._safe_sftp_op(lambda sftp: recursive_delete(sftp, remote_dir), sftp_name)
            return result if result is not None else False
        else:
            # 直接删除空目录
            def operation(sftp):
                sftp.rmdir(remote_dir)
                return True
            result = self._safe_sftp_op(operation, sftp_name)
            return result if result is not None else False

    def get_file_stat(self, sftp_name: str, remote_path: str) -> Optional[os.stat_result]:
        """
        获取远程文件状态

        Args:
            sftp_name (str): SFTP配置名称
            remote_path (str): 远程文件路径

        Returns:
            Optional[os.stat_result]: 文件状态对象或None

        Example:
            >>> stat = client.get_file_stat("server1", "/remote/file.txt")
            >>> if stat:
            ...     print(f"文件大小: {stat.st_size} 字节")
        """
        def operation(sftp):
            return sftp.stat(remote_path)

        return self._safe_sftp_op(operation, sftp_name)

    def change_permissions(self, sftp_name: str, remote_path: str, mode: int) -> bool:
        """
        修改远程文件权限

        Args:
            sftp_name (str): SFTP配置名称
            remote_path (str): 远程文件路径
            mode (int): 权限模式（如 0o755）

        Returns:
            bool: 是否修改成功

        Example:
            >>> if client.change_permissions("server1", "/remote/file.sh", 0o755):
            ...     print("权限修改成功")
        """
        def operation(sftp):
            sftp.chmod(remote_path, mode)
            return True

        result = self._safe_sftp_op(operation, sftp_name)
        return result if result is not None else False

    def __enter__(self):
        """
        上下文管理器入口

        Example:
            >>> with SFTPClient(sftp_configs) as client:
            ...     client.download_file(...)
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """上下文管理器退出，自动关闭连接"""
        self.close()

    # ==================== 内部方法 ====================

    def _batch_download_with_resilience(self, sftp_name: str,
                                        download_tasks: List[Tuple[str, str]],
                                        batch_size: int = 20,
                                        progress_callback: Optional[Callable] = None,
                                        max_workers: int = 4) -> Tuple[int, int]:
        """
        分批次下载文件，提高稳定性（内部方法）
        """
        total_files = len(download_tasks)
        success_count = 0
        failed_files = []

        # 分批处理
        for batch_start in range(0, total_files, batch_size):
            batch_end = min(batch_start + batch_size, total_files)
            batch = download_tasks[batch_start:batch_end]

            self.logger.info(f"处理批次 {batch_start // batch_size + 1}/{(total_files + batch_size - 1) // batch_size} "
                             f"({batch_start + 1}-{batch_end}/{total_files})")

            batch_success, batch_failed = self._process_download_batch(
                sftp_name, batch, batch_start, total_files, progress_callback, max_workers
            )

            # 累计成功下载数量
            success_count += batch_success
            
            # 将本批次失败的文件添加到总失败列表
            failed_files.extend(batch_failed)

            self.logger.info(f"批次完成: {batch_success}/{len(batch)} 成功")

            # 每批次完成后重置连接
            if batch_end < total_files:
                self.logger.info("重置连接以保持稳定性...")
                self._close_connection(sftp_name)
                time.sleep(1)  # 短暂暂停

        # 重试失败的文件
        if failed_files:
            success_count += self._retry_failed_downloads(sftp_name, failed_files)

        return success_count, total_files

    def _process_download_batch(self, sftp_name: str, batch: List[Tuple[str, str]],
                               batch_start: int, total_files: int, progress_callback: Optional[Callable],
                               max_workers: int) -> Tuple[int, List[Tuple[str, str]]]:
        """
        处理单个下载批次（内部方法）
        
        Args:
            sftp_name (str): SFTP配置名称
            batch (List[Tuple[str, str]]): 下载任务批次
            batch_start (int): 批次开始索引
            total_files (int): 总文件数
            progress_callback (Optional[Callable]): 进度回调函数
            max_workers (int): 最大并行工作线程数
            
        Returns:
            Tuple[int, List[Tuple[str, str]]]: (成功数量, 失败任务列表)
        """
        import concurrent.futures
        from concurrent.futures import ThreadPoolExecutor

        batch_success = 0
        batch_failed = []

        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=min(max_workers, len(batch))) as executor:
            # 提交任务
            future_to_task = {}
            for idx, (remote_path, local_path) in enumerate(batch, 1):
                file_idx = batch_start + idx
                filename = os.path.basename(remote_path)
                future = executor.submit(
                    self._process_single_download,
                    sftp_name, remote_path, local_path, file_idx, total_files, progress_callback
                )
                future_to_task[future] = (remote_path, local_path, filename)

            # 收集结果
            for future in concurrent.futures.as_completed(future_to_task):
                remote_path, local_path, filename = future_to_task[future]
                try:
                    success = future.result()
                    if success:
                        batch_success += 1
                    else:
                        batch_failed.append((remote_path, local_path))
                except Exception as e:
                    self.logger.error(f"处理文件 {filename} 时出错: {e}")
                    batch_failed.append((remote_path, local_path))
                    # 异常时删除部分文件
                    if os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                            self.logger.info(f"已删除部分下载的文件: {local_path}")
                        except Exception as remove_error:
                            self.logger.warning(f"删除部分文件失败: {remove_error}")
                    if progress_callback:
                        progress_callback(batch_start + len(batch_failed), total_files, f"❌ 异常: {filename}")

        return batch_success, batch_failed

    def _retry_failed_downloads(self, sftp_name: str, failed_files: List[Tuple[str, str]]) -> int:
        """
        重试失败的下载任务（内部方法）
        
        Args:
            sftp_name (str): SFTP配置名称
            failed_files (List[Tuple[str, str]]): 失败的下载任务列表
            
        Returns:
            int: 重试成功的数量
        """
        retry_success = 0
        self.logger.info(f"重试 {len(failed_files)} 个失败的文件...")
        
        for remote_path, local_path in failed_files.copy():
            filename = os.path.basename(remote_path)
            if self._download_single_file_with_retry(sftp_name, remote_path, local_path, max_retries=2):
                retry_success += 1
                failed_files.remove((remote_path, local_path))
                self.logger.info(f"✅ 重试成功: {filename}")
            else:
                # 重试失败时删除部分文件
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                        self.logger.info(f"已删除部分下载的文件: {local_path}")
                    except Exception as remove_error:
                        self.logger.warning(f"删除部分文件失败: {remove_error}")

        if failed_files:
            self.logger.warning(f"最终失败文件: {len(failed_files)} 个")
            for remote_path, _ in failed_files:
                self.logger.warning(f"  - {os.path.basename(remote_path)}")

        return retry_success



    def _process_single_download(self, sftp_name: str, remote_path: str, local_path: str,
                                file_idx: int, total_files: int, progress_callback: Optional[Callable] = None) -> bool:
        """
        处理单个下载任务（用于并行处理）
        """
        filename = os.path.basename(remote_path)

        if progress_callback:
            progress_callback(file_idx, total_files, f"开始下载: {filename}")

        try:
            # 检查本地是否已存在完整文件
            if os.path.exists(local_path):
                try:
                    sftp = self._get_connection(sftp_name)
                    remote_size = sftp.stat(remote_path).st_size
                    local_size = os.path.getsize(local_path)

                    if local_size == remote_size:
                        self.logger.info(f"⏭️  文件已存在且完整，跳过: {filename}")
                        if progress_callback:
                            progress_callback(file_idx, total_files, f"已跳过: {filename}")
                        return True
                except Exception as e:
                    self.logger.debug(f"检查文件完整性失败: {e}")

            # 下载文件
            if self._download_single_file_with_retry(sftp_name, remote_path, local_path, max_retries=3):
                if progress_callback:
                    progress_callback(file_idx, total_files, f"✅ 完成: {filename}")
                return True
            else:
                # 确保删除部分文件
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                        self.logger.info(f"已删除部分下载的文件: {local_path}")
                    except Exception as remove_error:
                        self.logger.warning(f"删除部分文件失败: {remove_error}")
                if progress_callback:
                    progress_callback(file_idx, total_files, f"❌ 失败: {filename}")
                return False

        except Exception as e:
            self.logger.error(f"处理文件 {filename} 时出错: {e}")
            # 异常时删除部分文件
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    self.logger.info(f"已删除部分下载的文件: {local_path}")
                except Exception as remove_error:
                    self.logger.warning(f"删除部分文件失败: {remove_error}")
            if progress_callback:
                progress_callback(file_idx, total_files, f"❌ 异常: {filename}")
            return False

    def _download_single_file_with_retry(self, sftp_name: str, remote_path: str,
                                         local_path: str, max_retries: int = 3) -> bool:
        """
        带重试机制的单个文件下载（内部方法）
        """
        for attempt in range(max_retries):
            try:
                sftp = self._get_connection(sftp_name)
                if not sftp:
                    continue

                # 获取文件信息
                file_stat = sftp.stat(remote_path)
                remote_size = file_stat.st_size

                if remote_size == 0:
                    self.logger.warning(f"远程文件大小为0: {os.path.basename(remote_path)}")
                    # 删除可能的空文件
                    if os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                            self.logger.info(f"已删除部分下载的文件: {local_path}")
                        except Exception as remove_error:
                            self.logger.warning(f"删除部分文件失败: {remove_error}")
                    return False

                # 创建本地目录
                local_dir = os.path.dirname(local_path)
                if local_dir and not os.path.exists(local_dir):
                    os.makedirs(local_dir, exist_ok=True)

                # 检查是否需要断点续传
                downloaded = 0
                if os.path.exists(local_path):
                    local_size = os.path.getsize(local_path)
                    if local_size == remote_size:
                        return True
                    elif 0 < local_size < remote_size:
                        downloaded = local_size
                        self.logger.info(f"检测到部分文件，从 {local_size} 字节续传: {os.path.basename(remote_path)}")

                # 下载文件
                with open(local_path, 'ab' if downloaded > 0 else 'wb') as f:
                    if downloaded > 0:
                        # 断点续传
                        self.logger.info(f"开始断点续传: {os.path.basename(remote_path)} (已下载 {downloaded}/{remote_size} 字节)")
                        sftp.getfo(remote_path, f, downloaded)
                    else:
                        # 全新下载 - 使用 getfo 方法，与断点续传保持一致
                        self.logger.info(f"开始全新下载: {os.path.basename(remote_path)} (总大小: {remote_size} 字节)")
                        sftp.getfo(remote_path, f)

                # 验证文件完整性
                final_size = os.path.getsize(local_path)
                if final_size == remote_size:
                    # 可选：使用哈希值进一步验证文件完整性
                    try:
                        # 计算本地文件哈希值
                        local_hash = self._calculate_file_hash(local_path)
                        if local_hash:
                            # 计算远程文件哈希值
                            remote_hash = self._calculate_remote_file_hash(sftp, remote_path)
                            if remote_hash:
                                if local_hash == remote_hash:
                                    self.logger.info(f"文件哈希值验证通过: {os.path.basename(remote_path)}")
                                    return True
                                else:
                                    self.logger.error(f"文件哈希值不匹配: 本地={local_hash}, 远程={remote_hash}")
                                    if os.path.exists(local_path):
                                        try:
                                            os.remove(local_path)
                                            self.logger.info(f"已删除哈希值不匹配的文件: {local_path}")
                                        except Exception as remove_error:
                                            self.logger.warning(f"删除文件失败: {remove_error}")
                            else:
                                # 远程哈希值计算失败，仅使用大小验证
                                self.logger.warning("远程文件哈希值计算失败，仅使用大小验证")
                                return True
                    except Exception as e:
                        # 哈希值验证失败，仅使用大小验证
                        self.logger.warning(f"文件哈希值验证失败: {e}，仅使用大小验证")
                        return True
                else:
                    self.logger.error(f"文件大小不匹配: {final_size}/{remote_size}")
                    if os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                            self.logger.info(f"已删除部分下载的文件: {local_path}")
                        except Exception as remove_error:
                            self.logger.warning(f"删除部分文件失败: {remove_error}")

            except Exception as e:
                # 使用统一的异常处理方法
                should_retry = self._handle_exception(e, "下载", remote_path, attempt, max_retries)
                if should_retry:
                    self._close_connection(sftp_name)
                else:
                    # 下载失败时删除部分文件
                    if os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                            self.logger.info(f"已删除部分下载的文件: {local_path}")
                        except Exception as remove_error:
                            self.logger.warning(f"删除部分文件失败: {remove_error}")
                    if not isinstance(e, (SSHException, EOFError, socket.error, paramiko.SSHException)):
                        break

        return False

    def _visualization(self, sftp_name, remote_path, local_path, processor, operation='download'):
        """
        统一的上传/下载可视化方法（内部方法）
        """
        desc_map = {
            'upload': '上传文件',
            'download': '下载文件'
        }

        with tqdm(desc=desc_map[operation], unit="B", unit_scale=True, unit_divisor=1024, miniters=1) as pbar:
            def update_progress(bytes_transferred, total_bytes):
                if not hasattr(pbar, 'total'):
                    pbar.total = total_bytes
                pbar.update(bytes_transferred - pbar.n)

            # 使用重试机制
            for attempt in range(3):
                try:
                    if operation == 'download':
                        success = self.download_file(
                            sftp_name=sftp_name,
                            remote_path=remote_path,
                            local_path=local_path,
                            progress_callback=update_progress,
                            max_retries=1
                        )
                    else:
                        success = self.upload_file(
                            sftp_name=sftp_name,
                            local_path=local_path,
                            remote_path=remote_path,
                            progress_callback=update_progress,
                            max_retries=1
                        )

                    if success:
                        return
                    else:
                        pbar.set_description(f"{desc_map[operation]}失败 (尝试 {attempt + 1}/3)")
                        # 下载失败时删除部分文件
                        if operation == 'download' and os.path.exists(local_path):
                            try:
                                os.remove(local_path)
                                pbar.set_description(f"{desc_map[operation]}失败，已删除部分文件")
                            except Exception as remove_error:
                                pbar.set_description(f"删除部分文件失败: {str(remove_error)[:30]}...")
                except Exception as e:
                    pbar.set_description(f"{desc_map[operation]}错误: {str(e)[:50]}...")
                    # 异常时删除部分文件
                    if operation == 'download' and os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                            pbar.set_description(f"{desc_map[operation]}错误，已删除部分文件")
                        except Exception as remove_error:
                            pbar.set_description(f"删除部分文件失败: {str(remove_error)[:30]}...")
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                    else:
                        # 最终失败时确保删除部分文件
                        if operation == 'download' and os.path.exists(local_path):
                            try:
                                os.remove(local_path)
                            except:
                                pass
                        raise

    def _calculate_file_hash(self, file_path: str, hash_algorithm: str = 'md5') -> Optional[str]:
        """
        计算文件的哈希值

        Args:
            file_path (str): 文件路径
            hash_algorithm (str, optional): 哈希算法，支持 'md5' 或 'sha1'，默认为 'md5'

        Returns:
            Optional[str]: 文件的哈希值或None（如果计算失败）
        """
        import hashlib

        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}")
            return None

        try:
            if hash_algorithm.lower() == 'md5':
                hash_obj = hashlib.md5()
            elif hash_algorithm.lower() == 'sha1':
                hash_obj = hashlib.sha1()
            else:
                self.logger.error(f"不支持的哈希算法: {hash_algorithm}")
                return None

            with open(file_path, 'rb') as f:
                while chunk := f.read(8192 * 10):  # 80KB chunks
                    hash_obj.update(chunk)

            return hash_obj.hexdigest()
        except Exception as e:
            self.logger.error(f"计算文件哈希值失败: {e}")
            return None

    def _calculate_remote_file_hash(self, sftp: paramiko.SFTPClient, remote_path: str, hash_algorithm: str = 'md5') -> Optional[str]:
        """
        计算远程文件的哈希值

        Args:
            sftp (paramiko.SFTPClient): SFTP客户端
            remote_path (str): 远程文件路径
            hash_algorithm (str, optional): 哈希算法，支持 'md5' 或 'sha1'，默认为 'md5'

        Returns:
            Optional[str]: 远程文件的哈希值或None（如果计算失败）
        """
        import hashlib

        try:
            if hash_algorithm.lower() == 'md5':
                hash_obj = hashlib.md5()
            elif hash_algorithm.lower() == 'sha1':
                hash_obj = hashlib.sha1()
            else:
                self.logger.error(f"不支持的哈希算法: {hash_algorithm}")
                return None

            with sftp.open(remote_path, 'rb') as f:
                while chunk := f.read(8192 * 10):  # 80KB chunks
                    hash_obj.update(chunk)

            return hash_obj.hexdigest()
        except Exception as e:
            self.logger.error(f"计算远程文件哈希值失败: {e}")
            return None

    def _handle_exception(self, e: Exception, operation: str, file_path: str, attempt: int, max_retries: int) -> bool:
        """
        统一处理异常情况

        Args:
            e (Exception): 捕获到的异常
            operation (str): 操作类型，如 'download' 或 'upload'
            file_path (str): 文件路径
            attempt (int): 当前尝试次数
            max_retries (int): 最大重试次数

        Returns:
            bool: 是否应该继续重试
        """
        # 检查是否是网络相关异常
        is_network_error = isinstance(e, (SSHException, EOFError, socket.error, paramiko.SSHException))
        
        if is_network_error:
            self.logger.warning(f"{operation}失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                return True  # 继续重试
            else:
                self.logger.error(f"❌ {operation}失败达到最大重试次数: {file_path}")
                return False  # 停止重试
        else:
            self.logger.error(f"❌ {operation}异常: {e}")
            return False  # 非网络异常，直接停止重试

    def _safe_sftp_op(self, operation: Callable[[paramiko.SFTPClient], Any], sftp_name: str = None, max_retries: int = 3) -> Optional[Any]:
        """
        带重试机制的SFTP操作封装（内部方法）
        
        此方法为SFTP操作提供统一的错误处理和重试机制，确保操作的可靠性。
        
        Args:
            operation (Callable[[paramiko.SFTPClient], Any]): 要执行的SFTP操作函数，接收sftp客户端作为唯一参数
            sftp_name (str, optional): SFTP配置名称，如果为None则使用当前连接的服务器
            max_retries (int, optional): 最大重试次数，默认为3
            
        Returns:
            Optional[Any]: 操作结果或None（如果操作失败）
            
        Example:
            >>> # 示例：使用 _safe_sftp_op 执行远程文件统计
            >>> def stat_operation(sftp):
            ...     return sftp.stat("/remote/file.txt")
            >>> 
            >>> stat_result = client._safe_sftp_op(stat_operation, "server1")
            >>> if stat_result:
            ...     print(f"文件大小: {stat_result.st_size} 字节")
        """
        if sftp_name is None:
            if self._current_sftp_name:
                sftp_name = self._current_sftp_name
            else:
                self.logger.error("未指定SFTP服务器名称")
                return None

        for retry in range(max_retries):
            try:
                sftp = self._get_connection(sftp_name)
                if not sftp:
                    self.logger.warning(f"获取SFTP连接失败 (尝试 {retry + 1}/{max_retries})")
                    if retry < max_retries - 1:
                        time.sleep(2 ** retry)
                        continue
                    else:
                        self.logger.error("无法获取SFTP连接")
                        return None
                
                try:
                    result = operation(sftp)
                    return result
                except (SSHException, EOFError, socket.error, paramiko.SSHException) as e:
                    self.logger.warning(f'SFTP操作异常 (尝试 {retry + 1}/{max_retries}): {e}')
                    if retry < max_retries - 1:
                        time.sleep(2 ** retry)
                        self._close_connection(sftp_name)
                        continue
                    else:
                        self.logger.error(f'❌ SFTP操作失败: {e}')
                        return None
                except Exception as e:
                    self.logger.error(f'❌ 操作执行错误: {e}')
                    return None

            except Exception as e:
                self.logger.error(f'❌ 连接错误: {e}')
                if retry < max_retries - 1:
                    time.sleep(2 ** retry)
                    self._close_connection(sftp_name)
                else:
                    break

        return None