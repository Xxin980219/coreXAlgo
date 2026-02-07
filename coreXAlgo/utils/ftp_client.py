import io
import os
import socket
import time
from ftplib import FTP, error_proto, error_perm, error_temp, all_errors, error_reply
from typing import Dict, Callable, Optional

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
        - 自动连接和重连机制
        - 文件上传下载（支持断点续传）
        - 目录遍历和文件列表获取
        - 进度可视化和回调通知
        - 异常处理和重试机制

    Example:
        >>> from ftplib import FTP
        >>> ftp_configs = {
        ...     "server1": {
        ...         "host": "ftp.example.com",
        ...         "port": 21,
        ...         "username": "user",
        ...         "password": "pass"
        ...     }
        ... }
        >>> client = FTPClient(ftp_configs, verbose=True)
        >>> client.download_file("server1", "/remote/file.txt", "./local/file.txt")
    """

    def __init__(self, ftp_configs: Dict[str, dict], verbose=False):
        """
        初始化FTP客户端

        Args:
            ftp_configs: FTP配置字典，格式为 {ftp_name: {host, port, username, password, ...}}
            verbose: 是否启用详细日志输出
        """
        self._configs = ftp_configs
        self._ftp = None
        self.ftp_name = None
        self.logger = set_logging("FTPClient", verbose=verbose)

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
        self._ftp = FTP(timeout=TIMEOUT)
        self._ftp.set_debuglevel(debug_level)  # 开启调试日志

        try:
            # 1. 连接服务器
            try:
                self._ftp.connect(self._configs[self.ftp_name]['host'], self._configs[self.ftp_name]['port'],
                                  timeout=TIMEOUT)
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
                login_resp = self._ftp.login(self._configs[self.ftp_name]['username'],
                                             self._configs[self.ftp_name]['password'])
                if '230' not in login_resp:  # 检查登录响应码
                    raise RuntimeError(f"登录失败: {login_resp}")
            except error_perm as e:
                raise RuntimeError(f"认证失败（用户名/密码错误）: {e}")
            except error_temp as e:
                raise RuntimeError(f"临时服务器错误: {e}")

            # 3. 设置传输模式
            try:
                self._ftp.set_pasv(False)  # 主动模式
                # 验证模式是否设置成功（通过发送NOOP命令）
                if '200' not in self._ftp.sendcmd('NOOP'):
                    raise RuntimeError("无法切换到主动模式")
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

    def is_connected(self, ftp_name, debug_level=0):
        """
        检查与指定FTP服务器的连接状态

        Args:
            ftp_name (str): FTP配置名称，用于标识要检查的服务器配置
            debug_level (int): 调试级别，传递给_ftpconnect方法
                             0: 无调试输出
                             1: 输出命令和响应
                             2: 输出完整通信详情

        Returns:
            bool: 连接状态
                True: 服务器可达且认证成功
                False: 连接失败、认证失败或配置不存在
        """
        try:
            if not self._ftp:
                self._ftpconnect(ftp_name, debug_level)
                self._close()
            return True
        except:
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
        if not self._ftp:
            self.ftp_name = ftp_name
            self._ftpconnect()
        file_list = []

        try:
            for filename in self.list_dir(ftp_dir):
                full_path = os.path.join(ftp_dir, filename)

                if self.is_dir(full_path):
                    file_list.extend(self.get_dir_file_list(ftp_name, full_path))
                else:
                    file_list.append(full_path)
        finally:
            self._close()
        return file_list

    def download_file(self, ftp_name, remote_path, local_path, bufsize=1024,
                      progress_callback: Optional[Callable[[int, int], None]] = None):
        """下载单个大文件（支持断点续传）

        Args:
            ftp_name: 配置名称
            remote_path: 远程文件路径
            local_path: 本地保存路径
            bufsize: 缓冲区大小（字节）
            progress_callback: 进度回调（0-100）,接收两个参数(bytes_transferred, total_bytes)

        Returns:
            bool: 是否下载成功
        """
        if not self._ftp:
            self.ftp_name = ftp_name
            self._ftpconnect()
        try:
            # 分离目录和文件名
            remote_dir, filename = os.path.split(remote_path)
            local_path = os.path.join(local_path, filename) if os.path.isdir(local_path) else local_path

            # 获取文件大小
            file_size = self._ftp.size(remote_path)
            if not file_size:
                self.logger.error("无法获取远程文件大小")
                return False

            # 检查断点续传（本地已下载部分）
            downloaded = 0
            if os.path.exists(local_path):
                local_size = os.path.getsize(local_path)
                if local_size == file_size:
                    self.logger.info(f"🔄 文件已存在且完整，跳过下载: {local_path}")
                    return
                elif 0 < local_size < file_size:
                    self.logger.info(f"⏩ 检测到部分下载文件，尝试从字节 {local_size} 续传")
                    downloaded = local_size
                    try:
                        self._ftp.voidcmd(f"REST {local_size}")  # FTP断点续传命令
                    except error_reply as e:
                        if "350" not in str(e):
                            self.logger.warning("⚠️ 续传协商失败，重新下载")
                            os.remove(local_path)
                            downloaded = 0

            with open(local_path, 'ab' if downloaded > 0 else 'wb') as f:
                # 定义下载回调
                callback = _ftp_block_callback(
                    file_size=file_size - downloaded,
                    percent_callback=None,
                    size_callback=progress_callback,
                    process_block=f.write
                )
                self._ftp.retrbinary(f"RETR {remote_path}", callback, bufsize, rest=downloaded)

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

    def upload_file(self, ftp_name, local_path, remote_path, bufsize=1024,
                    progress_callback: Optional[Callable[[int, int], None]] = None):
        """上传单个文件（支持断点续传）

        Args:
            ftp_name: 配置名称
            local_path: 本地文件路径
            remote_path: 远程保存路径
            bufsize: 缓冲区大小（字节）
            progress_callback: 进度回调（0-100）,接收两个参数(bytes_transferred, total_bytes)

        Returns:
            bool: 是否上传成功
        """
        if not self._ftp:
            self.ftp_name = ftp_name
            self._ftpconnect()

        try:
            # 分离目录和文件名
            remote_dir, filename = os.path.split(remote_path)
            # 切换工作目录
            if remote_dir:
                self._safe_ftp_op(lambda: self._ftp.cwd(remote_dir))

            # 获取本地文件大小
            file_size = os.path.getsize(local_path)
            uploaded = 0

            # 检查断点续传
            try:
                remote_size = self._ftp.size(filename)
                if remote_size == file_size:
                    print(f"🔄 文件已存在且完整，跳过上传: {remote_path}")
                    return True
                elif remote_size > 0:
                    print(f"⏩ 检测到部分上传文件，尝试从字节 {remote_size} 续传")
                    uploaded = remote_size
            except:
                pass

            with open(local_path, 'rb') as fp:
                if uploaded > 0:
                    fp.seek(uploaded)  # 跳转到续传位置

                    callback = _ftp_block_callback(
                        file_size=file_size - uploaded,
                        percent_callback=None,
                        size_callback=progress_callback,
                        process_block=None
                    )

                    # 分块读取上传（避免内存溢出）
                    while uploaded < file_size:
                        chunk = fp.read(min(bufsize, file_size - uploaded))
                        if not chunk:
                            break

                        self._ftp.storbinary(
                            f"APPE {filename}" if uploaded else f"STOR {filename}",
                            io.BytesIO(chunk),
                            blocksize=len(chunk)
                        )
                        uploaded += len(chunk)
                        callback(chunk)

            # 验证完整性
            if uploaded != file_size:
                raise RuntimeError(f"上传不完整: {uploaded}/{file_size}字节")

            self.logger.info(f"✅ 文件已上传至: {remote_path}")
            return True

        except Exception as e:
            self.logger.error(f"❌ 下载失败: {e}")
            return False
        finally:
            self._close()

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

    def download_file_list(self, ftp_name, remote_path_list, local_path_list, bufsize=1024,
                           progress_callback: Optional[Callable[[int, int, str], None]] = None):
        """下载多个文件（支持断点续传）

        Args:
            ftp_name: 配置名称
            remote_path_list: 多个远程文件路径的list
            local_path_list: 可以是以下两种形式：
                     - str: 所有文件保存到该目录
                     - list: 每个文件对应的本地保存路径
            bufsize: 缓冲区大小（字节）
            progress_callback: 进度回调函数，接收三个参数：
                              (current_file_index, total_files, current_file_name)

        Returns:
            bool: 是否下载成功
        """
        if not self._ftp:
            self.ftp_name = ftp_name
            self._ftpconnect()

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
                    # 获取文件大小,检查远程文件是否存在
                    try:
                        # 获取文件大小,检查远程文件是否存在
                        file_size = self._ftp.size(remote_path)
                        if not file_size:
                            self.logger.error(f"远程文件为空: {filename}")
                            continue
                    except Exception as e:
                        self.logger.error(f"无法访问远程文件 {filename}: {str(e)}")
                        continue

                    # 创建本地目录
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)

                    # 检查断点续传（本地已下载部分）
                    downloaded = 0
                    if os.path.exists(local_path):
                        local_size = os.path.getsize(local_path)
                        if local_size == file_size:
                            self.logger.info(f"🔄 文件已存在且完整，跳过下载: {local_path}")
                            success_count += 1
                            continue
                        elif 0 < local_size < file_size:
                            self.logger.info(
                                f"⏩ 检测到部分下载文件，尝试续传: {filename} ({local_size}/{file_size} bytes)")
                            downloaded = local_size
                            try:
                                self._ftp.voidcmd(f"REST {local_size}")  # FTP断点续传命令
                            except error_reply as e:
                                if "350" not in str(e):
                                    self.logger.warning("⚠️ 续传协商失败，重新下载")
                                    os.remove(local_path)
                                    downloaded = 0

                    with open(local_path, 'ab' if downloaded > 0 else 'wb') as f:
                        def _update_progress(block):
                            """适配单文件进度回调"""
                            f.write(block)
                            if progress_callback:
                                current_size = os.path.getsize(local_path)
                                percent = min(100, int(current_size * 100 / file_size))
                                progress_callback(idx, total_files, f"{filename} ({percent}%)")

                        try:
                            self._ftp.retrbinary(f"RETR {remote_path}", _update_progress, bufsize, rest=downloaded)
                        except Exception as e:
                            self.logger.error(f"下载失败: {remote_path}: {str(e)}")
                            if os.path.exists(local_path):
                                os.remove(local_path)
                            continue

                        # 验证完整性
                        if os.path.getsize(local_path) != file_size:
                            os.remove(local_path)
                            self.logger.error(
                                f"下载不完整: {local_path} ({os.path.getsize(local_path)}/{file_size}字节)")
                            continue

                    success_count += 1
                    self.logger.info(f"✅ {success_count}/{total_files} 下载成功: {filename} -> {local_path}")

                except Exception as e:
                    self.logger.error(f"❌ 处理文件 {filename} 时出错: {str(e)}")
                    if os.path.exists(local_path):
                        os.remove(local_path)

        finally:
            self._close()
            if progress_callback:
                progress_callback(total_files, total_files, "下载完成")

        return success_count

