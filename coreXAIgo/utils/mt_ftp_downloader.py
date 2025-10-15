import concurrent.futures
import random
from threading import RLock
from typing import Dict
from ..utils import FTPClient, set_logging

__all__ = ['MtFtpDownloader']


class MtFtpDownloader:
    """多线程并行下载ftp文件夹的所有文件"""

    def __init__(self, workers=4, verbose=False):
        self._workers = workers
        self._ftp_config = None
        self._lock = RLock()
        self.logger = set_logging("MtFtpDownloader", verbose=verbose)

    def set_ftp_config(self, ftp_configs: Dict[str, dict]):
        self._ftp_config = ftp_configs

    def download_files_by_pathlist(self, ftp_name, local_path_list, max_download_num=100, ftp_dir=None,
                                   img_path_list=None, shuffle=False, callback=None):
        """多线程下载FTP文件列表

        Args:
            ftp_name: FTP配置名称
            local_path_list: 本地保存路径，可以是:
                - str: 所有文件保存到该目录
                - list: 每个文件对应的本地保存路径
            max_download_num: 最大下载数量
            ftp_dir: 要下载的FTP目录
            img_path_list: 预定义的文件路径列表
            shuffle: 是否随机打乱文件顺序
            callback: 进度回调函数

        Returns:
            int: 成功下载的文件数量
        """
        with FTPClient(self._ftp_config) as ftp:
            # 获取文件列表
            file_list = img_path_list if ftp_dir is None else ftp.get_dir_file_list(ftp_name, ftp_dir)

        if not file_list:
            self.logger.warning("无文件可下载")
            return 0

        if shuffle:
            random.seed(42)
            random.shuffle(file_list)

        # 获取要下载的最大数量的图片
        file_list = file_list[:max_download_num]
        total_files = len(file_list)

        # 分配任务给工作线程
        worker_file_list = [file_list[i::self._workers] for i in range(self._workers)]
        worker_percent = [0 for i in range(self._workers)]

        def _atomic_callback(worker_index, percent):
            with self._lock:
                worker_percent[worker_index] = percent
                if callback:
                    overall_progress = sum(worker_percent) / self._workers
                    callback(int(overall_progress))

        # 创建线程池
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._workers) as executor:
            futures = []
            ftp_clients = []

            try:
                # 为每个工作线程创建独立的FTP连接
                for worker_id in range(self._workers):
                    ftp_client = FTPClient(self._ftp_config)
                    ftp_client._ftpconnect(ftp_name)
                    ftp_clients.append(ftp_client)

                    # 提交下载任务
                    future = executor.submit(
                        ftp_client.download_file_list,
                        ftp_name=ftp_name,
                        remote_path_list=worker_file_list[worker_id],
                        local_path_list=local_path_list,
                        bufsize=1024,
                        progress_callback=lambda p, t, n: _atomic_callback(worker_id, p / t * 100)
                    )
                    futures.append(future)

                # 等待所有任务完成
                success_count = sum(f.result() for f in futures)

            except Exception as e:
                self.logger.error(f"下载过程中发生错误: {str(e)}")
                raise
            finally:
                # 确保所有FTP连接关闭
                for client in ftp_clients:
                    try:
                        client.close()
                    except Exception as e:
                        self.logger.warning(f"关闭FTP连接时出错: {str(e)}")

        return success_count
