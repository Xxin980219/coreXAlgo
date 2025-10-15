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

    def download_files_by_pathlist(self, ftp_name, save_dir, max_download_num=100, ftp_dir=None, img_path_list=None,
                                   shuffle=False, callback=None):
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

        worker_file_list = [file_list[i::self._workers] for i in range(self._workers)]
        worker_percent = [0 for i in range(self._workers)]

        def _atomic_callback(worker_index, percent):
            with self._lock:
                worker_percent[worker_index] = percent
                return callback(int(sum(worker_percent) / self._workers))

        # 每个线程使用独立FTP连接
        ftp_client_list = []
        for i in range(self._workers):
            ftp_client = FTPClient(self._ftp_config)
            ftp_client._ftpconnect(ftp_name)
            ftp_client_list.append(ftp_client)

        # 使用线程池下载
        result = [None for i in range(self._workers)]
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=self._workers) as executor:

            for worker_id in range(self._workers):
                # 提交任务
                cb = lambda p, wi=i: _atomic_callback(wi, p) if callback else None
                result[worker_id] = executor.submit(
                    ftp_client_list[worker_id].download_file_list,
                    ftp_name,
                    worker_file_list[worker_id],
                    save_dir,
                    1024,
                    cb
                )
        for ftp_client in ftp_client_list:
            ftp_client.close()

        # 等待任务完成并清理连接
        success_count = 0
        for future in result:
            try:
                success_count += future.result()
            except Exception as e:
                self.logger.error(f"线程下载异常: {str(e)}")
        return success_count
