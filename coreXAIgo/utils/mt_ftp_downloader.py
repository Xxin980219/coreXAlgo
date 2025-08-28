import concurrent.futures
import random
from threading import RLock
from typing import Dict
from ..utils import FTPClient, set_logging

__all__ = ['MtFtpDownloader']

# Set logger
logger = set_logging(__name__)


class MtFtpDownloader:
    """多线程并行下载ftp文件夹的所有文件"""

    def __init__(self, workers=4):
        self._workers = workers
        self._ftp_config = None
        self._lock = RLock()

    def set_ftp_config(self, ftp_configs: Dict[str, dict]):
        self._ftp_config = ftp_configs

    def download_files_by_pathlist(self, ftp_name, save_dir, max_download_num=100, ftp_dir=None, img_path_list=None,
                                   shuffle=False, callback=None):
        with FTPClient(self._ftp_config) as ftp:
            # 获取文件列表
            file_list = img_path_list if ftp_dir is None else ftp.get_dir_file_list(ftp_name, ftp_dir)

        if not file_list:
            logger.warning("无文件可下载")
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
                logger.error(f"线程下载异常: {str(e)}")
        return success_count


if __name__ == '__main__':
    ftp_configs = {
        "155": {
            "host": "10.141.70.155",
            "port": 21,
            "username": "root",
            "password": "admin@boe"
        },
        "169": {
            "host": "10.141.70.169",
            "port": 21,
            "username": "root",
            "password": "xh01@B7cim"
        },
        "151": {
            "host": "10.141.70.151",
            "port": 21,
            "username": "root",
            "password": "admin@boe"
        }
    }

    mt_ftp_downloader = MtFtpDownloader()
    mt_ftp_downloader.set_ftp_config(ftp_configs)

    a = mt_ftp_downloader.download_files_by_pathlist("155",
                                                     ftp_dir="/TSP/20241216/P8_to_U4/NG",
                                                     save_dir=r"D:\Xxin\PycharmProjects\SplitData\xxin_dev\utils\123")
    print(a)
    # remote_img_dir = "/media/nas/ftpdata/public-service/vsftpd1/1"
    # # 读取CSV文件
    # df_total = pd.read_csv(r'D:\Xxin\PycharmProjects\SplitData\datas\OLED2\BP_O.csv')
    # a, b = os.path.split(r'D:\Xxin\PycharmProjects\SplitData\datas\OLED2\BP_O.csv')
    # img_path_list = []
    # for index, r in df_total.iterrows():
    #     remote_path = f"{remote_img_dir}/{r['image_path'].lstrip('/')}/{r['image_name']}"
    #     # remote_path = f"/{r['image_path'].lstrip('/')}/{r['image_name']}"
    #     img_path_list.append(remote_path)
