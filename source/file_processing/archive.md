# Archive

文件压缩解压

## 核心功能

- **压缩格式支持**：支持多种压缩格式，包括 ZIP、TAR、TAR.GZ、TAR.BZ2
- **文件夹压缩**：将整个文件夹压缩为指定格式
- **文件解压**：解压压缩文件到指定目录
- **大文件支持**：优化大文件的解压处理

## 使用示例

### 压缩文件夹

```python
from coreXAlgo.file_processing import ArchiveManager, CompressionFormat

# 创建归档管理器实例
manager = ArchiveManager()

# 压缩文件夹为ZIP格式
manager.compress('source_folder/', 'output.zip', CompressionFormat.ZIP)

# 压缩文件夹为TAR.GZ格式
manager.compress('source_folder/', 'output.tar.gz', CompressionFormat.TARGZ)
```

### 解压文件

```python
from coreXAlgo.file_processing import ArchiveManager

# 创建归档管理器实例
manager = ArchiveManager()

# 解压ZIP文件
manager.extract('input.zip', 'output_folder/')

# 解压TAR.GZ文件
manager.extract('input.tar.gz', 'output_folder/')
```

### 大文件解压

```python
from coreXAlgo.file_processing import ArchiveManager

# 创建归档管理器实例
manager = ArchiveManager()

# 解压大文件（自动处理大文件解压）
manager.extract('large_archive.zip', 'output_folder/')
```

### API 参考

```{eval-rst}
.. automodule:: coreXAlgo.file_processing.archive
   :members:
   :undoc-members:
   :show-inheritance:
```