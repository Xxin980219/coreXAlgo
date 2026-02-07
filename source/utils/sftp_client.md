# Sftp_client

SFTP客户端下载和上传

## 核心功能

- **多服务器配置管理**：支持配置多个SFTP服务器，通过名称进行切换
- **文件传输**：支持文件上传和下载，均支持断点续传
- **批量操作**：支持批量下载或上传多个文件，支持分批处理
- **连接池管理**：优化连接参数，复用连接，提高性能
- **进度监控**：提供实时进度回调功能，支持可视化进度条
- **递归目录操作**：支持递归获取目录下所有文件列表
- **安全认证**：支持密码认证和SSH密钥认证，支持从环境变量获取密码
- **错误处理**：完善的错误处理机制，支持指数退避重试
- **文件完整性验证**：自动验证传输前后的文件大小
- **连接稳定性**：优化连接参数，解决连接异常问题
- **上下文管理器**：支持使用with语句自动管理资源

## 优化内容

- 修复了 `'Channel' object has no attribute 'set_buff_size'` 连接异常
- 解决了 `Garbage packet received` 下载异常
- 优化了连接参数和错误处理逻辑
- 增加了连接池管理，提高连接复用率
- 支持从环境变量获取密码，增强安全性
- 支持SSH密钥认证，提供更多认证选项
- 优化了断点续传功能，提高大文件传输稳定性

## 使用示例

### 基本使用示例

```python
from coreXAlgo.utils.sftp_client import SFTPClient

# 配置SFTP服务器信息
sftp_configs = {
    "sftp_server1": {
        "host": "10.141.1.120",
        "port": 22,
        "username": "root",
        "password": "admin"
    }
}

# 创建SFTP客户端实例
client = SFTPClient(sftp_configs, verbose=True)

# 检查连接
if client.is_connected("sftp_server1"):
    print("连接正常")

# 下载单个文件
client.download_file(
    sftp_name="sftp_server1",
    remote_path="/remote/path/file.txt",
    local_path="./local/path/file.txt"
)

# 上传单个文件
client.upload_file(
    sftp_name="sftp_server1",
    local_path="./local/path/file.txt",
    remote_path="/remote/path/file.txt"
)

# 关闭连接
client.close()
```

### 批量下载文件

```python
# 批量下载多个文件
def progress_callback(current, total, filename):
    print(f"[{current}/{total}] 处理: {filename}")

remote_files = ["/remote/file1.txt", "/remote/file2.jpg", "/remote/file3.pdf"]

success, total = client.download_file_list(
    sftp_name="sftp_server1",
    remote_path_list=remote_files,
    local_path_list="./local/downloads",
    progress_callback=progress_callback,
    batch_size=20,
    max_workers=4
)

print(f"下载完成: {success}/{total}")
```

### 批量上传文件

```python
# 批量上传多个文件
local_files = ["./local/file1.txt", "./local/file2.jpg"]
remote_destinations = ["/remote/upload/file1.txt", "/remote/upload/file2.jpg"]

success, total = client.upload_file_list(
    sftp_name="sftp_server1",
    local_path_list=local_files,
    remote_path_list=remote_destinations,
    batch_size=20
)

print(f"上传完成: {success}/{total}")
```

### 带进度条的文件传输

```python
# 带可视化进度条的下载
client.download_file_visualization(
    sftp_name="sftp_server1",
    remote_path="/remote/large_file.zip",
    local_path="./local/large_file.zip"
)

# 带可视化进度条的上传
client.upload_file_visualization(
    sftp_name="sftp_server1",
    local_path="./local/large_file.zip",
    remote_path="/remote/large_file.zip"
)
```

### 递归获取目录文件列表

```python
# 递归获取目录下所有文件
all_files = client.get_dir_file_list(
    sftp_name="sftp_server1",
    sftp_dir="/remote/project"
)

print(f"找到 {len(all_files)} 个文件")
for file_path in all_files[:10]:  # 打印前10个文件
    print(file_path)
```

### 使用SSH密钥认证

```python
# 使用SSH密钥认证
sftp_configs = {
    "sftp_server2": {
        "host": "10.141.1.121",
        "port": 22,
        "username": "user",
        "private_key": "/path/to/key.pem",
        "passphrase": "optional_passphrase"  # 密钥密码（如果有）
    }
}

client = SFTPClient(sftp_configs)

# 检查连接
if client.is_connected("sftp_server2"):
    print("使用SSH密钥连接成功")
```

### 从环境变量获取密码

```python
import os

# 设置环境变量
os.environ["SFTP_PASSWORD"] = "your_secure_password"

# 从环境变量获取密码
sftp_configs = {
    "sftp_server3": {
        "host": "10.141.1.122",
        "port": 22,
        "username": "user",
        "password_env": "SFTP_PASSWORD"  # 从环境变量获取密码
    }
}

client = SFTPClient(sftp_configs)

# 检查连接
if client.is_connected("sftp_server3"):
    print("使用环境变量密码连接成功")
```

### 使用上下文管理器

```python
# 使用上下文管理器自动管理资源
with SFTPClient(sftp_configs) as client:
    # 执行操作
    client.download_file(
        sftp_name="sftp_server1",
        remote_path="/remote/path/file.txt",
        local_path="./local/path/file.txt"
    )
    
# 退出上下文管理器时自动关闭连接
print("连接已自动关闭")
```

### API 参考

```{eval-rst}
.. automodule:: coreXAlgo.utils.sftp_client
   :members:
   :undoc-members:
   :show-inheritance:
```