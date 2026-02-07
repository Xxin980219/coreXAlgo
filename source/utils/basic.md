# Basic

基础函数

## 核心功能

- **字符串处理**：输出带颜色和样式的字符串
- **随机种子设置**：设置所有随机数生成器的种子，确保结果可复现
- **日志配置**：配置并返回日志记录器
- **GPU管理**：打印GPU内存使用情况、检查CUDA环境、设置可见GPU设备
- **文件序列化**：支持JSON、YAML和pickle格式的对象保存和加载
- **线程池**：使用线程池并行处理数据项，支持进度显示和错误处理

## 使用示例

### 字符串处理

```python
from coreXAlgo.utils import colorstr

# 基本用法
print(colorstr('red', 'bold', 'Error Message'))
print(colorstr('green', 'Success!'))
print(colorstr('hello world'))  # 默认蓝色粗体

# 组合使用
warning_msg = colorstr('yellow', 'underline', 'Warning:')
print(f"{warning_msg} This is a warning message")
```

### 随机种子设置

```python
from coreXAlgo.utils import set_all_seed

# 设置随机种子
set_all_seed(42)
# 后续的随机操作将产生可复现的结果
```

### 日志配置

```python
from coreXAlgo.utils import set_logging

# 创建和使用日志记录器（输出显示）
logger = set_logging("my_app", verbose=True)
logger.info("Application started")  # 会输出到控制台

# 创建和使用日志记录器（不输出显示）
logger = set_logging("my_app", verbose=False)
logger.info("Application started")  # 不会输出到控制台
```

### GPU管理

```python
from coreXAlgo.utils import print_gpu_memory, check_cuda_available, set_gpu_visible

# 打印当前GPU内存使用情况
print_gpu_memory()

# 检查CUDA环境和GPU配置
check_cuda_available()

# 设置可见的GPU设备
set_gpu_visible(0)  # 只使用第0号GPU
# 或使用多块GPU
# set_gpu_visible('0,1,2')
```

### 文件序列化

```python
from coreXAlgo.utils import obj_to_json, obj_from_json, obj_to_yaml, obj_from_yaml, obj_to_pkl, obj_from_pkl

# JSON操作
config = {'lr': 0.01, 'batch_size': 32}
obj_to_json(config, 'config.json')
loaded_config = obj_from_json('config.json')

# YAML操作
obj_to_yaml(config, 'config.yaml')
loaded_config = obj_from_yaml('config.yaml')

# Pickle操作
obj_to_pkl(config, 'config.pkl')
loaded_config = obj_from_pkl('config.pkl')
```

### 线程池并行处理

```python
from coreXAlgo.utils import thread_pool

# 定义处理函数
def process_item(item):
    # 处理逻辑
    print(f"Processing: {item}")

# 要处理的数据项
items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# 使用线程池并行处理
failed_indices = thread_pool(process_item, items, workers=4)
print(f"Failed indices: {failed_indices}")
```

## API 参考

```{eval-rst}
.. automodule:: coreXAlgo.utils.basic
   :members:
   :undoc-members:
   :show-inheritance:
```