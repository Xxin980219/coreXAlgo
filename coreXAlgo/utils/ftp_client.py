import io
import os
import socket
import time
from ftplib import FTP, error_proto, error_perm, error_temp, all_errors, error_reply
from typing import Dict, Callable, Optional

from tqdm import tqdm

from ..utils import set_logging

__all__ = ['FTPClient']


def _ftp_block_callback(file_size, percent_callback=None, size_callback=None, process_block=None):
    """ load/upload block callback

    :param file_size(int): total file size
    :param percent_callback(function): 进度百分比回调函数
    :param size_callback(function): 进度已下载大小回调函数
    :param process_block(function): 原始数据处理函数，如写入文件
    :return: (function)
    """
    load_progress = [0, -1]  # [load_size, load_percent]

    def _callback_wrapper(data: bytes):
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
    TIMEOUT = 5
    RETRY_TIMES = 3

    def __init__(self, ftp_configs: Dict[str, dict], verbose=False):
        """
        初始化FTP客户端
        :param ftp_configs: ftp配置字典 {ftp_name: {host,port,username,password,...}}
        """
        self._configs = ftp_configs
        self._ftp = None
        self.ftp_name = None
        self.logger = set_logging("FTPClient", verbose=verbose)

    def _ftpconnect(self, ftp_name=None, debug_level=0):
        """
        :param debug_level: 调试级别
                            0: 无输出
                            1: 命令和响应
                            2: 完整通信详情
        """
        if ftp_name is not None:
            self.ftp_name = ftp_name
        if self.ftp_name not in self._configs:
            raise ValueError(f"FTP配置 '{self.ftp_name}' 不存在")

        config = self._configs[self.ftp_name]
        self._ftp = FTP(timeout=self.TIMEOUT)
        self._ftp.set_debuglevel(debug_level)  # 开启调试日志

        try:
            # 1. 连接服务器
            try:
                self._ftp.connect(self._configs[self.ftp_name]['host'], self._configs[self.ftp_name]['port'],
                                  timeout=self.TIMEOUT)
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
            self.close()
            raise RuntimeError(f"FTP操作失败: {e}")

    def _ftp_reconnect(self):
        self.close()
        self._ftpconnect()

    def is_connected(self, ftp_name, debug_level=0):
        try:
            if not self._ftp:
                self._ftpconnect(ftp_name, debug_level)
                self.close()
            return True
        except:
            return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
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
        for retry in range(self.RETRY_TIMES):
            try:
                if self._ftp:
                    return operation()
            except error_perm as e:
                self.logger.warning('FTP权限错误: %s', str(e))
                return None
            except Exception as e:
                self.logger.warning('FTP操作异常: %s', str(e))
            time.sleep(self.TIMEOUT ** (retry + 1))
            self._ftp_reconnect()
        return None

    def is_dir(self, remote_path, guess_by_extension=True):
        """判断远程路径是否为目录"""
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
        """列出远程目录内容"""
        return self._safe_ftp_op(lambda: self._ftp.nlst(remote_dir)) or []

    def get_dir_file_list(self, ftp_name, ftp_dir):
        """get ftp directory file list

        :param file_dir(str): ftp directory
        :return: (list) ftp file list
        """
        if not self._ftp:
            self.ftp_name = ftp_name
            self._ftpconnect()
        file_list = []
        for file in self.list_dir(ftp_dir):
            if self.is_dir(file):
                file_list += self.get_dir_file_list(file)
            else:
                file_list.append(file)
        self.close()
        return file_list

    def download_file(self, ftp_name, remote_path, local_path, bufsize=1024,
                      progress_callback: Optional[Callable[[int], None]] = None):
        """下载单个文件（支持断点续传）

        Args:
            ftp_name: 配置名称
            remote_path: 远程文件路径
            local_path: 本地保存路径
            bufsize: 缓冲区大小（字节）
            progress_callback: 进度回调（0-100）

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
            self.close()

    def upload_file(self, ftp_name, local_path, remote_path, bufsize=1024,
                    progress_callback: Optional[Callable[[int], None]] = None):
        """上传单个文件（支持断点续传）

        Args:
            ftp_name: 配置名称
            local_path: 本地文件路径
            remote_path: 远程保存路径
            bufsize: 缓冲区大小（字节）
            progress_callback: 进度回调（0-100）

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
            self.close()

    def download_file_visualization(self, ftp_name, remote_path, local_path):
        with tqdm(desc="下载文件", unit="B", unit_scale=True, unit_divisor=1024, miniters=1) as pbar:
            def update_progress(file_size, current_size):
                pbar.total = file_size
                pbar.update(current_size)

            self.download_file(ftp_name=ftp_name, remote_path=remote_path, local_path=local_path,
                               progress_callback=update_progress)

    def download_file_list(self, ftp_name, file_list, save_dir, bufsize=1024,
                           progress_callback: Optional[Callable[[int], None]] = None):
        """下载多个文件（支持断点续传）

        Args:
            ftp_name: 配置名称
            file_list: 多个远程文件路径的list
            save_dir: 本地保存目录
            bufsize: 缓冲区大小（字节）
            progress_callback: 进度回调（0-100）

        Returns:
            bool: 是否下载成功
        """
        if not self._ftp:
            self.ftp_name = ftp_name
            self._ftpconnect()

        total_files = len(file_list)
        success_count = 0
        try:
            for i, file in enumerate(set(file_list)):
                try:
                    # 分离目录和文件名
                    remote_dir, filename = os.path.split(file)
                    local_path = os.path.join(save_dir, filename)

                    # 创建本地目录
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)

                    # 获取文件大小
                    file_size = self._ftp.size(file)
                    if not file_size:
                        self.logger.error(f"无法获取远程文件大小: {filename}")
                        continue

                    # 检查断点续传（本地已下载部分）
                    downloaded = 0
                    if os.path.exists(local_path):
                        local_size = os.path.getsize(local_path)
                        if local_size == file_size:
                            self.logger.info(f"🔄 文件已存在且完整，跳过下载: {local_path}")
                            success_count += 1
                            if progress_callback:
                                progress_callback(int(100 * i / total_files))
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
                        def _update_progress(percent):
                            """适配单文件进度回调"""
                            if progress_callback:
                                # 计算全局进度 (i + percent/100)
                                overall = i + percent / 100
                                progress_callback(overall)

                        # 定义下载回调
                        callback = _ftp_block_callback(
                            file_size=file_size - downloaded,
                            percent_callback=_update_progress,
                            process_block=f.write
                        )
                        self._ftp.retrbinary(f"RETR {file}", callback, bufsize, rest=downloaded)

                    # 验证完整性
                    if os.path.getsize(local_path) != file_size:
                        os.remove(local_path)  # 删除不完整文件
                        raise RuntimeError(f"下载不完整: {downloaded}/{file_size}字节")

                    success_count += 1
                    self.logger.info(f"✅ 下载成功，文件已保存至: {local_path}")
                except Exception as e:
                    if os.path.exists(local_path):
                        os.remove(local_path)  # 清理残留文件
                    self.logger.error(f"❌ 下载失败:  {filename}: {str(e)}")
                finally:
                    # 更新进度（即使失败也计数）
                    if progress_callback:
                        progress_callback(i + 1, total_files)

            return success_count

        finally:
            # 全部完成后才关闭连接
            self.close()
