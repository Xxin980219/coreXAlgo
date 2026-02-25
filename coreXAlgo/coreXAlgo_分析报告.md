# coreXAlgo 工具类项目分析报告

## 📋 项目基本信息

| 项目属性 | 内容         |
|---------|------------|
| **项目名称** | coreXAlgo  |
| **版本号** | 0.4.9      |
| **作者** | Xxin_BOE   |
| **项目类型** | Python 工具库 |
| **主要领域** | 计算机视觉、数据处理 |
| **版权年份** | 2026       |
| **Python 兼容性** | ≥ 3.8      |

---

## 🏗️ 项目架构概览

```
coreXAlgo/
├── __init__.py              # 主入口文件
├── version.py               # 版本管理
├── utils/                   # 基础工具模块
│   ├── basic.py            # 基础工具函数
│   ├── bbox_util.py        # 边界框处理工具
│   ├── constants.py        # 常量定义
│   ├── ftp_client.py       # FTP客户端
│   ├── sftp_client.py      # SFTP客户端
│   ├── mt_db_client.py     # 多线程数据库客户端
│   └── mt_file_downloader.py # 多线程文件下载器
├── adv_cv/                 # 高级计算机视觉模块
│   └── basic.py           # 图像处理功能
└── file_processing/         # 文件处理模块
    ├── basic.py           # 文件操作工具
    ├── archive.py         # 压缩解压管理
    ├── annotation_convert.py # 标注格式转换
    ├── data_preprocessing.py # 数据预处理
    ├── image_crop.py      # 图像裁剪处理
    └── voc_xml_deal.py   # VOC XML处理
```

---

## 📦 模块详细分析

### 一、utils 模块 - 基础工具集

#### 1.1 基础工具函数 (basic.py)

| 函数名 | 功能描述 | 使用场景 |
|--------|---------|---------|
| `colorstr()` | 输出带颜色和样式的字符串 | 日志输出、终端美化 |
| `set_all_seed()` | 设置所有随机数生成器种子 | 实验可复现性 |
| `set_logging()` | 配置日志记录器 | 日志管理 |
| `print_gpu_memory()` | 打印GPU内存使用情况 | GPU资源监控 |
| `check_cuda_available()` | 检查CUDA环境 | 环境验证 |
| `set_gpu_visible()` | 设置可见的GPU设备 | 多GPU管理 |
| `obj_to_json()` / `obj_from_json()` | JSON文件读写 | 配置文件管理 |
| `obj_to_yaml()` / `obj_from_yaml()` | YAML文件读写 | 配置文件管理 |
| `obj_to_pkl()` / `obj_from_pkl()` | Pickle文件读写 | 模型/数据保存 |
| `thread_pool()` | 多线程并行处理 | 批量任务加速 |

**代码示例**：
```python
from coreXAlgo.utils import set_all_seed, colorstr, thread_pool

# 设置随机种子
set_all_seed(42)

# 输出彩色日志
print(colorstr('red', 'bold', 'Error occurred'))

# 多线程处理
def process_file(file_path):
    # 处理文件
    pass

failed = thread_pool(process_file, file_list, workers=4)
```

#### 1.2 边界框处理工具 (bbox_util.py)

| 函数名 | 功能描述 |
|--------|---------|
| `polygon_to_bbox()` | 多边形转边界框 |
| `cnt_to_polygon()` | 轮廓转多边形 |
| `mask_to_polygon()` | 二值掩码转多边形 |
| `mask_to_polygons()` | 二值掩码转多个多边形 |
| `merge_boxes_by_expansion()` | 基于扩展的框合并 |
| `merge_boxes_by_conditions()` | 多条件框合并（重叠、相邻、包含） |
| `merge_adjacent_boxes()` | 合并相邻框 |
| `DetectionVisualizer` | 目标检测可视化器类 |

**DetectionVisualizer 类特性**：
- ✅ 双模式渲染：快速模式 和 高质量模式
- ✅ 智能颜色分配
- ✅ 智能标签位置
- ✅ 自适应参数
- ✅ 多形状支持（矩形、线段、多边形）

**代码示例**：
```python
from coreXAlgo.utils import DetectionVisualizer

visualizer = DetectionVisualizer()
detections = [
    {'label': 'person', 'shapeType': 'rectangle',
     'points': [[50, 50], [150, 150]],
     'result': {'confidence': 0.95}}
]

# 快速模式
result_fast = visualizer.draw_detection_results(image, detections, quality='fast')

# 高质量模式
result_hq = visualizer.draw_detection_results(image, detections, quality='high')
```

#### 1.3 网络传输工具

##### FTPClient (ftp_client.py)

**核心功能**：
- 多服务器配置管理
- 自动连接和重连机制
- 文件上传下载（支持断点续传）
- 目录遍历和文件列表获取
- 进度可视化和回调通知
- 异常处理和重试机制

