# Mt_file_downloader

多线程并行下载FTP/SFTP文件夹的所有文件

## 核心功能

- **多线程并发下载**：支持多线程同时下载多个文件，提高下载速度
- **连接池管理**：为每个线程创建独立的FTP/SFTP连接，避免连接冲突
- **协议支持**：同时支持FTP和SFTP协议，统一接口操作
- **灵活的文件选择**：支持下载整个目录或指定的文件列表
- **进度回调**：提供实时进度回调功能，方便显示下载进度
- **文件顺序控制**：支持随机打乱文件顺序，避免集中下载特定目录的文件
- **下载数量限制**：支持设置最大下载数量，避免一次性下载过多文件
- **错误处理**：提供详细的错误处理和日志记录
- **断点续传**：支持文件下载的断点续传功能
- **文件完整性验证**：自动验证下载文件的完整性
- **批量处理控制**：支持自定义每批处理文件数量，提高下载稳定性
- **文件存在性检查**：支持批量检查文件是否存在
- **智能连接管理**：内置连接保活、健康检查和自动重连机制
- **连接预热**：在开始检查前预热连接，确保连接稳定性
- **服务器友好**：智能的请求间隔，避免服务器限流
- **详细的日志输出**：支持详细的连接状态和错误处理日志

## 使用示例

### 基本使用示例

```python
from coreXAlgo.utils.mt_file_downloader import MtFileDownloader

# 配置FTP服务器信息
file_config = {
    "my_ftp": {
        "host": "192.168.1.100",
        "port": 21,
        "username": "admin",
        "password": "123456"
    },
    "my_sftp": {
        "host": "192.168.1.101",
        "port": 22,
        "username": "user",
        "password": "pass123"
    }
}

# 创建下载器实例（初始化时直接传入服务器配置）
downloader = MtFileDownloader(file_config, workers=4, verbose=True)

# 下载整个目录到指定文件夹
def progress_callback(percent):
    print(f"下载进度: {percent}%")

success_count = downloader.download_files_by_pathlist(
    ftp_name="my_ftp",  # 可以使用FTP或SFTP配置
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
    ftp_name="my_sftp",  # 使用SFTP配置
    local_path_list=local_paths,
    img_path_list=file_list,
    max_download_num=10
)

print(f"成功下载: {success_count} 个文件")
```

### 调整线程数量

```python
# 创建更多线程的下载器实例（适用于网络带宽充足的情况）
downloader = MtFileDownloader(file_config, workers=8, verbose=True)

# 下载文件
success_count = downloader.download_files_by_pathlist(
    ftp_name="my_ftp",
    local_path_list="/local/download/path",
    ftp_dir="/remote/large_files",
    max_download_num=200
)

print(f"成功下载: {success_count} 个文件")
```

### 自定义批处理大小

```python
# 自定义每批处理文件数量，提高下载稳定性
# 适用于网络不稳定或服务器连接限制较严格的情况
success_count = downloader.download_files_by_pathlist(
    ftp_name="my_ftp",
    local_path_list="/local/download/path",
    ftp_dir="/remote/large_files",
    max_download_num=200,
    batch_size=10  # 每批处理10个文件
)

print(f"成功下载: {success_count} 个文件")

# 对于SFTP服务器，也可以使用相同的方式设置batch_size
success_count = downloader.download_files_by_pathlist(
    ftp_name="my_sftp",
    local_path_list="/local/sftp_downloads",
    ftp_dir="/remote/sftp_files",
    max_download_num=100,
    batch_size=5  # 每批处理5个文件
)

print(f"成功下载: {success_count} 个文件")
```

### 使用SFTP协议

```python
# 使用SFTP协议下载文件
success_count = downloader.download_files_by_pathlist(
    ftp_name="my_sftp",  # 使用SFTP配置
    local_path_list="/local/sftp_downloads",
    ftp_dir="/remote/sftp_files",
    max_download_num=100
)

print(f"成功下载: {success_count} 个文件")
```

### 文件存在性检查

