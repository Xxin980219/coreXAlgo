# Basic

基础函数

## 核心功能

- **文件查找**：递归查找目录中的文件，支持按扩展名过滤
- **文件名处理**：提取文件名、生成顺序文件名
- **文件操作**：复制、移动单个或多个文件
- **文件分析**：查找重复文件、缺失文件
- **文件选择**：随机选择指定数量的文件

## 使用示例

### 文件查找

```python
from coreXAlgo.file_processing import get_files, get_filenames

# 查找目录中的所有XML文件
xml_files = get_files('annotations/', '.xml')
print(f"Found {len(xml_files)} XML files")

# 提取文件名列表（不含扩展名）
filenames = get_filenames('images/', '.jpg')
print(f"Found {len(filenames)} JPG files")
```

### 文件操作

```python
from coreXAlgo.file_processing import copy_file, move_file, copy_files, move_files

# 复制单个文件
copy_file('source/file.txt', 'destination/file.txt')

# 移动单个文件
move_file('source/file.txt', 'destination/file.txt')

# 批量复制文件
file_pairs = [('source/file1.txt', 'dest/file1.txt'), ('source/file2.txt', 'dest/file2.txt')]
copy_files(file_pairs)

# 批量移动文件
move_files(file_pairs)
```

### 文件分析

```python
from coreXAlgo.file_processing import get_duplicate_files, get_missing_files

# 查找重复文件
duplicates = get_duplicate_files('directory/')
print(f"Found {len(duplicates)} duplicate files")

# 查找缺失文件
source_files = ['file1.txt', 'file2.txt', 'file3.txt']
target_files = ['file1.txt', 'file3.txt']
missing = get_missing_files(source_files, target_files)
print(f"Missing files: {missing}")
```

### 随机文件选择

```python
from coreXAlgo.file_processing import randomly_select_files

# 随机选择5个文件
selected = randomly_select_files('directory/', 5, '.jpg')
print(f"Selected files: {selected}")
```

### 生成顺序文件名

```python
from coreXAlgo.file_processing import generate_sequential_filename

# 生成顺序文件名
filename = generate_sequential_filename('output/', 'image', '.jpg')
print(f"Generated filename: {filename}")
```

### API 参考

```{eval-rst}
.. automodule:: coreXAlgo.file_processing.basic
   :members:
   :undoc-members:
   :show-inheritance:
```