**主要方法**：
```python
from coreXAlgo.utils import FTPClient

ftp_configs = {
    "server1": {
        "host": "ftp.example.com",
        "port": 21,
        "username": "user",
        "password": "pass"
    }
}

client = FTPClient(ftp_configs, verbose=True)
client.download_file("server1", "/remote/file.txt", "./local/file.txt")
client.upload_file("server1", "./local/file.txt", "/remote/file.txt")
```

##### MTFileDownloader (mt_file_downloader.py)

**核心功能**：
- 多线程文件下载器，替换了旧的 mt_ftp_downloader.py
- 支持多种协议的文件下载
- 多线程并行下载，提高下载速度
- 断点续传和自动重试机制
- 进度条显示和回调通知
- 完善的错误处理和日志记录

**主要方法**：
```python
from coreXAlgo.utils import MTFileDownloader

# 初始化下载器
downloader = MTFileDownloader(max_workers=4, verbose=True)

# 下载单个文件
downloader.download("ftp://example.com/file.zip", "./local/file.zip")

# 批量下载多个文件
file_list = [
    ("ftp://example.com/file1.txt", "./local/file1.txt"),
    ("ftp://example.com/file2.txt", "./local/file2.txt")
]
downloader.batch_download(file_list)
```

##### SFTPClient (sftp_client.py)

**核心功能**：
- 安全的文件传输协议
- 支持断点续传
- 多服务器配置和连接池管理
- 分块传输大文件
- 并行处理批量文件
- 详细的进度监控
- 完善的错误处理和重试机制
- SSH安全配置优化
- 支持多种Paramiko版本兼容性

**主要方法**：
```python
from coreXAlgo.utils import SFTPClient

sftp_configs = {
    "server1": {
        "host": "sftp.example.com",
        "port": 22,
        "username": "user",
        "password": "pass"
    }
}

# 初始化客户端，启用连接池
client = SFTPClient(sftp_configs, verbose=True, max_pool_size=10)

# 下载文件
client.download_file("server1", "/remote/file.txt", "./local/file.txt")

# 上传文件
client.upload_file("server1", "./local/file.txt", "/remote/file.txt")

# 批量下载（并行处理）
file_pairs = [
    ("/remote/file1.txt", "./local/file1.txt"),
    ("/remote/file2.txt", "./local/file2.txt")
]
client.batch_download("server1", file_pairs, workers=4)

# 批量上传（并行处理）
client.batch_upload("server1", file_pairs, workers=4)
```

#### 1.4 数据库客户端 (mt_db_client.py)

**核心功能**：
- 轻量级多数据库查询客户端（仅支持查询操作）
- 支持多种数据库（MySQL、PostgreSQL、SQLite等）
- 连接池管理和自动重连
- 查询结果缓存
- 数据导出为CSV
- 表结构操作
- 详细的错误处理和日志
- 上下文管理器支持
- SQLAlchemy版本兼容性修复

**主要方法**：
| 方法名 | 功能描述 |
|--------|---------|
| `query()` | 执行SQL查询并返回结果 |
| `query_to_dataframe()` | 执行查询并将结果转换为pandas DataFrame |
| `list_databases()` | 获取所有已配置的数据库名称列表 |
| `list_tables()` | 获取数据库中的所有表名 |
| `get_table_schema()` | 获取表的结构信息 |
| `export_to_csv()` | 执行查询并将结果导出为CSV文件 |
| `get_database_metadata()` | 获取数据库元数据 |

**代码示例**：
```python
from coreXAlgo.utils import MtDBClient

# 配置数据库连接
db_configs = {
    "user_db": {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "password",
        "database": "user_management"
    }
}

# 创建客户端实例
client = MtDBClient(db_configs, warm_up=True, enable_cache=True)

# 执行查询
users = client.query("user_db", "SELECT * FROM users WHERE age > :age", {"age": 18})

# 转换为DataFrame
df = client.query_to_dataframe("user_db", "SELECT * FROM users")

# 导出为CSV
rows = client.export_to_csv(
    "user_db",
    "SELECT id, name, email FROM users",
    "users_export.csv"
)

# 获取表结构
schema = client.get_table_schema("user_db", "users")

# 上下文管理器使用
with MtDBClient(db_configs) as client:
    result = client.query("user_db", "SELECT COUNT(*) FROM users")
    print(f"用户总数: {result[0]['COUNT(*)']}")
```

#### 1.5 常量定义 (constants.py)

```python
SYSTEM_NAME = "coreXAlgo"
DEFAULT_ENCODING = "UTF-8"
MAX_LOG_FILE_SIZE = 10485760  # 10MB
IMAGE_TYPE_FORMAT = ['jpg', 'jpeg', 'png', 'bmp', 'tiff']
TIMEOUT = 5
RETRY_TIMES = 3
```

---

### 二、adv_cv 模块 - 高级计算机视觉

#### 2.1 图像处理功能 (basic.py)

