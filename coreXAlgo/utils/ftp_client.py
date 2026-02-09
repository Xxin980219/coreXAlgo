import io
import os
import socket
import time
from ftplib import FTP, error_proto, error_perm, error_temp, all_errors, error_reply
from typing import Dict, Callable, Optional, List, Union, Tuple, Any

from tqdm import tqdm

from .basic import set_logging
from .constants import TIMEOUT, RETRY_TIMES


def _ftp_block_callback(file_size, percent_callback=None, size_callback=None, process_block=None):
    """
    FTP文件传输块回调函数包装器，该函数创建一个回调包装器，用于处理FTP文件传输过程中的数据块回调。
    支持进度百分比回调、已传输大小回调和原始数据处理。

    Args:
        file_size (int): 文件总大小（字节数）
        percent_callback (Tuple[function, optional]): 进度百分比回调函数，接收一个整数参数（0-100）
        size_callback (Tuple[function, optional]): 已传输大小回调函数，接收两个参数：总文件大小和当前块大小
        process_block (Tuple[function, optional]): 原始数据处理函数，接收一个bytes参数，用于处理每个数据块（如写入文件）

    Returns:
        function: 回调包装器函数，接收一个bytes类型的数据块参数

    Example:
        >>> # 示例用法
        >>> def print_percent(percent):
        ...     print(f"进度: {percent}%")
        >>>
        >>> def handle_block(data):
        ...     # 处理数据块，如写入文件
        ...     pass
        >>>
        >>> callback = _ftp_block_callback(
        ...     file_size=1024000,
        ...     percent_callback=print_percent,
        ...     process_block=handle_block
        ... )
        >>>
        >>> # 在FTP传输中使用callback
        >>> # ftp.retrbinary('RETR filename', callback)
    """
    load_progress = [0, -1]  # [load_size, load_percent]

    def _callback_wrapper(data: bytes):
        """
        回调包装器内部函数，处理每个数据块，执行相应的回调函数

        Args:
            data : 当前传输的数据块
        """
        if process_block:
            process_block(data)
        if percent_callback:
            load_progress[0] += len(data)

            current_percent = int(100 * load_progress[0] / file_size)
            if current_percent != load_progress[1]:
                load_progress[1] = current_percent
                percent_callback(current_percent)  # 回调百分比
        if size_callback:
            size_callback(file_size, len(data))

    return _callback_wrapper