```python
# 批量检查文件是否存在
downloader = MtFileDownloader(file_config, workers=20, verbose=True)

# 准备文件列表
file_list = ["/remote/file1.txt", "/remote/file2.jpg", "/remote/file3.pdf"]
local_paths = ["/local/file1.txt", "/local/file2.jpg", "/local/file3.pdf"]

print("开始检查文件存在性...")
existing_files, existing_local_paths = downloader.check_files_existence(
    server_name="my_ftp",
    file_path_list=file_list,
    local_path_list=local_paths,
    max_download_num=None  # 检查所有文件
)

print(f"文件检查完成: 存在 {len(existing_files)} 个文件，不存在 {len(file_list) - len(existing_files)} 个文件")

# 使用存在的文件列表进行下载
if existing_files:
    success_count = downloader.download_files_by_pathlist(
        ftp_name="my_ftp",
        local_path_list=existing_local_paths,
        img_path_list=existing_files
    )
    print(f"成功下载: {success_count} 个文件")
```

### 多线程文件检查

```python
# 多线程并行检查大量文件
downloader = MtFileDownloader(file_config, workers=20, verbose=True)  # 20个线程

# 准备大量文件列表
file_list = [f"/remote/file{i}.txt" for i in range(10000)]
local_paths = [f"/local/file{i}.txt" for i in range(10000)]

print("开始检查文件存在性...")
existing_files, existing_local_paths = downloader.check_files_existence(
    server_name="my_ftp",
    file_path_list=file_list,
    local_path_list=local_paths,
    max_download_num=None  # 默认检查所有文件
)

print(f"文件检查完成: 存在 {len(existing_files)} 个文件，不存在 {len(file_list) - len(existing_files)} 个文件")
```

### 连接管理参数

```python
# 配置连接管理参数
downloader = MtFileDownloader(file_config, workers=10, verbose=True)

# 调整连接管理参数
success_count = downloader.download_files_by_pathlist(
    ftp_name="my_ftp",
    local_path_list="/local/downloads",
    ftp_dir="/remote/files",
    batch_size=50,  # 每批处理50个文件
    max_download_num=1000
)
```

### 最大下载数量默认行为

```python
# max_download_num 未指定时，默认检查/下载所有文件
downloader = MtFileDownloader(file_config, workers=5, verbose=True)

# 检查所有文件
existing_files, existing_local_paths = downloader.check_files_existence(
    server_name="my_ftp",
    file_path_list=file_list,
    local_path_list=local_paths
    # 未指定 max_download_num，默认检查所有
)

# 下载所有文件
success_count = downloader.download_files_by_pathlist(
    ftp_name="my_ftp",
    local_path_list=existing_local_paths,
    img_path_list=existing_files
    # 未指定 max_download_num，默认下载所有
)
```

### 高级错误处理

```python
# 启用详细日志，查看连接状态和错误处理
downloader = MtFileDownloader(file_config, workers=10, verbose=True)

# 下载文件，自动处理连接错误
try:
    success_count = downloader.download_files_by_pathlist(
        ftp_name="my_ftp",
        local_path_list="/local/downloads",
        ftp_dir="/remote/large_files",
        max_download_num=500
    )
    print(f"成功下载: {success_count} 个文件")
except Exception as e:
    print(f"下载过程中发生错误: {str(e)}")
```

## 技术特性

### 连接管理
- **NOOP保活**：定期发送NOOP命令保持连接活跃
- **智能重连**：遇到425/550错误时自动重新连接
- **连接预热**：开始检查前发送预热命令确保连接稳定
- **健康检查**：每次操作前验证连接状态

### 错误处理
- **425错误处理**：无法建立连接时的自动重连
- **550错误处理**：无法获取文件大小时的重试策略
- **连续错误跟踪**：监控连续错误，超过阈值强制重连
- **指数退避**：错误重试时的智能延迟策略

### 服务器友好
- **智能请求间隔**：避免短时间内发送过多请求
- **LIST命令延迟**：为LIST命令添加额外延迟，减少服务器拒绝
- **批量重新连接**：定期重新建立连接，避免连接老化

### 性能优化
- **多线程并行**：充分利用网络带宽
- **连接池隔离**：每个线程独立连接，避免冲突
- **文件顺序打乱**：均匀分布请求，避免服务器热点
- **批量处理**：减少连接建立开销

## API参考

```{eval-rst}
.. automodule:: coreXAlgo.utils.mt_file_downloader
   :members:
   :undoc-members:
   :show-inheritance:
```