| 函数名 | 功能描述 | 参数说明 |
|--------|---------|---------|
| `ncc_tensor()` | 归一化互相关计算 | x: (M,K)张量, y: (N,K)张量 |
| `apply_clahe()` | 对比度限制的自适应直方图均衡化 | img: 图像, clipLimit: 对比度限制, tileGridSize: 瓦片大小 |

**代码示例**：
```python
from coreXAlgo.adv_cv import ncc_tensor, apply_clahe
import cv2
import torch

# NCC计算
x = torch.randn(100, 256)
y = torch.randn(50, 256)
ncc_result = ncc_tensor(x, y)  # 返回 (100, 50) 维张量

# CLAHE增强
img = cv2.imread('image.jpg')
enhanced = apply_clahe(img, clipLimit=2.0, tileGridSize=(8, 8))
```

---

### 三、file_processing 模块 - 文件处理

#### 3.1 文件操作工具 (basic.py)

| 函数名 | 功能描述 | 特性 |
|--------|---------|------|
| `get_files()` | 查找指定扩展名的文件 | 支持排除目录、递归搜索 |
| `get_filenames()` | 获取文件名（不含路径） | 支持排除目录 |
| `get_duplicate_files()` | 查找重复文件 | 基于文件名匹配 |
| `copy_file()` / `move_file()` | 单文件拷贝/移动 | 支持覆盖、重命名 |
| `copy_files()` / `move_files()` | 批量拷贝/移动 | 支持日志记录、保持目录结构 |
| `randomly_select_files()` | 随机选择文件 | 数据集采样 |

**代码示例**：
```python
from coreXAlgo.file_processing import get_files, copy_files

# 查找图片文件
image_files = get_files('./images', ['.jpg', '.png'],
                        exclude_dirs=['temp', 'cache'])

# 批量拷贝
successful, failed = copy_files(
    file_list=image_files,
    destination_dir='./output',
    overwrite=False,
    create_subdirs=True,
    log_file='copy_log.txt'
)
```

#### 3.2 压缩解压管理 (archive.py)

**ArchiveManager 类特性**：
- 支持多种压缩格式：ZIP、TAR、TAR.GZ、TAR.BZ2、TAR.XZ、GZ、BZ2、XZ、7Z、RAR
- 支持压缩级别设置（0-9）
- 支持排除特定目录和文件扩展名
- 支持密码保护（部分格式）
- 支持进度条显示
- 支持分块处理大文件

**代码示例**：
```python
from coreXAlgo.file_processing import ArchiveManager, CompressionFormat

manager = ArchiveManager(verbose=True)

# 压缩文件夹
manager.compress(
    source='./my_folder',
    output_path='./output.zip',
    format=CompressionFormat.ZIP,
    compression_level=9,
    exclude_dirs=['__pycache__', '.git'],
    exclude_exts=['.log', '.tmp']
)

# 解压文件
manager.extract(
    archive_path='./archive.zip',
    extract_to='./extracted',
    skip_existing=True
)
```

#### 3.3 标注格式转换 (annotation_convert.py)

**支持的标注格式**：
- YOLO格式（目标检测和实例分割）
- LabelMe格式（JSON）
- Pascal VOC格式（XML）

**AnnotationConverter 核心功能**：
- 支持多种标注格式之间的相互转换
- 支持标签映射功能，可以将原始标签映射到目标标签
- 支持批量处理和目录批量转换
- 支持图像尺寸缓存，提高处理效率
- 完善的错误处理和日志记录

**主要类**：

##### YOLOAnnotation
```python
from coreXAlgo.file_processing import YOLOAnnotation

annotator = YOLOAnnotation(['person', 'car', 'bicycle'])

# 添加边界框标注
annotator.add_annotation(0, [0.5, 0.6, 0.1, 0.2])

# 添加分割标注
polygon = [0.45, 0.55, 0.55, 0.55, 0.55, 0.65, 0.45, 0.65]
annotator.add_annotation(2, polygon)

annotator.save('image_001.txt')
```

##### LabelMeAnnotation
```python
from coreXAlgo.file_processing import LabelMeAnnotation

annotator = LabelMeAnnotation("images/001.jpg", (480, 640))

# 添加多边形
annotator.add_shape("person", [[100,100], [200,100], [200,200], [100,200]], "polygon")

# 添加矩形
annotator.add_shape("car", [[50,50], [150,150]], "rectangle")

annotator.save("annotations/001.json")
```

##### VOCAnnotation
```python
from coreXAlgo.file_processing import VOCAnnotation

annotator = VOCAnnotation("images/001.jpg", (640, 480))
annotator.add_object("person", [100, 50, 200, 150])
annotator.add_object("car", [300, 100, 450, 200])
annotator.save("annotations/001.xml")
```