class FTPClient:
    """
    FTP客户端类，提供完整的FTP服务器操作功能

    功能特性：
        - 多服务器配置管理
        - 连接池和自动重连机制
        - 文件上传下载（支持断点续传）
        - 目录遍历和文件列表获取
        - 进度可视化和回调通知
        - 异常处理和重试机制
        - 配置验证和标准化
        - 环境变量密码管理

    Example:
        >>> ftp_configs = {
        ...     "server1": {
        ...         "host": "ftp.example.com",
        ...         "port": 21,
        ...         "username": "user",
        ...         "password": "pass",  # 直接密码
        ...         "password_env": "FTP_PASSWORD",  # 从环境变量获取密码
        ...         "timeout": 30,  # 连接超时时间
        ...         "retry_times": 3,  # 重试次数
        ...         "passive": False  # 传输模式
        ...     }
        ... }
        >>> client = FTPClient(ftp_configs, verbose=True, max_connections=5)
        >>> client.download_file("server1", "/remote/file.txt", "./local/file.txt")
    """

    def __init__(self, ftp_configs: Dict[str, dict], verbose=False, max_connections=5):
        """
        初始化FTP客户端

        Args:
            ftp_configs (Dict[str, dict]): FTP配置字典
                Example:
                    {
                        "server1": {
                            "host": "ftp.example.com",
                            "port": 21,
                            "username": "user",
                            "password": "pass",  # 直接密码
                            "password_env": "FTP_PASSWORD",  # 从环境变量获取密码
                            "timeout": 30,  # 连接超时时间
                            "retry_times": 3,  # 重试次数
                            "passive": False,  # 传输模式
                            "keepalive": 30,  # 心跳间隔
                            "private_key": "/path/to/key.pem",  # SSH私钥路径（如果FTP服务器支持）
                            "passphrase": "optional passphrase",  # 私钥密码
                            "passphrase_env": "FTP_PASSPHRASE"  # 从环境变量获取私钥密码
                        }
                    }
            verbose (bool, optional): 是否启用详细日志输出
            max_connections (int, optional): 最大并行连接数

        Example:
            >>> ftp = FTPClient(ftp_configs, verbose=True, max_connections=5)
        """
        self._configs = ftp_configs
        self._connections = {}  # 连接池
        self._transports = {}  # 传输层池（用于高级连接管理）
        self._ftp = None
        self.ftp_name = None
        self.logger = set_logging("FTPClient", verbose=verbose)
        self.max_connections = max_connections
        self._current_ftp_name = None
        
        # 验证和标准化配置
        if not ftp_configs:
            self.logger.warning("警告: 未提供FTP配置")
        else:
            for name, config in ftp_configs.items():
                # 验证必要参数
                if 'host' not in config:
                    self.logger.error(f"配置 '{name}' 缺少必要参数: host")
                    continue
                if 'port' not in config:
                    config['port'] = 21  # 默认端口
                    self.logger.info(f"配置 '{name}' 使用默认端口: 21")
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
                config.setdefault('passive', False)  # 默认主动模式
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
                
                # 加载私钥（如果支持）
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

    def _ftpconnect(self, ftp_name=None, debug_level=0):
        """
        连接到FTP服务器

        Args:
            ftp_name: FTP配置名称，如果为None则使用当前已设置的ftp_name
            debug_level: 调试级别
                         0: 无输出
                         1: 输出命令和响应
                         2: 输出完整通信详情

        Returns:
            FTP连接对象
        """
        if ftp_name is not None:
            self.ftp_name = ftp_name
        if self.ftp_name not in self._configs:
            raise ValueError(f"FTP配置 '{self.ftp_name}' 不存在")

        config = self._configs[self.ftp_name]
        timeout = config.get('timeout', TIMEOUT)
        self._ftp = FTP(timeout=timeout)
        self._ftp.set_debuglevel(debug_level)  # 开启调试日志

        try:
            # 1. 连接服务器
            try:
                self._ftp.connect(config['host'], config['port'], timeout=timeout)
                welcome_msg = self._ftp.getwelcome()
                if not welcome_msg.startswith('220'):
                    raise RuntimeError(f"非预期欢迎消息: {welcome_msg}")
            except socket.timeout:
                raise RuntimeError(f"连接FTP服务器超时（{config['host']}:{config['port']}）")
            except socket.error as e:
                raise RuntimeError(f"网络错误: {e}")
            except error_proto as e:
                raise RuntimeError(f"协议错误: {e}")

            # 2. 登录认证
            try:
                login_resp = self._ftp.login(config['username'], config['password'])
                if '230' not in login_resp:  # 检查登录响应码
                    raise RuntimeError(f"登录失败: {login_resp}")
            except error_perm as e:
                raise RuntimeError(f"认证失败（用户名/密码错误）: {e}")
            except error_temp as e:
                raise RuntimeError(f"临时服务器错误: {e}")

            # 3. 设置传输模式
            try:
                passive = config.get('passive', False)
                self._ftp.set_pasv(passive)  # 设置传输模式
                # 验证模式是否设置成功（通过发送NOOP命令）
                if '200' not in self._ftp.sendcmd('NOOP'):
                    raise RuntimeError(f"无法切换到{'被动' if passive else '主动'}模式")
            except error_proto as e:
                raise RuntimeError(f"模式设置失败: {e}")

            self.logger.info(
                f"✅ 成功连接到FTP: {self.ftp_name} (模式: {'PASV' if self._ftp.passiveserver else 'PORT'})")
            return self._ftp

        except all_errors as e:
            # 确保发生异常时关闭连接
            self._close()
            raise RuntimeError(f"FTP操作失败: {e}")

    def _ftp_reconnect(self):
        self._close()
        self._ftpconnect()

    def _get_connection(self, ftp_name: str, retry_count: int = None) -> Optional[FTP]:
        """
        获取FTP连接，支持自动重连和连接池管理

        Args:
            ftp_name (str): FTP配置名称
            retry_count (int, optional): 重试次数，默认使用配置中的值

        Returns:
            Optional[FTP]: FTP连接对象或None

        Example:
            >>> ftp = client._get_connection("server1")
        """
        # 检查连接池大小
        if len(self._connections) > self.max_connections:
            # 关闭最旧的连接
            oldest_name = next(iter(self._connections))
            self.logger.info(f"连接池已满，关闭最旧的连接: {oldest_name}")
            self._close_connection(oldest_name)

        if ftp_name in self._connections:
            try:
                # 测试连接是否有效
                conn = self._connections[ftp_name]
                conn.voidcmd('NOOP')
                self.logger.debug(f"复用现有连接: {ftp_name}")
                return conn
            except (error_perm, error_proto, socket.error):
                # 连接已失效，清理
                self.logger.warning(f"连接已失效，重新连接: {ftp_name}")
                self._close_connection(ftp_name)

        if ftp_name not in self._configs:
            self.logger.error(f"FTP配置 '{ftp_name}' 不存在")
            return None

        config = self._configs[ftp_name]

        # 使用配置中的重试次数或默认值
        actual_retry_count = retry_count if retry_count is not None else config.get('retry_times', 3)

        for attempt in range(actual_retry_count):
            try:
                # 创建新的连接
                self.logger.info(f"尝试连接到 {ftp_name} ({config['host']}:{config['port']}) 第{attempt + 1}次...")

                # 创建FTP连接
                timeout = config.get('timeout', TIMEOUT)
                ftp = FTP(timeout=timeout)
                ftp.set_debuglevel(0)  # 不输出调试信息

                # 连接服务器
                ftp.connect(config['host'], config['port'], timeout=timeout)
                welcome_msg = ftp.getwelcome()
                if not welcome_msg.startswith('220'):
                    raise RuntimeError(f"非预期欢迎消息: {welcome_msg}")

                # 登录认证
                # 注意：标准FTP协议只支持密码认证，不支持SSH密钥认证
                # 私钥配置仅用于特殊FTP服务器或未来扩展
                private_key = config.get('private_key')
                if private_key:
                    self.logger.info(f"注意: FTP协议不支持SSH密钥认证，忽略私钥配置: {private_key}")
                
                login_resp = ftp.login(config['username'], config.get('password', ''))
                if '230' not in login_resp:
                    raise RuntimeError(f"登录失败: {login_resp}")

                # 设置传输模式
                passive = config.get('passive', False)
                ftp.set_pasv(passive)
                # 验证模式是否设置成功
                if '200' not in ftp.sendcmd('NOOP'):
                    raise RuntimeError(f"无法切换到{'被动' if passive else '主动'}模式")

                # 设置心跳间隔
                keepalive = config.get('keepalive', 30)
                # FTP协议本身不支持心跳，但我们可以定期发送NOOP命令

                # 保存连接
                self._connections[ftp_name] = ftp
                self._current_ftp_name = ftp_name

                self.logger.info(f"✅ 成功连接到FTP: {ftp_name} (模式: {'PASV' if passive else 'PORT'})")
                return ftp

            except error_perm as e:
                self.logger.error(f"❌ 认证失败: {e}")
                return None
            except (error_proto, socket.error) as e:
                self.logger.warning(f"连接失败 (尝试 {attempt + 1}/{actual_retry_count}): {e}")
                if attempt < actual_retry_count - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    self.logger.error(f"❌ 无法连接到 {ftp_name}: {e}")
                    return None
            except Exception as e:
                self.logger.error(f"❌ 连接异常: {e}")
                if attempt < actual_retry_count - 1:
                    time.sleep(2 ** attempt)
                else:
                    return None

    def _close_connection(self, ftp_name: str):
        """关闭指定连接"""
        if ftp_name in self._connections:
            try:
                self._connections[ftp_name].quit()
            except:
                pass
            finally:
                del self._connections[ftp_name]

        if ftp_name in self._transports:
            try:
                self._transports[ftp_name].close()
            except:
                pass
            finally:
                del self._transports[ftp_name]

    def close(self):
        """
        关闭所有连接

        Example:
            >>> client.close()
        """
        for ftp_name in list(self._connections.keys()):
            self._close_connection(ftp_name)
        # 清理所有传输层连接
        for ftp_name in list(self._transports.keys()):
            try:
                self._transports[ftp_name].close()
            except:
                pass
            finally:
                del self._transports[ftp_name]
        self._close()

    def is_connected(self, ftp_name: str) -> bool:
        """
        检查是否能够连接到指定的FTP服务器

        Args:
            ftp_name (str): FTP配置名称

        Returns:
            bool: 连接是否成功

        Example:
            >>> if client.is_connected("server1"):
            ...     print("连接正常")
        """
        try:
            self.logger.info(f"检查FTP服务器连接: {ftp_name}")
            ftp = self._get_connection(ftp_name, retry_count=1)
            if ftp:
                self.logger.info(f"✅ FTP服务器连接正常: {ftp_name}")
                return True
            else:
                self.logger.warning(f"❌ 无法连接到FTP服务器: {ftp_name}")
                return False
        except Exception as e:
            self.logger.error(f"❌ 检查FTP连接时出错: {e}")
            return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._close()

    def _close(self):
        """close ftp connect

        :return:
        """
        if self._ftp:
            try:
                self._ftp.quit()
            except:
                pass
            finally:
                self._ftp = None

    def _safe_ftp_op(self, operation: Callable):
        """带重试的FTP操作封"""
        for retry in range(RETRY_TIMES):
            try:
                if self._ftp:
                    return operation()
            except error_perm as e:
                self.logger.warning('FTP权限错误: %s', str(e))
                return None
            except Exception as e:
                self.logger.warning('FTP操作异常: %s', str(e))
            time.sleep(TIMEOUT ** (retry + 1))
            self._ftp_reconnect()
        return None

    def is_dir(self, remote_path, guess_by_extension=True):
        """
        判断远程路径是否为目录

        Args:
            remote_path (str): 要检查的远程路径
            guess_by_extension (bool): 是否使用扩展名猜测方式
                                True: 使用快速猜测（性能好，但可能有误判）
                                False: 使用准确判断（性能较差，但准确）

        Returns:
            bool: True表示是目录，False表示是文件或路径不存在

        Example:
            >>> ftp.is_dir("/home/user")      # 可能返回True（目录）
            >>> ftp.is_dir("/home/file.txt")  # 可能返回False（文件）
            >>> ftp.is_dir("/invalid/path")   # 返回False（路径不存在）
        """
        if guess_by_extension:
            return '.' not in os.path.basename(remote_path)[-6:]

        original_dir = self._safe_ftp_op(lambda: self._ftp.pwd())
        if not original_dir:
            return False

        try:
            self._ftp.cwd(remote_path)
            return True
        except:
            return False
        finally:
            self._safe_ftp_op(lambda: self._ftp.cwd(original_dir))

    def list_dir(self, remote_dir):
        """
        列出远程目录的内容（文件和子目录名称）

        Args:
        remote_dir (str): 要列出的远程目录路径
                        可以是绝对路径（如"/home/user"）或相对路径（如"docs"）
                        如果为空字符串，表示当前工作目录

        Returns:
            list: 包含目录中所有文件和子目录名称的列表
                  如果目录为空、不存在或操作失败，返回空列表
                  列表中的名称不包含完整路径，只有文件名或目录名

        Example:
            >>> ftp.list_dir("/home/user")
            ['file1.txt', 'file2.pdf', 'subdirectory', 'archive.zip']

            >>> ftp.list_dir("/nonexistent")
            []  # 目录不存在时返回空列表

            >>> ftp.list_dir("")
            ['.', '..', 'file1.txt', 'docs']  # 当前目录可能包含特殊条目
        """
        return self._safe_ftp_op(lambda: self._ftp.nlst(remote_dir)) or []

    def get_dir_file_list(self, ftp_name, ftp_dir):
        """
        递归获取FTP目录及其所有子目录中的文件列表

        Args:
            ftp_name (str): FTP配置名称，用于标识使用哪个FTP服务器配置
            ftp_dir (str): 要遍历的远程目录路径，可以是绝对路径或相对路径
                          如果路径不存在，将返回空列表

        Returns:
            list: 包含所有文件完整路径的列表，格式为：
                  ["/path/to/file1.txt", "/path/to/subdir/file2.pdf", ...]
                  如果目录为空或不存在，返回空列表

        Example:
            >>> ftp_client.get_dir_file_list("my_ftp", "/data")
            ['/data/file1.txt', '/data/docs/report.pdf', '/data/images/photo.jpg']

            >>> ftp_client.get_dir_file_list("my_ftp", "/empty_dir")
            []  # 空目录返回空列表
        """
        ftp = self._get_connection(ftp_name)
        if not ftp:
            self.logger.error(f"无法获取FTP连接: {ftp_name}")
            return []

        # 保存当前连接，以便递归调用时使用
        self._ftp = ftp
        self.ftp_name = ftp_name
        
        file_list = []

        try:
            # 使用当前连接列出目录内容
            try:
                items = ftp.nlst(ftp_dir)
            except Exception as e:
                self.logger.error(f"列出目录失败: {e}")
                return []

            for item in items:
                # 跳过特殊目录
                if item in ['.', '..']:
                    continue
                
                full_path = os.path.join(ftp_dir, item) if ftp_dir else item

                # 检查是否为目录
                try:
                    original_dir = ftp.pwd()
                    ftp.cwd(full_path)
                    # 是目录，递归遍历
                    file_list.extend(self.get_dir_file_list(ftp_name, full_path))
                    ftp.cwd(original_dir)
                except Exception:
                    # 不是目录，添加到文件列表
                    file_list.append(full_path)
        finally:
            # 不关闭连接，因为可能还有其他操作需要使用
            pass
        return file_list

    def download_file(self, ftp_name, remote_path, local_path, bufsize=8192,
                      progress_callback: Optional[Callable[[int, int], None]] = None, max_retries: int = 3):
        """下载单个大文件（支持断点续传和重试）

        Args:
            ftp_name: 配置名称
            remote_path: 远程文件路径
            local_path: 本地保存路径
            bufsize: 缓冲区大小（字节）
            progress_callback: 进度回调（0-100）,接收两个参数(bytes_transferred, total_bytes)
            max_retries: 最大重试次数，默认为3

        Returns:
            bool: 是否下载成功

        Example:
            >>> def progress_callback(transferred, total):
            ...     print(f"进度: {transferred}/{total} bytes ({transferred/total*100:.1f}%)")
            >>>
            >>> success = client.download_file(
            ...     ftp_name="server1",
            ...     remote_path="/remote/data.zip",
            ...     local_path="/local/data.zip",
            ...     progress_callback=progress_callback
            ... )
        """
        for attempt in range(max_retries):
            try:
                ftp = self._get_connection(ftp_name)
                if not ftp:
                    self.logger.warning(f"无法获取FTP连接: {ftp_name} (尝试 {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return False

                # 分离目录和文件名
                remote_dir, filename = os.path.split(remote_path)
                local_path = os.path.join(local_path, filename) if os.path.isdir(local_path) else local_path

                # 获取文件大小
                try:
                    file_size = ftp.size(remote_path)
                    if not file_size:
                        self.logger.error("无法获取远程文件大小")
                        return False
                except Exception as e:
                    self.logger.error(f"获取文件大小失败: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        self._close_connection(ftp_name)
                        continue
                    return False

                if file_size == 0:
                    self.logger.warning(f"远程文件大小为0: {os.path.basename(remote_path)}")
                    # 删除可能的空文件
                    if os.path.exists(local_path):
                        os.remove(local_path)
                    return False

                # 创建本地目录
                local_dir = os.path.dirname(local_path)
                if local_dir and not os.path.exists(local_dir):
                    os.makedirs(local_dir, exist_ok=True)

                # 检查断点续传
                downloaded = 0
                if os.path.exists(local_path):
                    local_size = os.path.getsize(local_path)
                    if local_size == file_size:
                        self.logger.info(f"🔄 文件已存在且完整，跳过下载: {local_path}")
                        return True
                    elif 0 < local_size < file_size:
                        downloaded = local_size
                        self.logger.info(f"⏩ 检测到部分文件，从 {local_size} 字节续传: {os.path.basename(remote_path)}")
                        try:
                            ftp.voidcmd(f"REST {local_size}")  # FTP断点续传命令
                        except error_reply as e:
                            if "350" not in str(e):
                                self.logger.warning("⚠️ 续传协商失败，重新下载")
                                os.remove(local_path)
                                downloaded = 0

                # 下载文件 - 分块下载优化
                total_transferred = downloaded
                
                if downloaded > 0:
                    # 断点续传
                    self.logger.info(f"开始断点续传: {os.path.basename(remote_path)} (已下载 {downloaded}/{file_size} 字节)")
                    with open(local_path, 'ab') as f:
                        # 定义下载回调
                        def callback(data):
                            nonlocal total_transferred
                            f.write(data)
                            total_transferred += len(data)
                            if progress_callback:
                                progress_callback(total_transferred, file_size)
                        
                        ftp.retrbinary(f"RETR {remote_path}", callback, bufsize, rest=downloaded)
                else:
                    # 全新下载
                    self.logger.info(f"开始全新下载: {os.path.basename(remote_path)} (总大小: {file_size} 字节)")
                    with open(local_path, 'wb') as f:
                        # 定义下载回调
                        def callback(data):
                            nonlocal total_transferred
                            f.write(data)
                            total_transferred += len(data)
                            if progress_callback:
                                progress_callback(total_transferred, file_size)
                        
                        ftp.retrbinary(f"RETR {remote_path}", callback, bufsize)

                # 验证文件完整性
                final_size = os.path.getsize(local_path)
                if final_size == file_size:
                    self.logger.info(f"✅ 文件已保存至: {local_path}")
                    return True
                else:
                    self.logger.error(f"文件大小不匹配: {final_size}/{file_size}")
                    if os.path.exists(local_path):
                        os.remove(local_path)
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        self._close_connection(ftp_name)
                        continue
                    return False

            except (error_perm, error_proto, socket.error) as e:
                self.logger.warning(f"下载失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    sleep_time = 2 ** attempt
                    self.logger.info(f"等待 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
                    self.logger.info(f"重置连接并重新尝试下载: {remote_path}")
                    self._close_connection(ftp_name)
                else:
                    self.logger.error(f"❌ 下载失败达到最大重试次数: {remote_path}")
                    # 下载失败时删除部分文件
                    if os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                            self.logger.info(f"已删除部分下载的文件: {local_path}")
                        except Exception as remove_error:
                            self.logger.warning(f"删除部分文件失败: {remove_error}")
            except Exception as e:
                self.logger.error(f"❌ 下载异常: {e}")
                # 异常时删除部分文件
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                        self.logger.info(f"已删除部分下载的文件: {local_path}")
                    except Exception as remove_error:
                        self.logger.warning(f"删除部分文件失败: {remove_error}")
                if attempt < max_retries - 1:
                    sleep_time = 2 ** attempt
                    self.logger.info(f"等待 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
                    self.logger.info(f"重置连接并重新尝试下载: {remote_path}")
                    self._close_connection(ftp_name)
                else:
                    break

        return False

    def upload_file(self, ftp_name, local_path, remote_path, bufsize=8192,
                    progress_callback: Optional[Callable[[int, int], None]] = None, max_retries: int = 3):
        """上传单个文件（支持断点续传和重试）

        Args:
            ftp_name: 配置名称
            local_path: 本地文件路径
            remote_path: 远程保存路径
            bufsize: 缓冲区大小（字节）
            progress_callback: 进度回调（0-100）,接收两个参数(bytes_transferred, total_bytes)
            max_retries: 最大重试次数，默认为3

        Returns:
            bool: 是否上传成功

        Example:
            >>> success = client.upload_file(
            ...     ftp_name="server1",
            ...     local_path="/local/data.zip",
            ...     remote_path="/remote/data.zip"
            ... )
        """
        temp_path = remote_path + '.part'
        
        for attempt in range(max_retries):
            try:
                ftp = self._get_connection(ftp_name)
                if not ftp:
                    self.logger.warning(f"无法获取FTP连接: {ftp_name} (尝试 {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return False

                # 检查本地文件
                if not os.path.exists(local_path):
                    self.logger.error(f"本地文件不存在: {local_path}")
                    return False

                local_size = os.path.getsize(local_path)
                if local_size == 0:
                    self.logger.warning(f"本地文件为空: {local_path}")
                    return False

                # 分离目录和文件名
                remote_dir, filename = os.path.split(remote_path)
                
                # 创建远程目录
                if remote_dir:
                    try:
                        # 递归创建目录
                        parts = remote_dir.strip('/').split('/')
                        current_path = ''
                        for part in parts:
                            if part:
                                current_path = f"{current_path}/{part}" if current_path else f"/{part}"
                                try:
                                    ftp.cwd(current_path)
                                except:
                                    try:
                                        ftp.mkd(current_path)
                                        self.logger.info(f"创建远程目录: {current_path}")
                                    except Exception as e:
                                        self.logger.error(f"创建目录失败: {e}")
                                        if attempt < max_retries - 1:
                                            time.sleep(2 ** attempt)
                                            self._close_connection(ftp_name)
                                            continue
                                        return False
                    except Exception as e:
                        self.logger.error(f"处理远程目录失败: {e}")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            self._close_connection(ftp_name)
                            continue
                        return False

                # 检查断点续传
                uploaded = 0
                try:
                    remote_size = ftp.size(filename)
                    if remote_size == local_size:
                        self.logger.info(f"🔄 文件已存在且完整，跳过上传: {remote_path}")
                        return True
                    elif remote_size > 0 and remote_size < local_size:
                        uploaded = remote_size
                        self.logger.info(f"⏩ 检测到部分上传文件，尝试从字节 {uploaded} 续传")
                except:
                    pass

                # 上传文件
                total_transferred = uploaded
                
                with open(local_path, 'rb') as fp:
                    if uploaded > 0:
                        fp.seek(uploaded)  # 跳转到续传位置

                    # 定义上传回调
                    def callback(data):
                        nonlocal total_transferred
                        total_transferred += len(data)
                        if progress_callback:
                            progress_callback(total_transferred, local_size)

                    # 分块上传
                    while total_transferred < local_size:
                        chunk = fp.read(min(bufsize, local_size - total_transferred))
                        if not chunk:
                            break

                        # 使用APPE命令进行续传，STOR命令进行新上传
                        cmd = f"APPE {filename}" if uploaded > 0 else f"STOR {filename}"
                        ftp.storbinary(cmd, io.BytesIO(chunk), blocksize=len(chunk))
                        callback(chunk)

                # 验证完整性
                if total_transferred != local_size:
                    raise RuntimeError(f"上传不完整: {total_transferred}/{local_size}字节")

                self.logger.info(f"✅ 文件已上传至: {remote_path}")
                return True

            except (error_perm, error_proto, socket.error) as e:
                self.logger.warning(f"上传失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    self._close_connection(ftp_name)
                else:
                    self.logger.error(f"❌ 上传失败达到最大重试次数: {local_path}")
            except Exception as e:
                self.logger.error(f"❌ 上传异常: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    self._close_connection(ftp_name)
                else:
                    break

        return False

    def _visualization(self, ftp_name, remote_path, local_path, processor, operation='download'):
        """
        统一的上传/下载可视化方法

        Args:
            sftp_name: 配置名称
            remote_path: 远程路径
            local_path: 本地路径
            processor: 处理函数 (upload_file 或 download_file)
            operation: 操作类型 ('upload' 或 'download')
        """
        desc_map = {
            'upload': '上传文件',
            'download': '下载文件'
        }
        with tqdm(desc=desc_map[operation], unit="B", unit_scale=True, unit_divisor=1024, miniters=1) as pbar:
            def update_progress(bytes_transferred, total_bytes):
                """
                 进度更新回调函数，由processor函数在传输过程中调用

                 Args:
                     bytes_transferred (int): 已传输的字节数
                     total_bytes (int): 文件总字节数
                 """
                if not hasattr(pbar, 'total'):
                    pbar.total = total_bytes
                pbar.update(bytes_transferred - pbar.n)

            processor(
                ftp_name=ftp_name,
                remote_path=remote_path,
                local_path=local_path,
                progress_callback=update_progress
            )

    def download_file_visualization(self, ftp_name, remote_path, local_path):
        """
        带可视化进度条的下载文件方法

        Args:
            ftp_name (str): FTP配置名称，指定使用哪个FTP服务器
            remote_path (str): 要下载的远程文件路径
            local_path (str): 本地保存路径，可以是文件路径或目录路径
                            如果是目录，文件将保存到该目录下，使用远程文件名

        Returns:
            bool: 下载是否成功（与download_file方法返回值一致）

        Example:
            >>> ftp_client.download_file_visualization(
            ...     "my_ftp",
            ...     "/server/data/large_file.zip",
            ...     "./downloads/large_file.zip"
            ... )
            # 显示：下载文件: 45%|████▌     | 45.2M/100M [00:30<00:45, 1.2MB/s]
        """
        self._visualization(
            ftp_name=ftp_name,
            remote_path=remote_path,
            local_path=local_path,
            processor=self.download_file,
            operation='download'
        )

    def upload_file_visualization(self, ftp_name, local_path, remote_path):
        """
        带可视化进度条的上传文件方法

        Args:
            ftp_name (str): FTP配置名称，指定使用哪个FTP服务器连接
            local_path (str): 要上传的本地文件路径，必须是存在的文件
            remote_path (str): 远程保存路径，可以是文件路径或目录路径
                             如果是目录，文件将保存到该目录下，使用本地文件名

        Returns:
            bool: 上传是否成功（与upload_file方法返回值一致）

        Example:
            >>> ftp_client.upload_file_visualization(
            ...     "my_ftp",
            ...     "./local/large_file.zip",
            ...     "/server/backups/large_file.zip"
            ... )
            # 显示：上传文件: 45%|████▌     | 45.2M/100M [00:30<00:45, 1.2MB/s]
        """
        self._visualization(
            ftp_name=ftp_name,
            remote_path=remote_path,
            local_path=local_path,
            processor=self.upload_file,
            operation='upload'
        )

    def _calculate_file_hash(self, file_path: str, hash_algorithm: str = 'md5') -> Optional[str]:
        """
        计算文件的哈希值

        Args:
            file_path (str): 文件路径
            hash_algorithm (str): 哈希算法，支持 'md5', 'sha1', 'sha256'

        Returns:
            Optional[str]: 文件的哈希值，计算失败返回None
        """
        import hashlib

        try:
            hash_obj = getattr(hashlib, hash_algorithm)()
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            self.logger.error(f"计算文件哈希值失败: {e}")
            return None

    def verify_file_integrity(self, ftp_name: str, remote_path: str, local_path: str,
                             hash_algorithm: str = 'md5') -> bool:
        """
        验证文件完整性

        Args:
            ftp_name (str): FTP配置名称
            remote_path (str): 远程文件路径
            local_path (str): 本地文件路径
            hash_algorithm (str): 哈希算法，支持 'md5', 'sha1', 'sha256'

        Returns:
            bool: 完整性验证是否通过
        """
        # 计算本地文件哈希值
        local_hash = self._calculate_file_hash(local_path, hash_algorithm)
        if not local_hash:
            self.logger.error(f"无法计算本地文件哈希值: {local_path}")
            return False

        # 尝试获取远程文件哈希值
        # 注意：FTP协议本身不支持直接获取文件哈希值
        # 这里我们通过比较文件大小来简单验证
        ftp = self._get_connection(ftp_name)
        if not ftp:
            self.logger.error(f"无法获取FTP连接: {ftp_name}")
            return False

        try:
            remote_size = ftp.size(remote_path)
            local_size = os.path.getsize(local_path)

            if remote_size == local_size:
                self.logger.info(f"文件完整性验证通过: {os.path.basename(local_path)}")
                self.logger.debug(f"文件大小匹配: {local_size} bytes")
                return True
            else:
                self.logger.error(f"文件大小不匹配: 本地={local_size} bytes, 远程={remote_size} bytes")
                return False
        except Exception as e:
            self.logger.error(f"验证文件完整性失败: {e}")
            return False

    def upload_file_list(self, ftp_name, local_path_list, remote_path_list,
                         progress_callback: Optional[Callable[[int, int, str], None]] = None,
                         batch_size: int = 20):
        """
        批量上传多个文件

        Args:
            ftp_name (str): FTP配置名称
            local_path_list (Union[str, List[str]]): 本地文件路径列表
                - str: 目录路径，会上传该目录下所有与远程文件名对应的文件
                - list: 每个文件对应的本地路径
            remote_path_list (List[str]): 远程保存路径列表
            progress_callback (Optional[Callable[[int, int, str], None]], optional): 进度回调函数
                - 参数1: 当前文件索引
                - 参数2: 总文件数
                - 参数3: 当前文件名
            batch_size (int, optional): 每批处理文件数

        Returns:
            tuple: (成功上传数量, 总文件数量)

        Example:
            >>> # 方式1: 上传指定文件到指定位置
            >>> success, total = client.upload_file_list(
            ...     ftp_name="server1",
            ...     local_path_list=["/local/file1.txt", "/local/file2.jpg"],
            ...     remote_path_list=["/remote/file1.txt", "/remote/file2.jpg"]
            ... )
            >>>
            >>> # 方式2: 上传目录下所有文件
            >>> success, total = client.upload_file_list(
            ...     ftp_name="server1",
            ...     local_path_list="/local/uploads",
            ...     remote_path_list=["/remote/file1.txt", "/remote/file2.jpg"]
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

            batch_success = 0
            for idx, (local_path, remote_path) in enumerate(batch, 1):
                file_idx = batch_start + idx
                filename = os.path.basename(local_path)

                if progress_callback:
                    progress_callback(file_idx, total_files, f"开始上传: {filename}")

                try:
                    if self.upload_file(ftp_name, local_path, remote_path):
                        # 验证文件完整性
                        if self.verify_file_integrity(ftp_name, remote_path, local_path):
                            success_count += 1
                            batch_success += 1
                            if progress_callback:
                                progress_callback(file_idx, total_files, f"✅ 完成: {filename}")
                        else:
                            failed_files.append((local_path, remote_path))
                            if progress_callback:
                                progress_callback(file_idx, total_files, f"❌ 完整性验证失败: {filename}")
                    else:
                        failed_files.append((local_path, remote_path))
                        if progress_callback:
                            progress_callback(file_idx, total_files, f"❌ 失败: {filename}")

                except Exception as e:
                    self.logger.error(f"处理文件 {filename} 时出错: {e}")
                    failed_files.append((local_path, remote_path))
                    if progress_callback:
                        progress_callback(file_idx, total_files, f"❌ 异常: {filename}")

            self.logger.info(f"批次完成: {batch_success}/{len(batch)} 成功")

            # 每批次完成后重置连接
            if batch_end < total_files:
                self.logger.info("重置连接以保持稳定性...")
                self._close_connection(ftp_name)
                time.sleep(1)

        if failed_files:
            self.logger.warning(f"上传失败文件: {len(failed_files)} 个")
            for local_path, _ in failed_files:
                self.logger.warning(f"  - {os.path.basename(local_path)}")

        return success_count, total_files

    def download_file_list(self, ftp_name, remote_path_list, local_path_list, bufsize=1024,
                           progress_callback: Optional[Callable[[int, int, str], None]] = None,
                           batch_size: int = 20, max_workers: int = 1):
        """批量下载多个文件（支持断点续传和分批处理）

        Args:
            ftp_name: 配置名称
            remote_path_list: 多个远程文件路径的list
            local_path_list: 可以是以下两种形式：
                     - str: 所有文件保存到该目录
                     - list: 每个文件对应的本地保存路径
            bufsize: 缓冲区大小（字节）
            progress_callback: 进度回调函数，接收三个参数：
                              (current_file_index, total_files, current_file_name)
            batch_size: 每批处理文件数，默认为20
            max_workers: 最大并行工作线程数，默认为1

        Returns:
            tuple: (成功下载数量, 总文件数量)

        Example:
            >>> def progress_callback(current, total, filename):
            ...     print(f"[{current}/{total}] 处理: {filename}")
            >>>
            >>> # 方式1: 所有文件保存到同一目录
            >>> success, total = client.download_file_list(
            ...     ftp_name="server1",
            ...     remote_path_list=["/remote/file1.txt", "/remote/file2.jpg"],
            ...     local_path_list="/local/downloads",
            ...     progress_callback=progress_callback,
            ...     max_workers=4
            ... )
            >>>
            >>> # 方式2: 每个文件指定保存路径
            >>> success, total = client.download_file_list(
            ...     ftp_name="server1",
            ...     remote_path_list=["/remote/file1.txt", "/remote/file2.jpg"],
            ...     local_path_list=["/local/file1.txt", "/local/file2.jpg"],
            ...     max_workers=2
            ... )
        """
        # 处理local_path_list的不同形式
        if isinstance(local_path_list, str):
            # 所有文件保存到同一目录
            download_tasks = [
                (remote_path, os.path.join(local_path_list, os.path.basename(remote_path)))
                for remote_path in remote_path_list
            ]
        elif isinstance(local_path_list, list):
            # 每个文件有独立的保存路径
            if len(local_path_list) != len(remote_path_list):
                raise ValueError("local_path_list长度必须与remote_path_list相同")
            download_tasks = list(zip(remote_path_list, local_path_list))
        else:
            raise TypeError("local_path_list必须是字符串或列表")

        total_files = len(download_tasks)
        success_count = 0
        failed_files = []

        # 添加连接保活机制
        conn = None
        if hasattr(self, '_ftp') and self._ftp:
            conn = self._ftp
        else:
            conn = self._get_connection(ftp_name)
        
        noop_count = 0
        noop_interval = 5  # 每5个文件发送一次NOOP命令保持连接
        reconnect_count = 0
        max_reconnects = 10  # 最多重新连接10次
        batch_reconnect_size = 50  # 每50个文件重新连接一次

        # 分批处理
        for batch_start in range(0, total_files, batch_size):
            batch_end = min(batch_start + batch_size, total_files)
            batch = download_tasks[batch_start:batch_end]

            self.logger.info(f"下载批次 {batch_start // batch_size + 1}/{(total_files + batch_size - 1) // batch_size} "
                             f"({batch_start + 1}-{batch_end}/{total_files})")

            # 定期重新连接，避免长时间使用同一连接
            if batch_start > 0 and batch_start % batch_reconnect_size == 0:
                self.logger.info(f"定期重新连接 (已处理{batch_start}个文件)")
                try:
                    self._close_connection(ftp_name)
                    conn = self._get_connection(ftp_name)
                    self.logger.info(f"定期重新连接成功")
                except Exception as reconnect_error:
                    self.logger.warning(f"定期重新连接失败: {str(reconnect_error)}")
                    # 尝试获取新连接
                    try:
                        conn = self._get_connection(ftp_name)
                    except Exception as e:
                        self.logger.error(f"获取新连接失败: {str(e)}")

            batch_success = 0
            for idx, (remote_path, local_path) in enumerate(batch, 1):
                file_idx = batch_start + idx
                filename = os.path.basename(remote_path)

                if progress_callback:
                    progress_callback(file_idx, total_files, f"开始下载: {filename}")

                try:
                    # 使用download_file方法处理单个文件，支持断点续传和重试
                    if self.download_file(ftp_name, remote_path, local_path, bufsize):
                        # 验证文件完整性
                        if self.verify_file_integrity(ftp_name, remote_path, local_path):
                            success_count += 1
                            batch_success += 1
                            if progress_callback:
                                progress_callback(file_idx, total_files, f"✅ 完成: {filename}")
                        else:
                            failed_files.append((remote_path, local_path))
                            if progress_callback:
                                progress_callback(file_idx, total_files, f"❌ 完整性验证失败: {filename}")
                    else:
                        failed_files.append((remote_path, local_path))
                        if progress_callback:
                            progress_callback(file_idx, total_files, f"❌ 失败: {filename}")

                except Exception as e:
                    self.logger.error(f"处理文件 {filename} 时出错: {e}")
                    failed_files.append((remote_path, local_path))
                    if progress_callback:
                        progress_callback(file_idx, total_files, f"❌ 异常: {filename}")
                finally:
                    # 连接保活：定期发送NOOP命令
                    if conn:
                        noop_count += 1
                        if noop_count >= noop_interval:
                            try:
                                conn.voidcmd('NOOP')
                                self.logger.debug(f"发送NOOP命令保持连接 (已处理{file_idx}个文件)")
                                noop_count = 0
                            except Exception as e:
                                self.logger.warning(f"发送NOOP命令失败: {str(e)}")
                                # 尝试重新连接
                                if reconnect_count < max_reconnects:
                                    try:
                                        self._close_connection(ftp_name)
                                        conn = self._get_connection(ftp_name)
                                        reconnect_count += 1
                                        self.logger.info(f"NOOP失败后重新连接成功 (第{reconnect_count}次)")
                                    except Exception as reconnect_error:
                                        self.logger.error(f"重新连接失败: {str(reconnect_error)}")

            self.logger.info(f"批次完成: {batch_success}/{len(batch)} 成功")

        if failed_files:
            self.logger.warning(f"下载失败文件: {len(failed_files)} 个")
            for remote_path, _ in failed_files:
                self.logger.warning(f"  - {os.path.basename(remote_path)}")

        if progress_callback:
            progress_callback(total_files, total_files, "下载完成")

        return success_count, total_files

