import io
import os
import time
from typing import Dict, Callable, Optional

import paramiko
from tqdm import tqdm

from .basic import set_logging
from .constants import TIMEOUT, RETRY_TIMES


class SFTPClient:
    """
    SFTP客户端类，提供安全的文件传输协议操作

    支持多服务器配置管理、断点续传、进度监控、错误重试等功能。
    适用于需要安全可靠地进行文件上传下载的场景。
    """

    def __init__(self, sftp_configs: Dict[str, dict], verbose=False):
        """
        初始化SFTP客户端

        Args:
            sftp_configs (Dict[str, dict]): SFTP配置字典，格式为：
                {
                    "sftp_server1": {
                        "host": "sftp.example.com",
                        "port": 22,
                        "username": "username",
                        "password": "password",
                        "timeout": 30
                    },
                    "sftp_server2": {...}
                }
            verbose (bool, optional): 是否启用详细日志，默认为False

        Example:
            >>> sftp_config = {
            ...     "production_sftp": {
            ...         "host": "sftp.example.com",
            ...         "port": 22,
            ...         "username": "user",
            ...         "password": "pass123"
            ...     }
            ... }
            >>> client = SFTPClient(sftp_config, verbose=True)
        """
        self._configs = sftp_configs
        self._transport = None
        self._sftp = None
        self.sftp_name = None
        self.logger = set_logging("SFTPClient", verbose=verbose)

    def _sftpconnect(self, sftp_name=None):
        """
        连接SFTP服务器

        Args:
            sftp_name (str, optional): SFTP配置名称，如果为None则使用当前配置

        Returns:
            paramiko.SFTPClient: 已连接的SFTP客户端实例

        Raises:
            ValueError: 当SFTP配置不存在时
            RuntimeError: 当连接失败时

        Example:
            >>> client._sftpconnect("production_sftp")
        """
        if sftp_name is not None:
            self.sftp_name = sftp_name
        if self.sftp_name not in self._configs:
            raise ValueError(f"SFTP配置 '{self.sftp_name}' 不存在")

        config = self._configs[self.sftp_name]

        try:
            # 1. 创建SSH客户端
            self._ssh_client = paramiko.SSHClient()
            self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # 2. 认证
            if 'password' in config:
                self._ssh_client.connect(
                    hostname=config['host'],
                    port=config['port'],
                    username=config['username'],
                    password=config['password'],
                    timeout=TIMEOUT
                )
            else:
                raise ValueError("必须提供密码进行认证")

            # 3. 创建SFTP客户端
            self._sftp = self._ssh_client.open_sftp()
            self._sftp.get_channel().settimeout(TIMEOUT)

            self.logger.info(f"✅ 成功连接到SFTP: {self.sftp_name}")
            return self._sftp

        except Exception as e:
            self.close()
            raise RuntimeError(f"SFTP连接失败: {e}")

    def _sftp_reconnect(self):
        """重新连接SFTP服务器"""
        self.close()
        self._sftpconnect()

    def is_connected(self, sftp_name):
        """
        检查是否能够连接到指定的SFTP服务器

        Args:
            sftp_name (str): SFTP配置名称

        Returns:
            bool: 连接是否成功

        Example:
            >>> if client.is_connected("production_sftp"):
            ...     print("连接正常")
        """
        try:
            if not self._sftp:
                self._sftpconnect(sftp_name)
                self.close()
            return True
        except:
            return False

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """上下文管理器退出，自动关闭连接"""
        self._close()

    def _close(self):
        """关闭SFTP连接"""
        if self._sftp:
            try:
                self._sftp.close()
            except:
                pass
            finally:
                self._sftp = None
        if self._transport:
            try:
                self._transport.close()
            except:
                pass
            finally:
                self._transport = None

    def _safe_sftp_op(self, operation: Callable):
        """
        带重试机制的SFTP操作封装

        Args:
            operation (Callable): 要执行的SFTP操作函数

        Returns:
            Any: 操作函数的返回值，失败时返回None

        Example:
            >>> result = client._safe_sftp_op(lambda: client._sftp.listdir("/remote/path"))
        """
        for retry in range(RETRY_TIMES):
            try:
                if self._sftp:
                    return operation()
            except Exception as e:
                self.logger.warning('SFTP操作异常: %s', str(e))
            time.sleep(TIMEOUT ** (retry + 1))
            self._sftp_reconnect()
        return None

    def _file_exists(self, path):
        """
        检查远程文件是否存在

        Args:
            path (str): 远程文件路径

        Returns:
            bool: 文件是否存在

        Example:
            >>> if client._file_exists("/remote/file.txt"):
            ...     print("文件存在")
        """
        try:
            self._sftp.stat(path)
            return True
        except:
            return False

    def is_dir(self, remote_path):
        """
        判断远程路径是否为目录

        Args:
            remote_path (str): 远程路径

        Returns:
            bool: 是否为目录

        Example:
            >>> if client.is_dir("/remote/directory"):
            ...     print("这是一个目录")
        """
        try:
            return self._safe_sftp_op(lambda: self._sftp.stat(remote_path).st_mode & 0o40000 != 0)
        except:
            return False

    def list_dir(self, remote_dir):
        """
        列出远程目录内容

        Args:
            remote_dir (str): 远程目录路径

        Returns:
            List[str]: 目录内容列表

        Example:
            >>> files = client.list_dir("/remote/directory")
            >>> for file in files:
            ...     print(file)
        """
        return self._safe_sftp_op(lambda: self._sftp.listdir(remote_dir)) or []

    def get_dir_file_list(self, sftp_name, sftp_dir):
        """
        递归获取SFTP目录下的所有文件列表

        Args:
            sftp_name (str): SFTP配置名称
            sftp_dir (str): 远程目录路径

        Returns:
            List[str]: 完整的文件路径列表

        Example:
            >>> file_list = client.get_dir_file_list("production_sftp", "/data/images")
            >>> print(f"找到 {len(file_list)} 个文件")
        """
        if not self._sftp:
            self.sftp_name = sftp_name
            self._sftpconnect()

        file_list = []
        try:
            for filename in self.list_dir(sftp_dir):
                full_path = os.path.join(sftp_dir, filename)
                if self.is_dir(full_path):
                    file_list.extend(self.get_dir_file_list(sftp_name, full_path))
                else:
                    file_list.append(full_path)
        finally:
            self._close()
        return file_list

    def download_file(self, sftp_name, remote_path, local_path,
                      progress_callback: Optional[Callable[[int, int], None]] = None):
        """
        下载单个大文件（支持断点续传）

        Args:
            sftp_name (str): SFTP配置名称
            remote_path (str): 远程文件路径
            local_path (str): 本地保存路径
            progress_callback (Optional[Callable[[int, int], None]], optional):
                进度回调函数，接收两个参数(bytes_transferred, total_bytes)

        Returns:
            bool: 是否下载成功

        Example:
            >>> def progress_callback(transferred, total):
            ...     print(f"进度: {transferred}/{total} bytes")
            >>>
            >>> success = client.download_file(
            ...     "production_sftp",
            ...     "/remote/data.zip",
            ...     "/local/data.zip",
            ...     progress_callback=progress_callback
            ... )
        """
        if not self._sftp:
            self.sftp_name = sftp_name
            self._sftpconnect()

        try:
            # 分离目录和文件名
            remote_dir, filename = os.path.split(remote_path)
            local_path = os.path.join(local_path, filename) if os.path.isdir(local_path) else local_path

            # 获取文件大小
            file_size = self._sftp.stat(remote_path).st_size
            if not file_size:
                self.logger.error("无法获取远程文件大小")
                return False

            # 检查断点续传（本地已下载部分）
            downloaded = 0
            if os.path.exists(local_path):
                local_size = os.path.getsize(local_path)
                if local_size == file_size:
                    self.logger.info(f"🔄 文件已存在且完整，跳过下载: {local_path}")
                    return True
                elif 0 < local_size < file_size:
                    self.logger.info(f"⏩ 检测到部分下载文件，尝试从字节 {local_size} 续传")
                    downloaded = local_size

            # 创建本地目录（如果不存在）
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # 定义回调函数
            callback = None
            if progress_callback:
                def _callback(x, y):
                    progress_callback(x + downloaded, file_size)

                callback = _callback

            # 使用SFTP的get方法下载文件
            if downloaded > 0:
                # 断点续传需要特殊处理
                with open(local_path, 'ab') as f:
                    # 先发送REST命令告诉服务器从哪个位置开始续传
                    self._sftp.get_channel().send(f"REST {downloaded}\r\n")
                    # 然后下载剩余部分
                    self._sftp.getfo(remote_path, f, callback=callback)
            else:
                # 全新下载
                self._sftp.get(remote_path, local_path, callback=callback)

            # 验证完整性
            if os.path.getsize(local_path) != file_size:
                os.remove(local_path)  # 删除不完整文件
                raise RuntimeError(f"下载不完整: {downloaded}/{file_size}字节")

            self.logger.info(f"✅ 文件已保存至: {local_path}")
            return True

        except Exception as e:
            if os.path.exists(local_path):
                os.remove(local_path)  # 清理残留文件
            self.logger.error(f"❌ 下载失败: {e}")
            return False
        finally:
            self._close()

    def upload_file(self, sftp_name, local_path, remote_path,
                    progress_callback: Optional[Callable[[int, int], None]] = None):
        """
        上传单个大文件（支持断点续传）

        Args:
            sftp_name (str): SFTP配置名称
            local_path (str): 本地文件路径
            remote_path (str): 远程保存路径
            progress_callback (Optional[Callable[[int, int], None]], optional):
                进度回调函数，接收两个参数(bytes_transferred, total_bytes)

        Returns:
            bool: 是否上传成功

        Example:
            >>> success = client.upload_file(
            ...     "production_sftp",
            ...     "/local/data.zip",
            ...     "/remote/data.zip"
            ... )
        """
        if not self._sftp:
            self.sftp_name = sftp_name
            self._sftpconnect()

        try:
            # 分离目录和文件名
            remote_dir, filename = os.path.split(remote_path)

            # 创建远程目录（如果不存在）
            try:
                self._sftp.stat(remote_dir)
            except IOError:
                self._sftp.mkdir(remote_dir)

            # 获取本地文件大小
            file_size = os.path.getsize(local_path)
            uploaded = 0

            # 检查断点续传
            try:
                remote_size = self._sftp.stat(remote_path).st_size
                if remote_size == file_size:
                    self.logger.info(f"🔄 文件已存在且完整，跳过上传: {remote_path}")
                    return True
                elif remote_size > 0:
                    self.logger.info(f"⏩ 检测到部分上传文件，尝试从字节 {remote_size} 续传")
                    uploaded = remote_size
            except IOError:
                pass

            # 准备回调函数
            callback = None
            if progress_callback:
                def _callback(x, y):
                    progress_callback(x + uploaded, file_size)

                callback = _callback

            # 分块上传实现
            chunk_size = 1024 * 1024  # 1MB chunks
            # 使用临时文件实现断点续传
            temp_path = remote_path + '.part'

            with open(local_path, 'rb') as fp:
                if uploaded > 0:
                    fp.seek(uploaded)

                # 如果是续传且临时文件不存在，尝试从原始文件续传
                if uploaded > 0 and not self._file_exists(temp_path):
                    self.logger.warning("⚠️ 临时文件不存在，尝试从原始文件续传")
                    try:
                        existing_size = self._sftp.stat(remote_path).st_size
                        if existing_size == uploaded:
                            self.logger.info("原始文件续传点验证通过")
                        else:
                            raise RuntimeError("原始文件大小不匹配")
                    except Exception as e:
                        self.logger.error(f"续传验证失败: {e}")
                        uploaded = 0
                        fp.seek(0)

                # 分块上传
                while True:
                    chunk = fp.read(chunk_size)
                    if not chunk:
                        break

                    # 使用BytesIO包装chunk
                    chunk_io = io.BytesIO(chunk)

                    if uploaded == 0 and fp.tell() == len(chunk):
                        # 全新上传
                        self._sftp.putfo(
                            chunk_io,
                            temp_path,
                            file_size=file_size,
                            callback=callback
                        )
                    else:
                        # 断点续传需要特殊处理
                        with self._sftp.open(temp_path, 'ab') as remote_file:
                            chunk_io.seek(0)
                            while True:
                                data = chunk_io.read(1024 * 32)  # 32KB blocks
                                if not data:
                                    break
                                remote_file.write(data)
                                if callback:
                                    callback(len(data), file_size)

                    uploaded = fp.tell()
                    self.logger.debug(f"已上传: {uploaded}/{file_size} bytes")

            # 验证并重命名
            temp_size = self._sftp.stat(temp_path).st_size
            if temp_size != file_size:
                raise RuntimeError(f"临时文件不完整: {temp_size}/{file_size}")

            self._sftp.rename(temp_path, remote_path)

            # 验证完整性
            remote_final_size = self._sftp.stat(remote_path).st_size
            if remote_final_size != file_size:
                try:
                    self._sftp.remove(remote_path)  # 删除不完整文件
                except:
                    pass
                raise RuntimeError(f"上传不完整: {remote_final_size}/{file_size}字节")

            self.logger.info(f"✅ 文件已上传至: {remote_path}")
            return True

        except Exception as e:
            self.logger.error(f"❌ 上传失败: {e}")
            return False
        finally:
            self._close()

    def _visualization(self, sftp_name, remote_path, local_path, processor, operation='download'):
        """
        统一的上传/下载可视化方法

        Args:
            sftp_name (str): SFTP配置名称
            remote_path (str): 远程路径
            local_path (str): 本地路径
            processor (Callable): 处理函数 (upload_file 或 download_file)
            operation (str): 操作类型 ('upload' 或 'download')

        Example:
            >>> client._visualization(
            ...     "production_sftp",
            ...     "/remote/file.txt",
            ...     "/local/file.txt",
            ...     client.download_file,
            ...     'download'
            ... )
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

            processor(
                sftp_name=sftp_name,
                remote_path=remote_path,
                local_path=local_path,
                progress_callback=update_progress
            )

    def download_file_visualization(self, sftp_name, remote_path, local_path):
        """
        下载文件可视化（带进度条）

        Args:
            sftp_name (str): SFTP配置名称
            remote_path (str): 远程文件路径
            local_path (str): 本地保存路径

        Example:
            >>> client.download_file_visualization(
            ...     "production_sftp",
            ...     "/remote/data.zip",
            ...     "/local/data.zip"
            ... )
        """
        self._visualization(
            sftp_name=sftp_name,
            remote_path=remote_path,
            local_path=local_path,
            processor=self.download_file,
            operation='download'
        )

    def upload_file_visualization(self, sftp_name, local_path, remote_path):
        """
        上传文件可视化（带进度条）

        Args:
            sftp_name (str): SFTP配置名称
            local_path (str): 本地文件路径
            remote_path (str): 远程保存路径

        Example:
            >>> client.upload_file_visualization(
            ...     "production_sftp",
            ...     "/local/data.zip",
            ...     "/remote/data.zip"
            ... )
        """
        self._visualization(
            sftp_name=sftp_name,
            remote_path=remote_path,
            local_path=local_path,
            processor=self.upload_file,
            operation='upload'
        )

    def download_file_list(self, sftp_name, remote_path_list, local_path_list,
                           progress_callback: Optional[Callable[[int, int, str], None]] = None):
        """
        下载多个文件（支持断点续传）

        Args:
            sftp_name (str): SFTP配置名称
            remote_path_list (List[str]): 远程文件路径列表
            local_path_list (Union[str, List[str]]): 本地保存路径，可以是：
                - str: 所有文件保存到该目录
                - list: 每个文件对应的本地保存路径
            progress_callback (Optional[Callable[[int, int, str], None]], optional):
                进度回调函数，接收三个参数：(current_file_index, total_files, current_file_name)

        Returns:
            tuple: (成功下载数量, 总文件数量)

        Example:
            >>> def progress_callback(current, total, filename):
            ...     print(f"正在下载 {current}/{total}: {filename}")
            >>>
            >>> success, total = client.download_file_list(
            ...     "production_sftp",
            ...     ["/remote/file1.txt", "/remote/file2.jpg"],
            ...     "/local/downloads",
            ...     progress_callback=progress_callback
            ... )
        """
        if not self._sftp:
            self.sftp_name = sftp_name
            self._sftpconnect()

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
                raise ValueError("save_dir列表长度必须与file_list相同")
            download_tasks = list(zip(remote_path_list, local_path_list))
        else:
            raise TypeError("save_dir必须是字符串或列表")

        total_files = len(download_tasks)
        success_count = 0

        try:
            for idx, (remote_path, local_path) in enumerate(download_tasks, 1):
                filename = os.path.basename(remote_path)

                # 通知回调当前文件
                if progress_callback:
                    progress_callback(idx, total_files, filename)

                try:
                    # 检查远程文件是否存在
                    try:
                        file_size = self._sftp.stat(remote_path).st_size
                        if not file_size:
                            self.logger.error(f"远程文件为空: {filename}")
                            continue
                    except Exception as e:
                        self.logger.error(f"无法访问远程文件 {filename}: {str(e)}")
                        continue

                    # 创建本地目录（如果不存在）
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)

                    # 检查断点续传（本地已下载部分）
                    downloaded = 0
                    if os.path.exists(local_path):
                        local_size = os.path.getsize(local_path)
                        if local_size == file_size:
                            self.logger.info(f"🔄 文件已存在且完整，跳过下载: {filename}")
                            success_count += 1
                            continue
                        elif 0 < local_size < file_size:
                            self.logger.info(
                                f"⏩ 检测到部分下载文件，尝试续传: {filename} ({local_size}/{file_size} bytes)")
                            downloaded = local_size

                    # 下载文件（使用正确的参数传递方式）
                    if downloaded > 0:
                        # 断点续传模式
                        with open(local_path, 'ab') as f:
                            self._sftp.getfo(
                                remotepath=remote_path,
                                fl=f,
                                callback=lambda x, y: progress_callback(idx, total_files,
                                                                        f"{filename} ({int(100 * (x + downloaded) / file_size)}%)") if progress_callback else None
                            )
                    else:
                        # 全新下载模式
                        self._sftp.get(
                            remotepath=remote_path,
                            localpath=local_path,
                            callback=lambda x, y: progress_callback(idx, total_files,
                                                                    f"{filename} ({int(100 * x / file_size)}%)") if progress_callback else None
                        )

                    # 验证完整性
                    if os.path.getsize(local_path) != file_size:
                        os.remove(local_path)
                        raise RuntimeError(f"下载不完整: {os.path.getsize(local_path)}/{file_size}字节")

                    success_count += 1
                    self.logger.info(f"✅ {success_count}/{total_files} 下载成功: {filename} -> {local_path}")

                except Exception as e:
                    if os.path.exists(local_path):
                        os.remove(local_path)
                    self.logger.error(f"❌ 下载失败 {filename}: {str(e)}")

            return success_count, total_files

        finally:
            self._close()

    def download_single_file(self, sftp_name, remote_path, local_path):
        """
        下载单个文件（简单版本）

        Args:
            sftp_name (str): SFTP配置名称
            remote_path (str): 远程文件路径
            local_path (str): 本地保存路径

        Returns:
            bool: 是否下载成功

        Example:
            >>> success = client.download_single_file(
            ...     "production_sftp",
            ...     "/remote/config.ini",
            ...     "/local/config.ini"
            ... )
        """
        if not self._sftp:
            self.sftp_name = sftp_name
            self._sftpconnect()

        try:
            # 分离目录和文件名
            remote_dir, filename = os.path.split(remote_path)
            local_path = os.path.join(local_path, filename) if os.path.isdir(local_path) else local_path

            # 创建本地目录（如果不存在）
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # 下载
            self._sftp.get(remote_path, local_path)

            self.logger.info(f"✅ 文件已保存至: {local_path}")
            return True

        except Exception as e:
            if os.path.exists(local_path):
                os.remove(local_path)  # 清理残留文件
            self.logger.error(f"❌ 下载失败: {e}")
            return False