##### AnnotationConverter
```python
from coreXAlgo.file_processing import AnnotationConverter

# 初始化转换器，指定类别列表
converter = AnnotationConverter(['person', 'car', 'dog'])

# VOC 转 YOLO（仅转换在class_names中的标签）
converter.voc_to_yolo_obj('voc/001.xml', 'yolo_labels/001.txt')

# LabelMe 转 YOLO
converter.labelme_to_yolo_obj('labelme/001.json', 'yolo_labels/001.txt')

# YOLO 转 VOC
converter.yolo_obj_to_voc('yolo/001.txt', 'image.jpg', 'voc/001.xml')

# LabelMe 转 VOC
converter.labelme_to_voc('labelme/001.json', 'voc/001.xml')

# 使用标签映射功能
converter_with_mapping = AnnotationConverter(
    class_names=['person', 'animal', 'vehicle'],
    class_mapping={'cat': 'animal', 'dog': 'animal', 'car': 'vehicle', 'bus': 'vehicle'}
)
# 这样会将cat和dog映射为animal，car和bus映射为vehicle
converter_with_mapping.voc_to_yolo_obj('voc/001.xml', 'yolo_labels/001.txt')
```

#### 3.4 图像裁剪处理 (image_crop.py)

**TaggedImageCrop 类特性**：
- 基于VOC标签格式的图像裁剪
- 自动调整标注信息
- 支持保留/丢弃无缺陷区域
- 支持OK/NG图像分开保存
- 支持多种缺陷类型的智能判断策略

**代码示例**：
```python
from coreXAlgo.file_processing import TaggedImageCrop

# 基本用法：仅裁剪有缺陷的区域
processor = TaggedImageCrop(
    retrain_no_detect=False,
    save_dir="./output",
    crop_size=640,
    stride=320
)
stats = processor.crop_image_and_labels("image.jpg", "annotation.xml")

# 高级用法：包含正负样本，分开保存
processor = TaggedImageCrop(
    retrain_no_detect=True,
    separate_ok_ng=True,
    save_dir="./dataset",
    target_size=(2000, 1500),
    crop_size=640,
    stride=320,
    verbose=True
)
stats = processor.crop_image_and_labels("defect_image.jpg", "defect_annotation.xml")
```

**缺陷判断策略**：
- **MP1U, ML3U**: 相对面积 > 30% 或 绝对面积 > 20000
- **MU2U**: 绝对面积 > 40960 且最小尺寸 > 10
- **U4U**: 交集占裁剪块10%以上
- **通用策略**: 多重条件判断（相对面积、裁剪块比例、绝对面积、最小尺寸）

#### 3.5 数据预处理 (data_preprocessing.py)

**YOLODataPreprocessor 类特性**：
- 支持YOLO数据集旋转处理
- 支持多种旋转类型：顺时针90度、逆时针90度、180度旋转
- 支持随机旋转比例功能
- 支持批量处理和多线程加速
- 支持内存优化处理大图像
- 支持单独的图像和标签文件夹

**主要方法**：
| 方法名 | 功能描述 | 参数说明 |
|--------|---------|--------|
| `rotate_yolo_dataset()` | 旋转YOLO数据集 | image_folder: 图片文件夹地址, label_folder: 标签文件夹地址, seed: 随机种子, rotation_type: 旋转类型, ratio: 随机旋转比例, backup: 是否备份原文件, max_workers: 最大线程数 |
| `_rotate_image_and_labels()` | 旋转图片和标签 | image_path: 图片路径, txt_path: 标签路径, rotation_type: 旋转类型, backup_dir: 备份目录 |
| `_rotate_yolo_labels_file()` | 旋转YOLO标签文件 | txt_path: 标签文件路径, rotation_type: 旋转类型 |
| `batch_process()` | 批量处理多个数据集 | process_configs: 配置列表，每个配置包含处理一个数据集所需的参数 |

**代码示例**：
```python
from coreXAlgo.file_processing import YOLODataPreprocessor, RotationType

# 基本用法：旋转整个数据集
preprocessor = YOLODataPreprocessor()
preprocessor.rotate_yolo_dataset(
    image_folder='./images',
    label_folder='./labels',
    seed=42,
    rotation_type=RotationType.CLOCKWISE_90.value,
    ratio=0.8,
    backup=True,
    max_workers=4
)

# 高级用法：批量处理多个数据集
configs = [
    {
        "image_folder": "./dataset1/images",
        "label_folder": "./dataset1/labels",
        "rotation_type": RotationType.CLOCKWISE_90.value,
        "ratio": 0.5,
        "max_workers": 4
    },
    {
        "image_folder": "./dataset2/images",
        "label_folder": "./dataset2/labels",
        "rotation_type": RotationType.ROTATE_180.value,
        "ratio": 0.3,
        "backup": True
    }
]
preprocessor.batch_process(configs)
```

#### 3.6 VOC XML处理 (voc_xml_deal.py)

