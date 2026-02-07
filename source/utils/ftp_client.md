# Ftp_client

FTP客户端下载和上传

## 核心功能
- **FTP连接管理**：支持多服务器配置、自动连接和重连机制
- **文件传输**：支持文件上传和下载，均支持断点续传
- **目录操作**：列出远程目录内容、判断远程路径是否为目录
- **递归遍历**：递归获取FTP目录及其所有子目录中的文件列表
- **进度可视化**：提供带进度条的文件传输方法，支持实时进度显示
- **异常处理**：内置重试机制和错误处理，提高传输稳定性
- **安全操作**：使用上下文管理器确保连接正确关闭

## 使用示例

### 基本连接和文件下载

```python
from coreXAlgo.utils.ftp_client import FTPClient

# 配置FTP服务器信息
ftp_configs = {
    "server1": {
        "host": "ftp.example.com",
        "port": 21,
        "username": "user",
        "password": "pass"
    }
}

# 创建FTP客户端实例
client = FTPClient(ftp_configs, verbose=True)

# 下载单个文件
client.download_file(
    ftp_name="server1",
    remote_path="/remote/path/file.txt",
    local_path="./local/path/file.txt"
)
```

### 带进度条的文件上传

```python
# 带可视化进度条的上传
client.upload_file_visualization(
    ftp_name="server1",
    local_path="./local/large_file.zip",
    remote_path="/server/backups/large_file.zip"
)
# 显示：上传文件: 45%|████▌     | 45.2M/100M [00:30<00:45, 1.2MB/s]
```

### 递归获取目录文件列表

```python
# 递归获取目录下所有文件
file_list = client.get_dir_file_list(
    ftp_name="server1",
    ftp_dir="/data"
)
print(file_list)
# 输出: ['/data/file1.txt', '/data/docs/report.pdf', '/data/images/photo.jpg']
```

### 批量文件下载

```python
# 批量下载多个文件
def progress_callback(current_idx, total_files, file_name):
    print(f"正在下载 {current_idx}/{total_files}: {file_name}")

remote_files = ["/data/file1.txt", "/data/file2.txt", "/data/file3.txt"]
local_dir = "./downloads"

client.download_file_list(
    ftp_name="server1",
    remote_path_list=remote_files,
    local_path_list=local_dir,
    progress_callback=progress_callback
)
```

### 使用上下文管理器

```python
# 使用上下文管理器自动管理连接
with FTPClient(ftp_configs) as client:
    # 检查连接状态
    is_connected = client.is_connected("server1")
    print(f"连接状态: {is_connected}")
    
    # 列出目录内容
    files = client.list_dir("/data")
    print(f"目录内容: {files}")
# 退出上下文管理器时自动关闭连接
```

### API 参考

```{eval-rst}
.. automodule:: coreXAlgo.utils.ftp_client
   :members:
   :undoc-members:
   :show-inheritance:
```