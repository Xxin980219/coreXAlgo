import concurrent.futures
import os
import random
import time
from threading import RLock
from typing import Dict, Union, List, Optional, Callable
from .ftp_client import FTPClient
from .sftp_client import SFTPClient
from .basic import set_logging


class MtFileDownloader:
    """
    多线程并行下载FTP/SFTP文件夹的所有文件

    支持多线程并发下载，自动管理连接池，提供进度回调功能。
    适用于需要批量下载FTP或SFTP服务器文件的场景。
    """

    def __init__(self, configs: Dict[str, dict], workers=1, verbose=False):
        """
        初始化多线程FTP/SFTP下载器

        Args:
            configs (Dict[str, dict]): FTP或SFTP配置字典，格式为：
                # FTP配置示例
                {
                    "ftp_server1": {
                        "host": "ftp.example.com",
                        "port": 21,
                        "username": "username",
                        "password": "password",
                        "timeout": 30,
                        "type": "ftp"  # 可选，默认为ftp
                    },
                    # SFTP配置示例
                    "sftp_server1": {
                        "host": "sftp.example.com",
                        "port": 22,
                        "username": "username",
                        "password": "password",
                        "timeout": 30,
                        "type": "sftp"  # 必须指定为sftp
                    }
                }
            workers (int, optional): 工作线程数量，默认为4
            verbose (bool, optional): 是否启用详细日志，默认为False

        Example:
            >>> # FTP配置
            >>> ftp_config = {
            ...     "my_ftp": {
            ...         "host": "192.168.1.100",
            ...         "port": 21,
            ...         "username": "admin",
            ...         "password": "123456",
            ...         "type": "ftp"
            ...     }
            ... }
            >>> 
            >>> # SFTP配置
            >>> sftp_config = {
            ...     "my_sftp": {
            ...         "host": "192.168.1.100",
            ...         "port": 22,
            ...         "username": "admin",
            ...         "password": "123456",
            ...         "type": "sftp"
            ...     }
            ... }
            >>> 
            >>> downloader = MtFileDownloader({**ftp_config, **sftp_config}, workers=4, verbose=True)
        """
        self._workers = workers
        self._configs = configs
        self._lock = RLock()
        self.logger = set_logging("MtFtpDownloader", verbose=verbose)

    def check_files_existence(self, server_name, local_path_list, max_download_num=None, remote_dir=None, file_path_list=None, shuffle=False, callback=None, max_workers=None):
        """
        检查要下载的文件是否存在，并过滤出存在的文件及其对应的本地路径

        Args:
            server_name (str): 服务器配置名称，必须在初始化时提供的configs中
            local_path_list (Union[str, List[str]]): 本地保存路径，可以是：
                - str: 所有文件保存到该目录，文件名保持远程文件名
                - list: 每个文件对应的完整本地保存路径，长度必须与文件列表一致
            max_download_num (int, optional): 最大检查数量，默认为None（检查所有文件）
            remote_dir (str, optional): 要检查的远程目录路径，如果提供则检查该目录下所有文件
            file_path_list (List[str], optional): 预定义的文件路径列表，如果提供则直接检查这些文件
            shuffle (bool, optional): 是否随机打乱文件顺序，默认为False
            callback (Callable, optional): 进度回调函数，接收一个整数参数（0-100）表示检查进度
            max_workers (int, optional): 最大工作线程数，默认使用初始化时的workers数量

        Returns:
            Tuple[List[str], Union[str, List[str]]]: 过滤后的文件列表和对应的本地路径列表
                - 当local_path_list为str时，返回的第二个元素仍为str
                - 当local_path_list为list时，返回的第二个元素为过滤后的本地路径列表

        Raises:
            ValueError: 当服务器配置不存在或参数不合法时

        Example:
            >>> # 检查FTP服务器上的文件是否存在（检查所有文件）
            >>> downloader = MtFileDownloader(configs, workers=4)
            >>> file_list = ["/remote/file1.txt", "/remote/file2.jpg", "/remote/nonexistent.txt"]
            >>> local_paths = ["/local/file1.txt", "/local/file2.jpg", "/local/nonexistent.txt"]
            >>> filtered_files, filtered_local_paths = downloader.check_files_existence(
            ...     server_name="my_ftp",
            ...     local_path_list=local_paths,
            ...     file_path_list=file_list,
            ...     max_workers=4  # 使用4个线程并行检查
            ... )
            >>> # filtered_files 将只包含存在的文件
            >>> # filtered_local_paths 将只包含对应存在文件的本地路径
            >>>
            >>> # 限制检查数量（只检查前100个文件）
            >>> filtered_files, filtered_local_paths = downloader.check_files_existence(
            ...     server_name="my_ftp",
            ...     local_path_list=local_paths,
            ...     file_path_list=file_list,
            ...     max_download_num=100,
            ...     max_workers=4
            ... )
        """
        if server_name not in self._configs:
            raise ValueError(f"服务器配置 '{server_name}' 不存在，可用配置: {list(self._configs.keys())}")

        # 获取服务器类型
        server_config = self._configs[server_name]
        server_type = server_config.get('type', 'ftp').lower()

        # 确定使用的线程数
        if max_workers is None:
            max_workers = self._workers

        # 过滤出存在的文件及其对应的本地路径
        existing_files = []
        existing_local_paths = []
        client = None

        try:
            # 提前创建客户端连接并确保连接成功
            self.logger.info(f"正在连接到服务器: {server_name}")
            if server_type == 'sftp':
                client = SFTPClient(self._configs)
                # SFTP客户端不需要显式连接，_get_connection会自动处理
                # 尝试获取连接以确保连接成功
                conn = client._get_connection(server_name)
                self.logger.info(f"✅ 成功连接到SFTP服务器: {server_name}")
            else:
                client = FTPClient(self._configs)
                # 显式连接到FTP服务器
                client._ftpconnect(server_name)
                self.logger.info(f"✅ 成功连接到FTP服务器: {server_name}")

            # 获取文件列表
            if file_path_list is not None:
                file_list = file_path_list
            elif remote_dir is not None:
                if server_type == 'sftp':
                    file_list = client.get_dir_file_list(server_name, remote_dir)
                else:
                    file_list = client.get_dir_file_list(server_name, remote_dir)
            else:
                raise ValueError("必须提供remote_dir或file_path_list参数")

            if not file_list:
                self.logger.warning("无文件可检查")
                return [], local_path_list if isinstance(local_path_list, list) else local_path_list

            if shuffle:
                random.seed(42)
                random.shuffle(file_list)

            # 限制检查数量
            if max_download_num is not None:
                file_list = file_list[:max_download_num]
            total_files = len(file_list)

            # 如果local_path_list不是列表，直接返回原文件列表和local_path_list
            if not isinstance(local_path_list, list):
                return file_list, local_path_list

            # 检查local_path_list长度是否与文件列表一致
            if len(local_path_list) < len(file_list):
                raise ValueError("local_path_list长度必须大于或等于文件列表长度")

            # 如果只有一个worker或者文件数量很少，使用单线程
            if max_workers <= 1 or total_files <= 10:
                self.logger.info(f"使用单线程检查 {total_files} 个文件")
                return self._check_files_single_thread(client, server_name, server_type, file_list, local_path_list, callback)

            # 使用多线程并行检查
            self.logger.info(f"使用 {max_workers} 个线程并行检查 {total_files} 个文件")
            return self._check_files_multi_thread(client, server_name, server_type, file_list, local_path_list, max_workers, callback)

        finally:
            # 确保关闭连接
            if client:
                try:
                    if hasattr(client, 'close'):
                        client.close()
                    elif hasattr(client, '_close'):
                        client._close()
                except Exception as e:
                    self.logger.warning(f"关闭连接时出错: {str(e)}")

    def _check_files_single_thread(self, client, server_name, server_type, file_list, local_path_list, callback):
        """
        单线程检查文件存在性

        Args:
            client: FTP/SFTP客户端实例
            server_name: 服务器名称
            server_type: 服务器类型（ftp/sftp）
            file_list: 文件路径列表
            local_path_list: 本地路径列表
            callback: 进度回调函数

        Returns:
            Tuple[List[str], List[str]]: 存在的文件列表和对应的本地路径列表
        """
        existing_files = []
        existing_local_paths = []
        total_files = len(file_list)
        
        conn = None
        if server_type == 'sftp':
            conn = client._get_connection(server_name)
        else:
            if hasattr(client, '_ftp') and client._ftp:
                conn = client._ftp
            else:
                conn = client._get_connection(server_name)
        
        # 添加连接保活机制
        noop_count = 0
        noop_interval = 5
        reconnect_count = 0
        max_reconnects = 10
        batch_size = 200
        
        for i, file_path in enumerate(file_list):
            # 定期重新连接，避免长时间使用同一连接
            if i > 0 and i % batch_size == 0:
                self.logger.info(f"定期重新连接 (已检查{i}个文件)")
                try:
                    client._close_connection(server_name)
                    conn = client._get_connection(server_name)
                    self.logger.info(f"定期重新连接成功")
                except Exception as reconnect_error:
                    self.logger.warning(f"定期重新连接失败: {str(reconnect_error)}")
                    try:
                        conn = client._get_connection(server_name)
                    except Exception as e:
                        self.logger.error(f"获取新连接失败: {str(e)}")
                        continue
            
            try:
                if server_type == 'sftp':
                    conn.stat(file_path)
                    existing_files.append(file_path)
                    existing_local_paths.append(local_path_list[i])
                    self.logger.debug(f"文件存在: {file_path}")
                else:
                    if conn:
                        try:
                            file_size = conn.size(file_path)
                            existing_files.append(file_path)
                            existing_local_paths.append(local_path_list[i])
                            self.logger.debug(f"文件存在: {file_path}, 大小: {file_size} 字节")
                        except Exception as ftp_error:
                            try:
                                file_dir = os.path.dirname(file_path)
                                file_name = os.path.basename(file_path)
                                dir_list = conn.nlst(file_dir)
                                if file_name in dir_list:
                                    existing_files.append(file_path)
                                    existing_local_paths.append(local_path_list[i])
                                    self.logger.debug(f"文件存在: {file_path} (通过LIST检查)")
                                else:
                                    self.logger.warning(f"文件不存在: {file_path} (LIST检查失败)")
                            except Exception as list_error:
                                if reconnect_count < max_reconnects:
                                    self.logger.warning(f"LIST命令失败，尝试重新连接: {file_path}, 错误: {str(list_error)}")
                                    try:
                                        client._close_connection(server_name)
                                        conn = client._get_connection(server_name)
                                        reconnect_count += 1
                                        self.logger.info(f"重新连接成功 (第{reconnect_count}次)")
                                        file_size = conn.size(file_path)
                                        existing_files.append(file_path)
                                        existing_local_paths.append(local_path_list[i])
                                        self.logger.debug(f"文件存在: {file_path}, 大小: {file_size} 字节")
                                    except Exception as reconnect_error:
                                        self.logger.warning(f"重新连接后检查失败: {file_path}, 错误: {str(reconnect_error)}")
                                else:
                                    self.logger.warning(f"文件不存在: {file_path}, 错误: {str(ftp_error)}, LIST错误: {str(list_error)}")
                    else:
                        self.logger.error(f"无法获取FTP连接，无法检查文件: {file_path}")
            except Exception as e:
                self.logger.warning(f"文件检查失败: {file_path}, 错误: {str(e)}")
                continue
            finally:
                if server_type == 'ftp' and conn:
                    noop_count += 1
                    if noop_count >= noop_interval:
                        try:
                            conn.voidcmd('NOOP')
                            self.logger.debug(f"发送NOOP命令保持连接 (已检查{i+1}个文件)")
                            noop_count = 0
                        except Exception as e:
                            self.logger.warning(f"发送NOOP命令失败: {str(e)}")
                            if reconnect_count < max_reconnects:
                                try:
                                    client._close_connection(server_name)
                                    conn = client._get_connection(server_name)
                                    reconnect_count += 1
                                    self.logger.info(f"NOOP失败后重新连接成功 (第{reconnect_count}次)")
                                except Exception as reconnect_error:
                                    self.logger.error(f"重新连接失败: {str(reconnect_error)}")
                    
                    if callback:
                        progress = int((i + 1) / total_files * 100)
                        callback(progress)

        self.logger.info(f"文件检查完成: 存在 {len(existing_files)} 个文件，不存在 {len(file_list) - len(existing_files)} 个文件")
        return existing_files, existing_local_paths

    def _check_files_multi_thread(self, client, server_name, server_type, file_list, local_path_list, max_workers, callback):
        """
        多线程并行检查文件存在性

        Args:
            client: FTP/SFTP客户端实例
            server_name: 服务器名称
            server_type: 服务器类型（ftp/sftp）
            file_list: 文件路径列表
            local_path_list: 本地路径列表
            max_workers: 最大工作线程数
            callback: 进度回调函数

        Returns:
            Tuple[List[str], List[str]]: 存在的文件列表和对应的本地路径列表
        """
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed

        total_files = len(file_list)
        existing_files = []
        existing_local_paths = []
        lock = threading.Lock()
        progress_lock = threading.Lock()
        checked_count = [0]

        # 将文件列表分配给各个工作线程
        worker_file_list = [file_list[i::max_workers] for i in range(max_workers)]
        worker_local_path_list = []
        for worker_id in range(max_workers):
            worker_indices = [i for i in range(len(file_list)) if i % max_workers == worker_id]
            worker_local_paths = [local_path_list[i] for i in worker_indices]
            worker_local_path_list.append(worker_local_paths)

        def check_worker(worker_id, worker_files, worker_local_paths):
            """
            工作线程函数，检查分配给该线程的文件

            Args:
                worker_id: 工作线程ID
                worker_files: 该线程需要检查的文件列表
                worker_local_paths: 对应的本地路径列表

            Returns:
                Tuple[List[str], List[str]]: 该线程发现的存在的文件列表和对应的本地路径列表
            """
            worker_existing_files = []
            worker_existing_local_paths = []
            worker_client = None
            worker_conn = None
            
            try:
                # 创建独立的客户端连接
                if server_type == 'sftp':
                    worker_client = SFTPClient(self._configs)
                    worker_conn = worker_client._get_connection(server_name)
                else:
                    worker_client = FTPClient(self._configs)
                    worker_client._ftpconnect(server_name)
                    if hasattr(worker_client, '_ftp') and worker_client._ftp:
                        worker_conn = worker_client._ftp
                    else:
                        worker_conn = worker_client._get_connection(server_name)
                
                self.logger.debug(f"Worker {worker_id}: 已建立连接")
                
                # 连接预热：发送几个NOOP命令确保连接稳定
                self.logger.info(f"Worker {worker_id}: 开始连接预热...")
                for warmup_attempt in range(3):
                    try:
                        if server_type == 'sftp':
                            # SFTP预热：执行一些轻量级操作
                            worker_conn.listdir('.')[:1]  # 只获取一个文件进行测试
                        else:
                            # FTP预热：发送NOOP命令
                            worker_conn.voidcmd('NOOP')
                        time.sleep(0.1)  # 短暂延迟
                        self.logger.debug(f"Worker {worker_id}: 预热步骤 {warmup_attempt + 1}/3 完成")
                    except Exception as warmup_error:
                        self.logger.warning(f"Worker {worker_id}: 预热步骤 {warmup_attempt + 1} 失败: {str(warmup_error)}")
                        # 预热失败，重新连接
                        try:
                            worker_client._close_connection(server_name)
                            if server_type == 'sftp':
                                worker_conn = worker_client._get_connection(server_name)
                            else:
                                worker_client._ftpconnect(server_name)
                                if hasattr(worker_client, '_ftp') and worker_client._ftp:
                                    worker_conn = worker_client._ftp
                                else:
                                    worker_conn = worker_client._get_connection(server_name)
                        except Exception as reconn_error:
                            self.logger.error(f"Worker {worker_id}: 预热后重新连接失败: {str(reconn_error)}")
                self.logger.info(f"Worker {worker_id}: 连接预热完成")
                
                # 添加连接保活机制
                noop_count = 0
                noop_interval = 5  # 更频繁的NOOP，保持连接活跃
                reconnect_count = 0
                max_reconnects = 30  # 进一步增加最大重连次数
                batch_size = 100  # 减少批次大小，更频繁重新连接
                time_based_reconnect = 180  # 减少时间间隔，每180秒强制重新连接
                retry_delay = 0.5  # 减少基础重试延迟
                consecutive_errors = 0  # 连续错误计数
                max_consecutive_errors = 1  # 进一步降低连续错误阈值，更激进地重新连接
                start_time = time.time()  # 记录开始时间
                request_interval = 0.1  # 增加请求间隔，避免服务器限流
                last_operation_time = start_time  # 上次操作时间
                
                for idx, file_path in enumerate(worker_files):
                    # 基于时间的重新连接，避免连接老化
                    current_time = time.time()
                    if current_time - start_time > time_based_reconnect:
                        self.logger.info(f"Worker {worker_id}: 基于时间的重新连接 (运行时间: {current_time - start_time:.1f}秒)")
                        try:
                            worker_client._close_connection(server_name)
                            if server_type == 'sftp':
                                worker_conn = worker_client._get_connection(server_name)
                            else:
                                worker_client._ftpconnect(server_name)
                                if hasattr(worker_client, '_ftp') and worker_client._ftp:
                                    worker_conn = worker_client._ftp
                                else:
                                    worker_conn = worker_client._get_connection(server_name)
                            self.logger.info(f"Worker {worker_id}: 基于时间的重新连接成功")
                            start_time = current_time  # 重置开始时间
                            consecutive_errors = 0
                        except Exception as reconnect_error:
                            self.logger.warning(f"Worker {worker_id}: 基于时间的重新连接失败: {str(reconnect_error)}")
                            try:
                                if server_type == 'sftp':
                                    worker_conn = worker_client._get_connection(server_name)
                                else:
                                    worker_client._ftpconnect(server_name)
                                    if hasattr(worker_client, '_ftp') and worker_client._ftp:
                                        worker_conn = worker_client._ftp
                                    else:
                                        worker_conn = worker_client._get_connection(server_name)
                                start_time = current_time
                            except Exception as e:
                                self.logger.error(f"Worker {worker_id}: 获取新连接失败: {str(e)}")
                                consecutive_errors += 1
                                continue

                    # 定期重新连接
                    if idx > 0 and idx % batch_size == 0:
                        self.logger.info(f"Worker {worker_id}: 定期重新连接 (已检查{idx}个文件)")
                        try:
                            worker_client._close_connection(server_name)
                            if server_type == 'sftp':
                                worker_conn = worker_client._get_connection(server_name)
                            else:
                                worker_client._ftpconnect(server_name)
                                if hasattr(worker_client, '_ftp') and worker_client._ftp:
                                    worker_conn = worker_client._ftp
                                else:
                                    worker_conn = worker_client._get_connection(server_name)
                            self.logger.info(f"Worker {worker_id}: 定期重新连接成功")
                            consecutive_errors = 0
                        except Exception as reconnect_error:
                            self.logger.warning(f"Worker {worker_id}: 定期重新连接失败: {str(reconnect_error)}")
                            try:
                                if server_type == 'sftp':
                                    worker_conn = worker_client._get_connection(server_name)
                                else:
                                    worker_client._ftpconnect(server_name)
                                    if hasattr(worker_client, '_ftp') and worker_client._ftp:
                                        worker_conn = worker_client._ftp
                                    else:
                                        worker_conn = worker_client._get_connection(server_name)
                            except Exception as e:
                                self.logger.error(f"Worker {worker_id}: 获取新连接失败: {str(e)}")
                                consecutive_errors += 1
                                continue

                    # 智能请求间隔，避免服务器限流
                    time_since_last_operation = current_time - last_operation_time
                    if time_since_last_operation < request_interval:
                        wait_time = request_interval - time_since_last_operation
                        time.sleep(wait_time)
                    last_operation_time = time.time()
                    
                    try:
                        if server_type == 'sftp':
                            worker_conn.stat(file_path)
                            worker_existing_files.append(file_path)
                            worker_existing_local_paths.append(worker_local_paths[idx])
                            self.logger.debug(f"Worker {worker_id}: 文件存在: {file_path}")
                            consecutive_errors = 0  # 重置连续错误计数
                        else:
                            if worker_conn:
                                # 检查连续错误，超过阈值强制重新连接
                                if consecutive_errors >= max_consecutive_errors:
                                    self.logger.warning(f"Worker {worker_id}: 连续错误超过阈值，强制重新连接")
                                    try:
                                        worker_client._close_connection(server_name)
                                        worker_client._ftpconnect(server_name)
                                        if hasattr(worker_client, '_ftp') and worker_client._ftp:
                                            worker_conn = worker_client._ftp
                                        else:
                                            worker_conn = worker_client._get_connection(server_name)
                                        self.logger.info(f"Worker {worker_id}: 强制重新连接成功")
                                        consecutive_errors = 0
                                    except Exception as reconnect_error:
                                        self.logger.error(f"Worker {worker_id}: 强制重新连接失败: {str(reconnect_error)}")
                                        consecutive_errors += 1
                                        continue

                                # 尝试使用size命令检查文件
                                retry_count = 5  # 进一步增加重试次数
                                file_exists = False
                                
                                for attempt in range(retry_count):
                                    try:
                                        # 连接健康检查
                                        try:
                                            worker_conn.voidcmd('NOOP')
                                            self.logger.debug(f"Worker {worker_id}: 连接健康检查通过")
                                        except Exception as health_error:
                                            self.logger.warning(f"Worker {worker_id}: 连接健康检查失败: {str(health_error)}")
                                            # 连接不健康，立即重新连接
                                            try:
                                                worker_client._close_connection(server_name)
                                                worker_client._ftpconnect(server_name)
                                                if hasattr(worker_client, '_ftp') and worker_client._ftp:
                                                    worker_conn = worker_client._ftp
                                                else:
                                                    worker_conn = worker_client._get_connection(server_name)
                                                self.logger.info(f"Worker {worker_id}: 健康检查失败后重新连接成功")
                                                consecutive_errors = 0
                                            except Exception as reconn_error:
                                                self.logger.error(f"Worker {worker_id}: 健康检查失败后重新连接失败: {str(reconn_error)}")
                                                continue

                                        # 尝试获取文件大小
                                        file_size = worker_conn.size(file_path)
                                        worker_existing_files.append(file_path)
                                        worker_existing_local_paths.append(worker_local_paths[idx])
                                        self.logger.debug(f"Worker {worker_id}: 文件存在: {file_path}, 大小: {file_size} 字节")
                                        consecutive_errors = 0
                                        file_exists = True
                                        break
                                    except Exception as ftp_error:
                                        # 处理425和550错误
                                        error_str = str(ftp_error)
                                        if '425' in error_str or '550' in error_str:
                                            self.logger.warning(f"Worker {worker_id}: 服务器错误 (尝试 {attempt+1}/{retry_count}): {error_str}")
                                            # 立即重新连接
                                            try:
                                                worker_client._close_connection(server_name)
                                                worker_client._ftpconnect(server_name)
                                                if hasattr(worker_client, '_ftp') and worker_client._ftp:
                                                    worker_conn = worker_client._ftp
                                                else:
                                                    worker_conn = worker_client._get_connection(server_name)
                                                self.logger.info(f"Worker {worker_id}: 错误后立即重新连接成功")
                                                consecutive_errors = 0
                                            except Exception as reconn_error:
                                                self.logger.error(f"Worker {worker_id}: 错误后重新连接失败: {str(reconn_error)}")
                                                consecutive_errors += 1
                                                # 如果不是最后一次尝试，继续重试
                                                if attempt < retry_count - 1:
                                                    delay = retry_delay * (attempt + 1)  # 线性增加延迟
                                                    self.logger.info(f"Worker {worker_id}: 等待 {delay:.1f} 秒后重试...")
                                                    time.sleep(delay)
                                        else:
                                            # 其他错误，尝试LIST检查
                                            self.logger.debug(f"Worker {worker_id}: 其他错误: {str(ftp_error)}")
                                            break

                                if not file_exists:
                                    # 尝试使用LIST命令检查
                                    list_retry_count = 4  # 增加LIST重试次数
                                    list_success = False
                                    
                                    for list_attempt in range(list_retry_count):
                                        try:
                                            # 连接健康检查
                                            try:
                                                worker_conn.voidcmd('NOOP')
                                                self.logger.debug(f"Worker {worker_id}: LIST前连接健康检查通过")
                                            except Exception as health_error:
                                                self.logger.warning(f"Worker {worker_id}: LIST前连接健康检查失败: {str(health_error)}")
                                                # 连接不健康，立即重新连接
                                                try:
                                                    worker_client._close_connection(server_name)
                                                    worker_client._ftpconnect(server_name)
                                                    if hasattr(worker_client, '_ftp') and worker_client._ftp:
                                                        worker_conn = worker_client._ftp
                                                    else:
                                                        worker_conn = worker_client._get_connection(server_name)
                                                    self.logger.info(f"Worker {worker_id}: LIST前重新连接成功")
                                                    consecutive_errors = 0
                                                except Exception as reconn_error:
                                                    self.logger.error(f"Worker {worker_id}: LIST前重新连接失败: {str(reconn_error)}")
                                                    continue

                                            file_dir = os.path.dirname(file_path)
                                            file_name = os.path.basename(file_path)
                                            
                                            # 增加延迟避免服务器拒绝
                                            time.sleep(0.2)  # 进一步增加延迟
                                            
                                            dir_list = worker_conn.nlst(file_dir)
                                            if file_name in dir_list:
                                                worker_existing_files.append(file_path)
                                                worker_existing_local_paths.append(worker_local_paths[idx])
                                                self.logger.debug(f"Worker {worker_id}: 文件存在: {file_path} (通过LIST检查)")
                                                consecutive_errors = 0
                                                list_success = True
                                                break
                                            else:
                                                self.logger.debug(f"Worker {worker_id}: 文件不存在: {file_path} (LIST检查失败)")
                                                consecutive_errors += 1
                                                break
                                        except Exception as list_error:
                                            error_str = str(list_error)
                                            self.logger.warning(f"Worker {worker_id}: LIST命令失败 (尝试 {list_attempt+1}/{list_retry_count}): {error_str}")
                                            consecutive_errors += 1
                                            
                                            # 处理425和550错误，立即重新连接
                                            if '425' in error_str or '550' in error_str:
                                                # 立即重新连接
                                                try:
                                                    worker_client._close_connection(server_name)
                                                    worker_client._ftpconnect(server_name)
                                                    if hasattr(worker_client, '_ftp') and worker_client._ftp:
                                                        worker_conn = worker_client._ftp
                                                    else:
                                                        worker_conn = worker_client._get_connection(server_name)
                                                    reconnect_count += 1
                                                    self.logger.info(f"Worker {worker_id}: LIST失败后立即重新连接成功 (第{reconnect_count}次)")
                                                    consecutive_errors = 0
                                                except Exception as reconnect_error:
                                                    self.logger.error(f"Worker {worker_id}: LIST失败后重新连接失败: {str(reconnect_error)}")
                                                    # 如果不是最后一次尝试，等待后重试
                                                    if list_attempt < list_retry_count - 1:
                                                        delay = retry_delay * (list_attempt + 1) * 2
                                                        self.logger.info(f"Worker {worker_id}: 等待 {delay:.1f} 秒后重试LIST...")
                                                        time.sleep(delay)
                                            else:
                                                # 其他错误，不再重试
                                                break

                                    # 如果LIST也失败，尝试最终的重新连接
                                    if not list_success and reconnect_count < max_reconnects:
                                        self.logger.info(f"Worker {worker_id}: 所有检查都失败，尝试最终重新连接")
                                        try:
                                            worker_client._close_connection(server_name)
                                            worker_client._ftpconnect(server_name)
                                            if hasattr(worker_client, '_ftp') and worker_client._ftp:
                                                worker_conn = worker_client._ftp
                                            else:
                                                worker_conn = worker_client._get_connection(server_name)
                                            reconnect_count += 1
                                            self.logger.info(f"Worker {worker_id}: 最终重新连接成功")
                                            consecutive_errors = 0
                                        except Exception as final_reconnect_error:
                                            self.logger.error(f"Worker {worker_id}: 最终重新连接失败: {str(final_reconnect_error)}")
                            else:
                                self.logger.error(f"Worker {worker_id}: 无法获取FTP连接，无法检查文件: {file_path}")
                                consecutive_errors += 1
                    except Exception as e:
                        self.logger.debug(f"Worker {worker_id}: 文件检查失败: {file_path}, 错误: {str(e)}")
                        consecutive_errors += 1
                        continue
                    finally:
                        # 连接保活
                        if server_type == 'ftp' and worker_conn:
                            noop_count += 1
                            if noop_count >= noop_interval:
                                try:
                                    worker_conn.voidcmd('NOOP')
                                    self.logger.debug(f"Worker {worker_id}: 发送NOOP命令保持连接 (已检查{idx+1}个文件)")
                                    noop_count = 0
                                    consecutive_errors = 0  # 重置连续错误计数
                                except Exception as e:
                                    self.logger.warning(f"Worker {worker_id}: 发送NOOP命令失败: {str(e)}")
                                    consecutive_errors += 1
                                    if reconnect_count < max_reconnects:
                                        try:
                                            # 增加延迟避免服务器拒绝
                                            time.sleep(retry_delay)
                                            
                                            worker_client._close_connection(server_name)
                                            worker_client._ftpconnect(server_name)
                                            if hasattr(worker_client, '_ftp') and worker_client._ftp:
                                                worker_conn = worker_client._ftp
                                            else:
                                                worker_conn = worker_client._get_connection(server_name)
                                            reconnect_count += 1
                                            self.logger.info(f"Worker {worker_id}: NOOP失败后重新连接成功 (第{reconnect_count}次)")
                                            consecutive_errors = 0
                                        except Exception as reconnect_error:
                                            self.logger.error(f"Worker {worker_id}: 重新连接失败: {str(reconnect_error)}")
                                            consecutive_errors += 1
                        
                        # 更新进度
                        with progress_lock:
                            checked_count[0] += 1
                            if callback:
                                progress = int(checked_count[0] / total_files * 100)
                                callback(progress)

            except Exception as e:
                self.logger.error(f"Worker {worker_id}: 发生异常: {str(e)}")
            finally:
                # 关闭连接
                if worker_client:
                    try:
                        if hasattr(worker_client, 'close'):
                            worker_client.close()
                        elif hasattr(worker_client, '_close'):
                            worker_client._close()
                    except Exception as e:
                        self.logger.warning(f"Worker {worker_id}: 关闭连接时出错: {str(e)}")
            
            return worker_existing_files, worker_existing_local_paths

        # 使用线程池并行执行检查任务
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for worker_id in range(max_workers):
                future = executor.submit(
                    check_worker,
                    worker_id,
                    worker_file_list[worker_id],
                    worker_local_path_list[worker_id]
                )
                futures.append(future)
            
            # 等待所有任务完成并收集结果
            for future in as_completed(futures):
                try:
                    worker_existing_files, worker_existing_local_paths = future.result()
                    with lock:
                        existing_files.extend(worker_existing_files)
                        existing_local_paths.extend(worker_existing_local_paths)
                except Exception as e:
                    self.logger.error(f"工作线程执行失败: {str(e)}")

        self.logger.info(f"文件检查完成: 存在 {len(existing_files)} 个文件，不存在 {len(file_list) - len(existing_files)} 个文件")
        return existing_files, existing_local_paths

    def check_files_existence_visualization(self, server_name, local_path_list, max_download_num=100, remote_dir=None, file_path_list=None, shuffle=False, max_workers=None):
        """
        带可视化进度条的文件存在性检查方法

        Args:
            server_name (str): 服务器配置名称，必须在初始化时提供的configs中
            local_path_list (Union[str, List[str]]): 本地保存路径，可以是：
                - str: 所有文件保存到该目录，文件名保持远程文件名
                - list: 每个文件对应的完整本地保存路径，长度必须与文件列表一致
            max_download_num (int, optional): 最大检查数量，默认为100
            remote_dir (str, optional): 要检查的远程目录路径，如果提供则检查该目录下所有文件
            file_path_list (List[str], optional): 预定义的文件路径列表，如果提供则直接检查这些文件
            shuffle (bool, optional): 是否随机打乱文件顺序，默认为False
            max_workers (int, optional): 最大工作线程数，默认使用初始化时的workers数量

        Returns:
            Tuple[List[str], Union[str, List[str]]]: 过滤后的文件列表和对应的本地路径列表
                - 当local_path_list为str时，返回的第二个元素仍为str
                - 当local_path_list为list时，返回的第二个元素为过滤后的本地路径列表

        Example:
            >>> # 带可视化进度条的文件存在性检查（检查所有文件）
            >>> downloader = MtFileDownloader(configs, workers=4)
            >>> file_list = ["/remote/file1.txt", "/remote/file2.jpg", "/remote/nonexistent.txt"]
            >>> local_paths = ["/local/file1.txt", "/local/file2.jpg", "/local/nonexistent.txt"]
            >>> existing_files, existing_local_paths = downloader.check_files_existence_visualization(
            ...     server_name="my_ftp",
            ...     local_path_list=local_paths,
            ...     file_path_list=file_list,
            ...     max_workers=4  # 使用4个线程并行检查
            ... )
            >>> # 显示：检查文件存在性: 100%|██████████| 3/3 [00:05<00:00,  1.7s/it]
            >>>
            >>> # 限制检查数量（只检查前100个文件）
            >>> existing_files, existing_local_paths = downloader.check_files_existence_visualization(
            ...     server_name="my_ftp",
            ...     local_path_list=local_paths,
            ...     file_path_list=file_list,
            ...     max_download_num=100,
            ...     max_workers=4
            ... )
        """
        from tqdm import tqdm
        with tqdm(desc="检查文件存在性", unit="file", miniters=1) as pbar:
            def update_progress(progress):
                """
                进度更新回调函数，由check_files_existence函数在检查过程中调用

                Args:
                    progress (int): 检查进度百分比（0-100）
                """
                pbar.update(1)

            existing_files, existing_local_paths = self.check_files_existence(
                server_name=server_name,
                local_path_list=local_path_list,
                max_download_num=max_download_num,
                remote_dir=remote_dir,
                file_path_list=file_path_list,
                shuffle=shuffle,
                callback=update_progress,
                max_workers=max_workers
            )
        return existing_files, existing_local_paths


    def download_files_by_pathlist(self, server_name, local_path_list, max_download_num=None, remote_dir=None,
                                   file_path_list=None, shuffle=False, callback=None, batch_size=20):
        """
        多线程下载FTP/SFTP文件列表

        Args:
            server_name (str): 服务器配置名称，必须在初始化时提供的configs中
            local_path_list (Union[str, List[str]]): 本地保存路径，可以是：
                - str: 所有文件保存到该目录，文件名保持远程文件名
                - list: 每个文件对应的完整本地保存路径，长度必须与文件列表一致
            max_download_num (int, optional): 最大下载数量，默认为None（下载所有文件）
            remote_dir (str, optional): 要下载的远程目录路径，如果提供则下载该目录下所有文件
            file_path_list (List[str], optional): 预定义的文件路径列表，如果提供则直接下载这些文件
            shuffle (bool, optional): 是否随机打乱文件顺序，默认为False
            callback (Callable, optional): 进度回调函数，支持两种格式：
                - Callable[[int], None]: 接收一个整数参数（0-100）表示总体进度
                - Callable[[int, int, str], None]: 接收三个参数(current, total, name)表示当前文件进度
            batch_size (int, optional): 每批处理文件数，默认为20

        Returns:
            int: 成功下载的文件数量

        Raises:
            ValueError: 当服务器配置不存在或参数不合法时
            RuntimeError: 当下载过程中发生错误时

        Example:
            >>> # 初始化下载器并配置FTP和SFTP
            >>> configs = {
            ...     "my_ftp": {
            ...         "host": "192.168.1.100",
            ...         "port": 21,
            ...         "username": "admin",
            ...         "password": "123456",
            ...         "type": "ftp"
            ...     },
            ...     "my_sftp": {
            ...         "host": "192.168.1.100",
            ...         "port": 22,
            ...         "username": "admin",
            ...         "password": "123456",
            ...         "type": "sftp"
            ...     }
            ... }
            >>> downloader = MtFtpDownloader(configs, workers=4, verbose=True)
            >>>
            >>> # 下载整个FTP目录到指定文件夹（下载所有文件）
            >>> success_count = downloader.download_files_by_pathlist(
            ...     server_name="my_ftp",
            ...     local_path_list="/local/download/path",
            ...     remote_dir="/remote/files",
            ...     shuffle=True,
            ...     callback=lambda p: print(f"进度: {p}%"),
            ...     batch_size=10
            ... )
            >>>
            >>> # 下载指定SFTP文件列表到不同路径（下载所有文件）
            >>> file_list = ["/remote/file1.txt", "/remote/file2.jpg"]
            >>> local_paths = ["/local/file1.txt", "/local/file2.jpg"]
            >>> success_count = downloader.download_files_by_pathlist(
            ...     server_name="my_sftp",
            ...     local_path_list=local_paths,
            ...     file_path_list=file_list,
            ...     shuffle=True,
            ...     callback=lambda current, total, name: print(f"{current}/{total}: {name}"),
            ...     batch_size=5
            ... )
            >>>
            >>> # 限制下载数量（只下载前10个文件）
            >>> success_count = downloader.download_files_by_pathlist(
            ...     server_name="my_ftp",
            ...     local_path_list="/local/download/path",
            ...     remote_dir="/remote/files",
            ...     max_download_num=10,
            ...     batch_size=5
            ... )
            >>>
            >>> # 先检查文件是否存在，然后只下载存在的文件
            >>> file_list = ["/remote/file1.txt", "/remote/file2.jpg", "/remote/nonexistent.txt"]
            >>> local_paths = ["/local/file1.txt", "/local/file2.jpg", "/local/nonexistent.txt"]
            >>> # 检查文件存在性
            >>> existing_files, existing_local_paths = downloader.check_files_existence(
            ...     server_name="my_ftp",
            ...     local_path_list=local_paths,
            ...     file_path_list=file_list
            ... )
            >>> # 下载存在的文件
            >>> success_count = downloader.download_files_by_pathlist(
            ...     server_name="my_ftp",
            ...     local_path_list=existing_local_paths,
            ...     file_path_list=existing_files,
            ...     batch_size=5
            ... )
            >>>
            >>> # 使用可视化进度条检查文件存在性
            >>> existing_files, existing_local_paths = downloader.check_files_existence_visualization(
            ...     server_name="my_ftp",
            ...     local_path_list=local_paths,
            ...     file_path_list=file_list
            ... )
            >>> # 下载存在的文件
            >>> success_count = downloader.download_files_by_pathlist(
            ...     server_name="my_ftp",
            ...     local_path_list=existing_local_paths,
            ...     file_path_list=existing_files,
            ...     batch_size=5
            ... )

        Notes:
            - remote_dir 和 file_path_list 参数二选一，不能同时使用
            - 如果同时提供 remote_dir 和 file_path_list，优先使用 file_path_list
            - 使用多线程时，每个线程会创建独立的连接
            - 每个线程内部会使用指定的 batch_size 进行分批处理
            - 服务器配置必须在初始化时提供，不支持运行时修改
        """
        if batch_size <= 0:
            raise ValueError("batch_size必须大于0")
        if server_name not in self._configs:
            raise ValueError(f"服务器配置 '{server_name}' 不存在，可用配置: {list(self._configs.keys())}")

        # 获取服务器类型
        server_config = self._configs[server_name]
        server_type = server_config.get('type', 'ftp').lower()

        # 获取文件列表
        if file_path_list is not None:
            file_list = file_path_list
        elif remote_dir is not None:
            if server_type == 'sftp':
                with SFTPClient(self._configs) as client:
                    file_list = client.get_dir_file_list(server_name, remote_dir)
            else:
                with FTPClient(self._configs) as client:
                    file_list = client.get_dir_file_list(server_name, remote_dir)
        else:
            raise ValueError("必须提供remote_dir或file_path_list参数")

        if not file_list:
            self.logger.warning("无文件可下载")
            return 0

        if shuffle:
            random.seed(42)
            random.shuffle(file_list)

        # 限制下载数量
        if max_download_num is not None:
            file_list = file_list[:max_download_num]
        total_files = len(file_list)

        # 将文件列表分配给各个工作线程
        worker_file_list = [file_list[i::self._workers] for i in range(self._workers)]
        worker_percent = [0 for _ in range(self._workers)]

        # 处理local_path_list，为每个工作线程创建对应的本地路径列表
        worker_local_path_list = []
        if isinstance(local_path_list, list):
            # 当local_path_list是列表时，为每个工作线程创建对应的子列表
            for worker_id in range(self._workers):
                # 获取该工作线程处理的文件索引
                worker_indices = [i for i in range(len(file_list)) if i % self._workers == worker_id]
                # 根据索引创建对应的本地路径子列表
                worker_local_paths = [local_path_list[i] for i in worker_indices]
                worker_local_path_list.append(worker_local_paths)
        else:
            # 当local_path_list是字符串时，所有线程使用相同的路径
            worker_local_path_list = [local_path_list for _ in range(self._workers)]

        def _atomic_callback(worker_index, percent, current=None, total=None, name=None):
            """原子化的进度回调，确保线程安全"""
            with self._lock:
                worker_percent[worker_index] = percent
                if callback:
                    try:
                        # 尝试作为三参数回调调用
                        callback(current, total, name)
                    except TypeError:
                        # 如果失败，作为单参数回调调用
                        overall_progress = sum(worker_percent) / self._workers
                        callback(int(overall_progress))

        # 创建线程池执行下载任务
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._workers) as executor:
            futures = []
            clients = []

            try:
                # 为每个工作线程创建独立的客户端连接
                for worker_id in range(self._workers):
                    if server_type == 'sftp':
                        client = SFTPClient(self._configs)
                        # SFTP客户端不需要显式连接，_get_connection会自动处理
                        clients.append(client)

                        # 提交下载任务到线程池
                        future = executor.submit(
                            client.download_file_list,
                            sftp_name=server_name,
                            remote_path_list=worker_file_list[worker_id],
                            local_path_list=worker_local_path_list[worker_id],
                            progress_callback=lambda p, t, n: _atomic_callback(worker_id, p / t * 100, p, t, n),
                            batch_size=batch_size
                        )
                    else:
                        client = FTPClient(self._configs)
                        client._ftpconnect(server_name)
                        clients.append(client)

                        # 提交下载任务到线程池
                        future = executor.submit(
                            client.download_file_list,
                            ftp_name=server_name,
                            remote_path_list=worker_file_list[worker_id],
                            local_path_list=worker_local_path_list[worker_id],
                            bufsize=1024,
                            progress_callback=lambda p, t, n: _atomic_callback(worker_id, p / t * 100, p, t, n),
                            batch_size=batch_size
                        )
                    futures.append(future)

                # 等待所有任务完成并统计成功数量
                success_count = 0
                for future in futures:
                    result = future.result()
                    # 处理不同客户端的返回值格式
                    if isinstance(result, tuple):
                        # SFTP客户端返回 (成功数, 总数)
                        success_count += result[0]
                    else:
                        # FTP客户端返回成功数
                        success_count += result

                self.logger.info(f"下载完成: {success_count}/{total_files} 个文件")

            except Exception as e:
                self.logger.error(f"下载过程中发生错误: {str(e)}")
                raise RuntimeError(f"文件下载失败: {str(e)}")
            finally:
                # 确保所有客户端连接正确关闭
                for client in clients:
                    try:
                        if hasattr(client, 'close'):
                            client.close()
                        elif hasattr(client, '_close'):
                            client._close()
                    except Exception as e:
                        self.logger.warning(f"关闭连接时出错: {str(e)}")

        return success_count