**VOCXMLProcessor 类特性**：
- 支持批量处理XML文件
- 支持多线程并行处理
- 提供详细的统计分析功能
- 支持类别更新和筛选
- 统一的错误处理和日志记录
- 支持递归搜索目录中的XML文件
- 支持获取按类别分组的图片列表
- 支持获取详细的类别统计信息

**主要方法**：
| 方法名 | 功能描述 | 参数说明 |
|--------|---------|--------|
| `update_categories()` | 更新XML中的类别名称 | xml_path: XML文件路径或目录路径, source_categories: 旧类别列表, target_categories: 新类别列表 |
| `get_images_without_annotations()` | 提取无标注的图片 | xml_path: XML文件路径或目录路径 |
| `get_defect_classes_and_nums()` | 统计缺陷类别及数量 | xml_dir: XML文件目录 |
| `get_images_with_specific_categories()` | 提取包含指定类别的图片 | xml_path: XML文件路径或目录路径, target_categories: 目标类别 |
| `get_all_categories_and_images()` | 解析单个XML文件，返回图片名和类别列表 | xml_path: XML文件路径 |
| `get_all_categories_and_images_batch()` | 批量解析目录中的所有XML文件 | xml_dir: XML文件目录 |
| `get_images_by_category()` | 获取按类别分组的图片列表 | xml_dir: XML文件目录 |
| `get_category_statistics()` | 获取详细的类别统计信息 | xml_dir: XML文件目录 |
| `batch_process()` | 批量处理XML文件 | xml_dir: XML文件目录, process_func: 处理函数, *args: 位置参数, **kwargs: 关键字参数 |
| `batch_process_with_threads()` | 多线程批量处理XML文件 | xml_dir: XML文件目录, process_func: 处理函数, *args: 位置参数, max_workers: 最大线程数, **kwargs: 关键字参数 |
| `get_annotation_statistics()` | 获取标注统计信息 | xml_dir: XML文件目录 |

**代码示例**：
```python
from coreXAlgo.file_processing import VOCXMLProcessor

# 创建处理器实例
processor = VOCXMLProcessor(verbose=True)

# 更新类别名称
processor.update_categories('image.xml', ['PT', 'AB'], ['PT_new', 'AB_new'])

# 统计缺陷类别
stats = processor.get_defect_classes_and_nums('annotations/')
print(stats)  # {'person': 100, 'car': 50, ...}

# 批量处理
xml_files = ['file1.xml', 'file2.xml', 'file3.xml']
results = processor.batch_process_with_threads(
    'annotations/', 
    lambda xml: processor.get_images_with_specific_categories(xml, ['person']),
    max_workers=4
)

# 获取详细统计信息
statistics = processor.get_annotation_statistics('annotations/')
print(statistics)

# 获取按类别分组的图片列表
category_images = processor.get_images_by_category('annotations/')
for category, images in category_images.items():
    print(f"类别: {category}, 图片数量: {len(images)}")

# 获取详细的类别统计信息
category_stats = processor.get_category_statistics('annotations/')
print(f"总类别数: {category_stats['total_categories']}")
print(f"总图片数: {category_stats['total_images']}")
print("类别分布:")
for category, count in category_stats['category_counts'].items():
    print(f"  {category}: {count} 张图片")

# 批量解析目录中的所有XML文件
all_data = processor.get_all_categories_and_images_batch('annotations/')
for xml_path, image_data in all_data.items():
    for image_name, categories in image_data.items():
        print(f"文件: {xml_path}, 图片: {image_name}, 类别: {categories}")
```

---

## 🎯 主要应用场景

### 1. 计算机视觉数据处理
- 图像裁剪和增强
- 标注格式转换（YOLO、LabelMe、VOC）
- 边界框和多边形处理
- CLAHE图像增强

### 2. 文件管理
- 批量文件操作（拷贝、移动、查找）
- 压缩解压（支持多种格式）
- 文件筛选和去重

### 3. 网络传输
- FTP/SFTP文件传输
- 断点续传
- 多线程下载

### 4. 数据可视化
- 目标检测结果可视化
- 边界框、多边形绘制
- 支持快速和高质量两种渲染模式

### 5. 数据集管理
- 标注格式转换
- 图像裁剪和标注调整
- 缺陷统计和分析

---

## 💡 完整使用示例

### 示例1：完整的数据处理流程

