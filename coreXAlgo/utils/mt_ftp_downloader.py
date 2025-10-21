import concurrent.futures
import random
from threading import RLock
from typing import Dict
from .ftp_client import FTPClient
from .basic import set_logging


class MtFtpDownloader:
    """
    多线程并行下载FTP文件夹的所有文件

    支持多线程并发下载，自动管理FTP连接池，提供进度回调功能。
    适用于需要批量下载FTP服务器文件的场景。
    """

    def __init__(self, workers=4, verbose=False):
        """
        初始化多线程FTP下载器

        Args:
            workers (int, optional): 工作线程数量，默认为4
            verbose (bool, optional): 是否启用详细日志，默认为False

        Example:
            >>> downloader = MtFtpDownloader(workers=4, verbose=True)
        """
        self._workers = workers
        self._ftp_config = None
        self._lock = RLock()
        self.logger = set_logging("MtFtpDownloader", verbose=verbose)

    def set_ftp_config(self, ftp_configs: Dict[str, dict]):
        """
        设置FTP服务器配置

        Args:
            ftp_configs (Dict[str, dict]): FTP配置字典，格式为：
                {
                    "ftp_server1": {
                        "host": "ftp.example.com",
                        "port": 21,
                        "user": "username",
                        "password": "password",
                        "timeout": 30
                    },
                    "ftp_server2": {...}
                }

        Example:
            >>> ftp_config = {
            ...     "my_ftp": {
            ...         "host": "192.168.1.100",
            ...         "port": 21,
            ...         "user": "admin",
            ...         "password": "123456"
            ...     }
            ... }
            >>> downloader.set_ftp_config(ftp_config)
        """
        self._ftp_config = ftp_configs

    def download_files_by_pathlist(self, ftp_name, local_path_list, max_download_num=100, ftp_dir=None,
                                   img_path_list=None, shuffle=False, callback=None):
        """
        多线程下载FTP文件列表

        Args:
            ftp_name (str): FTP配置名称，必须在set_ftp_config中设置过
            local_path_list (Union[str, List[str]]): 本地保存路径，可以是：
                - str: 所有文件保存到该目录，文件名保持远程文件名
                - list: 每个文件对应的完整本地保存路径，长度必须与文件列表一致
            max_download_num (int, optional): 最大下载数量，默认为100
            ftp_dir (str, optional): 要下载的FTP目录路径，如果提供则下载该目录下所有文件
            img_path_list (List[str], optional): 预定义的文件路径列表，如果提供则直接下载这些文件
            shuffle (bool, optional): 是否随机打乱文件顺序，默认为False
            callback (Callable[[int], None], optional): 进度回调函数，接收一个整数参数（0-100）

        Returns:
            int: 成功下载的文件数量

        Raises:
            ValueError: 当FTP配置未设置或参数不合法时
            RuntimeError: 当下载过程中发生错误时

        Example:
            >>> # 下载整个目录到指定文件夹
            >>> success_count = downloader.download_files_by_pathlist(
            ...     ftp_name="my_ftp",
            ...     local_path_list="/local/download/path",
            ...     ftp_dir="/remote/files",
            ...     max_download_num=50,
            ...     shuffle=True,
            ...     callback=lambda p: print(f"进度: {p}%")
            ... )
            >>>
            >>> # 下载指定文件列表到不同路径
            >>> file_list = ["/remote/file1.txt", "/remote/file2.jpg"]
            >>> local_paths = ["/local/file1.txt", "/local/file2.jpg"]
            >>> success_count = downloader.download_files_by_pathlist(
            ...     ftp_name="my_ftp",
            ...     local_path_list=local_paths,
            ...     img_path_list=file_list,
            ...     max_download_num=10
            ... )

        Notes:
            - ftp_dir 和 img_path_list 参数二选一，不能同时使用
            - 如果同时提供 ftp_dir 和 img_path_list，优先使用 img_path_list
            - 使用多线程时，每个线程会创建独立的FTP连接
        """
        if self._ftp_config is None:
            raise ValueError("请先使用set_ftp_config方法设置FTP配置")

        if ftp_name not in self._ftp_config:
            raise ValueError(f"FTP配置 '{ftp_name}' 不存在，可用配置: {list(self._ftp_config.keys())}")

        # 获取文件列表
        with FTPClient(self._ftp_config) as ftp:
            if img_path_list is not None:
                file_list = img_path_list
            elif ftp_dir is not None:
                file_list = ftp.get_dir_file_list(ftp_name, ftp_dir)
            else:
                raise ValueError("必须提供ftp_dir或img_path_list参数")

        if not file_list:
            self.logger.warning("无文件可下载")
            return 0

        if shuffle:
            random.seed(42)
            random.shuffle(file_list)

        # 限制下载数量
        file_list = file_list[:max_download_num]
        total_files = len(file_list)

        # 将文件列表分配给各个工作线程
        worker_file_list = [file_list[i::self._workers] for i in range(self._workers)]
        worker_percent = [0 for _ in range(self._workers)]

        def _atomic_callback(worker_index, percent):
            """原子化的进度回调，确保线程安全"""
            with self._lock:
                worker_percent[worker_index] = percent
                if callback:
                    overall_progress = sum(worker_percent) / self._workers
                    callback(int(overall_progress))

        # 创建线程池执行下载任务
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._workers) as executor:
            futures = []
            ftp_clients = []

            try:
                # 为每个工作线程创建独立的FTP连接
                for worker_id in range(self._workers):
                    ftp_client = FTPClient(self._ftp_config)
                    ftp_client._ftpconnect(ftp_name)
                    ftp_clients.append(ftp_client)

                    # 提交下载任务到线程池
                    future = executor.submit(
                        ftp_client.download_file_list,
                        ftp_name=ftp_name,
                        remote_path_list=worker_file_list[worker_id],
                        local_path_list=local_path_list,
                        bufsize=1024,
                        progress_callback=lambda p, t, n: _atomic_callback(worker_id, p / t * 100)
                    )
                    futures.append(future)

                # 等待所有任务完成并统计成功数量
                success_count = sum(f.result() for f in futures)

                self.logger.info(f"下载完成: {success_count}/{total_files} 个文件")

            except Exception as e:
                self.logger.error(f"下载过程中发生错误: {str(e)}")
                raise RuntimeError(f"文件下载失败: {str(e)}")
            finally:
                # 确保所有FTP连接正确关闭
                for client in ftp_clients:
                    try:
                        client._close()
                    except Exception as e:
                        self.logger.warning(f"关闭FTP连接时出错: {str(e)}")

        return success_count
