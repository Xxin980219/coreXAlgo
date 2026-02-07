# Mt_ftp_downloader

多线程并行下载ftp文件夹的所有文件

## 核心功能

- **多线程并发下载**：支持多线程同时下载多个文件，提高下载速度
- **FTP连接池管理**：为每个线程创建独立的FTP连接，避免连接冲突
- **灵活的文件选择**：支持下载整个目录或指定的文件列表
- **进度回调**：提供实时进度回调功能，方便显示下载进度
- **文件顺序控制**：支持随机打乱文件顺序，避免集中下载特定目录的文件
- **下载数量限制**：支持设置最大下载数量，避免一次性下载过多文件
- **错误处理**：提供详细的错误处理和日志记录

## 使用示例

### 基本使用示例

```python
from coreXAlgo.utils.mt_ftp_downloader import MtFtpDownloader

# 创建下载器实例
downloader = MtFtpDownloader(workers=4, verbose=True)

# 设置FTP服务器配置
ftp_config = {
    "my_ftp": {
        "host": "192.168.1.100",
        "port": 21,
        "user": "admin",
        "password": "123456"
    }
}
downloader.set_ftp_config(ftp_config)

# 下载整个目录到指定文件夹
def progress_callback(percent):
    print(f"下载进度: {percent}%")

success_count = downloader.download_files_by_pathlist(
    ftp_name="my_ftp",
    local_path_list="/local/download/path",
    ftp_dir="/remote/files",
    max_download_num=50,
    shuffle=True,
    callback=progress_callback
)

print(f"成功下载: {success_count} 个文件")
```

### 下载指定文件列表

```python
# 下载指定的文件列表到不同路径
file_list = ["/remote/file1.txt", "/remote/file2.jpg", "/remote/file3.pdf"]
local_paths = ["/local/file1.txt", "/local/file2.jpg", "/local/file3.pdf"]

success_count = downloader.download_files_by_pathlist(
    ftp_name="my_ftp",
    local_path_list=local_paths,
    img_path_list=file_list,
    max_download_num=10
)

print(f"成功下载: {success_count} 个文件")
```

### 调整线程数量

```python
# 创建更多线程的下载器实例（适用于网络带宽充足的情况）
downloader = MtFtpDownloader(workers=8, verbose=True)
downloader.set_ftp_config(ftp_config)

# 下载文件
success_count = downloader.download_files_by_pathlist(
    ftp_name="my_ftp",
    local_path_list="/local/download/path",
    ftp_dir="/remote/large_files",
    max_download_num=200
)

print(f"成功下载: {success_count} 个文件")
```

```{eval-rst}
.. automodule:: coreXAlgo.utils.mt_ftp_downloader
   :members:
   :undoc-members:
   :show-inheritance:
```