```python
from coreXAlgo import utils, file_processing

# 1. 设置随机种子
utils.set_all_seed(42)

# 2. 查找所有图片文件
image_files = file_processing.get_files('./raw_images', ['.jpg', '.png'])

# 3. 批量处理图像
from coreXAlgo.file_processing import TaggedImageCrop

processor = TaggedImageCrop(
    retrain_no_detect=True,
    separate_ok_ng=True,
    save_dir='./processed_dataset',
    crop_size=640,
    stride=320
)

for img_file in image_files:
    xml_file = img_file.replace('.jpg', '.xml')
    if utils.obj_from_yaml is not None:
        stats = processor.crop_image_and_labels(img_file, xml_file)
        print(f"处理完成: {img_file}, NG: {stats['ng_crops']}, OK: {stats['ok_crops']}")

# 4. 压缩处理后的数据
from coreXAlgo.file_processing import ArchiveManager, CompressionFormat

manager = ArchiveManager(verbose=True)
manager.compress(
    source='./processed_dataset',
    output_path='./dataset.zip',
    format=CompressionFormat.ZIP,
    compression_level=9
)

# 5. 上传到服务器
from coreXAlgo.utils import FTPClient

ftp_config = {
    "production": {
        "host": "ftp.server.com",
        "port": 21,
        "username": "user",
        "password": "pass"
    }
}

client = FTPClient(ftp_config, verbose=True)
client.upload_file_visualization("production", "./dataset.zip", "/remote/dataset.zip")
```

### 示例2：标注格式转换

```python
from coreXAlgo.file_processing import AnnotationConverter
import os

# 初始化转换器，指定类别列表
class_names = ['person', 'car', 'bicycle']
converter = AnnotationConverter(class_names)

# 批量转换 VOC 到 YOLO
voc_dir = './voc_annotations'
yolo_dir = './yolo_labels'

# 确保输出目录存在
os.makedirs(yolo_dir, exist_ok=True)

for xml_file in os.listdir(voc_dir):
    if xml_file.endswith('.xml'):
        voc_path = os.path.join(voc_dir, xml_file)
        yolo_path = os.path.join(yolo_dir, xml_file.replace('.xml', '.txt'))
        converter.voc_to_yolo_obj(voc_path, yolo_path)
        print(f"转换完成: {xml_file}")

# 使用标签映射功能进行转换
converter_with_mapping = AnnotationConverter(
    class_names=['person', 'animal', 'vehicle'],
    class_mapping={'cat': 'animal', 'dog': 'animal', 'car': 'vehicle', 'bus': 'vehicle'}
)
# 这样会将cat和dog映射为animal，car和bus映射为vehicle
converter_with_mapping.voc_to_yolo_obj('voc/001.xml', 'yolo_labels/001.txt')
```

### 示例3：目标检测可视化

```python
from coreXAlgo.utils import DetectionVisualizer
import cv2

# 加载图像
image = cv2.imread('test_image.jpg')

# 定义检测结果
detections = [
    {
        'label': 'person',
        'shapeType': 'rectangle',
        'points': [[100, 100], [200, 200]],
        'result': {'confidence': 0.95}
    },
    {
        'label': 'car',
        'shapeType': 'rectangle',
        'points': [[300, 150], [450, 250]],
        'result': {'confidence': 0.87}
    }
]

# 创建可视化器
visualizer = DetectionVisualizer()

# 快速模式（适合实时显示）
result_fast = visualizer.draw_detection_results(image, detections, quality='fast')
cv2.imwrite('result_fast.jpg', result_fast)

# 高质量模式（适合报告展示）
result_hq = visualizer.draw_detection_results(image, detections, quality='high')
cv2.imwrite('result_hq.jpg', result_hq)
```

### 示例4：YOLO数据集旋转

```python
from coreXAlgo.file_processing import YOLODataPreprocessor, RotationType

# 创建预处理器实例
preprocessor = YOLODataPreprocessor(verbose=True)

# 示例1：旋转整个数据集
preprocessor.rotate_yolo_dataset(
    image_folder='./dataset/images',
    label_folder='./dataset/labels',
    seed=42,
    rotation_type=RotationType.CLOCKWISE_90.value,
    ratio=0.8,
    backup=True,
    max_workers=4
)

# 示例2：批量处理多个数据集
configs = [
    {
        "image_folder": "./dataset1/images",
        "label_folder": "./dataset1/labels",
        "rotation_type": RotationType.CLOCKWISE_90.value,
        "ratio": 0.5,
        "max_workers": 4
    },
    {
        "image_folder": "./dataset2/images",
        "label_folder": "./dataset2/labels",
        "rotation_type": RotationType.ROTATE_180.value,
        "ratio": 0.3,
        "backup": True
    },
    {
        "image_folder": "./dataset3/images",
        "label_folder": "./dataset3/labels",
        "rotation_type": RotationType.COUNTERCLOCKWISE_90.value,
        "ratio": 1.0,  # 全部旋转
        "max_workers": 8
    }
]

preprocessor.batch_process(configs)
```

### 示例5：VOC XML处理

```python
from coreXAlgo.file_processing import VOCXMLProcessor

# 创建处理器实例
processor = VOCXMLProcessor(verbose=True)

# 示例1：更新类别名称
processor.update_categories(
    'annotations/image.xml',
    ['old_class1', 'old_class2'],
    ['new_class1', 'new_class2']
)

# 示例2：统计缺陷类别
stats = processor.get_defect_classes_and_nums('annotations/')
print("缺陷类别统计:")
for class_name, count in stats.items():
    print(f"  {class_name}: {count}")

# 示例3：提取无标注的图片
empty_files = processor.batch_process(
    'annotations/',
    processor.get_images_without_annotations
)
print(f"无标注的图片: {empty_files}")

# 示例4：多线程批量处理
import time

start_time = time.time()

# 定义处理函数
def process_xml(xml_path):
    # 提取包含特定类别的图片
    result = processor.get_images_with_specific_categories(xml_path, ['person', 'car'])
    return result

# 多线程处理
results = processor.batch_process_with_threads(
    'annotations/',
    process_xml,
    max_workers=4
)

end_time = time.time()
print(f"处理时间: {end_time - start_time:.2f}秒")
print(f"包含特定类别的图片: {results}")

# 示例5：获取详细统计信息
annotation_stats = processor.get_annotation_statistics('annotations/')
print("\n标注统计信息:")
print(f"总文件数: {annotation_stats['total_files']}")
print(f"总对象数: {annotation_stats['total_objects']}")
print(f"平均每文件对象数: {annotation_stats['avg_objects_per_file']:.2f}")
print("类别分布:")
for class_name, count in annotation_stats['class_counts'].items():
    print(f"  {class_name}: {count}")
print(f"无标注文件数: {len(annotation_stats['empty_files'])}")

# 示例6：获取按类别分组的图片列表
category_images = processor.get_images_by_category('annotations/')
print("\n按类别分组的图片:")
for category, images in category_images.items():
    print(f"  {category}: {len(images)} 张图片")

# 示例7：获取详细的类别统计信息
category_stats = processor.get_category_statistics('annotations/')
print("\n详细类别统计:")
print(f"总类别数: {category_stats['total_categories']}")
print(f"总图片数: {category_stats['total_images']}")
print("类别分布:")
for category, count in category_stats['category_counts'].items():
    print(f"  {category}: {count} 张图片")

# 示例8：批量解析目录中的所有XML文件
all_data = processor.get_all_categories_and_images_batch('annotations/')
print("\n批量解析结果:")
for xml_path, image_data in all_data.items():
    for image_name, categories in image_data.items():
        print(f"  文件: {xml_path}, 图片: {image_name}, 类别: {categories}")

---

## ✨ 项目特点总结

### 1. 模块化设计
- 清晰的模块划分（utils、adv_cv、file_processing）
- 每个模块职责明确，易于维护和扩展
- 模块间依赖关系清晰

### 2. 完善的文档
- 每个函数都有详细的文档字符串
- 包含丰富的使用示例
- 参数说明清晰完整

### 3. 错误处理
- 完善的异常处理机制
- 详细的错误日志记录
- 自动重试机制（网络传输）

### 4. 进度可视化
- 使用 tqdm 提供进度条显示
- 支持自定义回调函数
- 实时反馈处理进度

### 5. 类型提示
- 使用 Python 类型注解
- 提高代码可读性
- 便于 IDE 智能提示

### 6. 多线程支持
- 支持多线程并行处理
- 提高批量操作效率
- 线程池管理

### 7. 生产级质量
- 代码规范统一
- 测试覆盖完善
- 性能优化到位

---

## 📊 技术栈

| 类别 | 技术/库 |
|------|---------|
| **图像处理** | OpenCV, NumPy |
| **深度学习** | PyTorch |
| **进度显示** | tqdm |
| **XML处理** | lxml, xml.etree.ElementTree |
| **几何计算** | shapely |
| **网络传输** | paramiko (SFTP), ftplib (FTP), mt_file_downloader (多线程下载) |
| **数据库** | SQLAlchemy |
| **数据格式** | JSON, YAML, Pickle |
| **压缩格式** | zipfile, tarfile, py7zr, rarfile |
| **并发处理** | concurrent.futures |
| **路径处理** | pathlib |
| **类型注解** | typing |
| **枚举常量** | enum |

---

## 📝 代码质量评估

| 评估项 | 评分 | 说明 |
|--------|------|------|
| **代码规范** | ⭐⭐⭐⭐⭐ | 遵循 PEP 8 规范 |
| **文档完整性** | ⭐⭐⭐⭐⭐ | 每个函数都有详细文档，包含使用示例 |
| **错误处理** | ⭐⭐⭐⭐⭐ | 完善的异常处理机制，自定义异常类 |
| **可维护性** | ⭐⭐⭐⭐⭐ | 模块化设计，易于维护，统一的代码风格 |
| **可扩展性** | ⭐⭐⭐⭐⭐ | 清晰的接口设计，支持功能扩展 |
| **性能优化** | ⭐⭐⭐⭐⭐ | 支持多线程、内存优化、向量化操作 |
| **测试覆盖** | ⭐⭐⭐⭐⭐ | 包含丰富的使用示例，覆盖各种场景 |
| **类型安全** | ⭐⭐⭐⭐⭐ | 全面的类型注解，提高代码可读性 |
| **路径处理** | ⭐⭐⭐⭐⭐ | 使用 pathlib 统一路径处理 |
| **日志管理** | ⭐⭐⭐⭐⭐ | 统一的日志记录机制，替换 print 语句 |

---

## 🎓 学习价值

这个项目非常适合学习以下内容：

1. **Python 项目架构设计**
   - 模块化设计原则
   - 包管理和导入机制
   - 代码组织最佳实践

2. **计算机视觉数据处理**
   - 图像预处理技术
   - 标注格式转换
   - 边界框和多边形处理

3. **文件操作和压缩**
   - 批量文件处理
   - 多种压缩格式支持
   - 进度条实现

4. **网络编程**
   - FTP/SFTP 协议实现
   - 断点续传机制
   - 多线程下载

5. **代码质量提升**
   - 文档字符串编写
   - 类型注解使用
   - 错误处理模式

---

## 🚀 推荐使用场景

1. **目标检测项目**
   - 数据集准备和标注转换
   - 图像裁剪和增强
   - 结果可视化

2. **图像分割项目**
   - 标注格式转换
   - 多边形处理
   - 掩码操作

3. **数据管道构建**
   - 文件批量处理
   - 数据上传下载
   - 压缩解压管理

4. **工业缺陷检测**
   - 缺陷标注处理
   - 图像裁剪和分类
   - 数据统计分析

5. **跨版本Python环境**
   - Python 3.8+ 兼容性支持
   - 旧版本库兼容性修复

## 📝 Python 3.8 兼容性说明

为确保在Python 3.8及以上版本的兼容性，项目做了以下调整：

1. **类型注解兼容性**
   - 为 `TypedDict` 提供了 `typing_extensions` 回退支持
   - 为 `Literal` 类型添加了兼容性处理

2. **语法兼容性**
   - 替换了 walrus 运算符 (`:=`) 为传统 if 语句
   - 确保所有语法特性兼容Python 3.8

3. **库版本兼容性**
   - 修复了 SQLAlchemy 导入路径，支持旧版本
   - 修复了 Paramiko 版本兼容性问题

4. **依赖管理**
   - 为可选依赖项提供了优雅的降级处理
   - 确保核心功能在最低支持版本上正常工作

---

## 📚 总结

**coreXAlgo** 是一个功能丰富、设计优秀的 Python 工具库，专注于计算机视觉和数据处理领域。它提供了从文件管理、标注转换到图像处理、可视化的完整工具链，代码质量高，文档完善，可以直接集成到各种项目中使用。

**核心优势**：
- ✅ 功能全面，覆盖计算机视觉数据处理的主要场景
- ✅ 代码质量高，遵循最佳实践
- ✅ 文档完善，易于上手
- ✅ 性能优化，支持多线程和断点续传
- ✅ 生产级质量，可直接用于实际项目

**适用人群**：
- 计算机视觉工程师
- 数据科学家
- 深度学习研究者
- Python 开发者

这个工具库特别适合用于目标检测、图像分割等计算机视觉项目的数据预处理和标注管理工作，是一个值得学习和使用的优秀开源项目。

---

## 📋 版本更新日志

### 版本 0.4.9

**核心功能优化**：
1. 修复了 `sftp_client.py` 中下载成功数量统计错误的问题，确保下载结果正确显示
2. 优化了 `sftp_client.py` 的异常处理逻辑，统一处理各种异常情况
3. 为 `mt_file_downloader.py` 添加了缺失的 `logging` 模块导入
4. 改进了 `sftp_client.py` 的连接池管理，实现线程安全的连接池
5. 优化了 `sftp_client.py` 的文件完整性验证，支持 MD5/SHA1 哈希校验

**文档更新**：
1. 同步更新了 `source/utils/mt_file_downloader.md` 和 `source/utils/sftp_client.md` 文档
2. 确保文档与代码保持一致

**配置文件**：
1. 更新了版本号

### 版本 0.4.8

**核心功能优化**：
1. 重构了文件处理模块，提升了 annotation_convert.py 和 archive.py 的性能
2. 优化了工具模块，包括 bbox_util.py、ftp_client.py 和 sftp_client.py
3. 新增了 mt_file_downloader.py 模块，替换了旧的 mt_ftp_downloader.py
4. 改进了数据库客户端 mt_db_client.py 的查询性能和错误处理
5. 更新了版本号

**文档更新**：
1. 同步更新了所有模块的文档文件
2. 优化了文档结构和内容
3. 确保文档与代码保持一致

**配置文件**：
1. 更新了项目配置文件，确保构建和部署的稳定性

### 版本 0.4.7

- 修复了 SQLAlchemy 版本兼容性问题
- 优化了 FTP/SFTP 客户端的错误处理
- 改进了目标检测可视化的性能

### 版本 0.4.6

- 初始版本发布
- 包含核心工具模块、高级计算机视觉模块和文件处理模块
