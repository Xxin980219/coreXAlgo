# Data_preprocessing

YOLO数据预处理

## 核心功能

- **数据增强**：支持多种数据增强技术，如旋转、翻转、缩放等
- **旋转增强**：支持多种旋转类型，包括随机角度、90度倍数等
- **批量处理**：支持批量处理YOLO格式的数据集

## 使用示例

### YOLO数据预处理

```python
from coreXAlgo.file_processing import YOLODataPreprocessor, RotationType

# 创建数据预处理实例
preprocessor = YOLODataPreprocessor(
    image_dir='images/',
    label_dir='labels/',
    output_dir='output/',
    rotation_type=RotationType.RANDOM,
    max_rotation_angle=45,
    flip_horizontal=True,
    flip_vertical=False,
    scale_range=(0.8, 1.2)
)

# 执行数据预处理
preprocessor.process()
print(f"Processed {len(preprocessor.processed_images)} images")
```

### 使用不同的旋转类型

```python
from coreXAlgo.file_processing import YOLODataPreprocessor, RotationType

# 使用90度倍数旋转
preprocessor = YOLODataPreprocessor(
    image_dir='images/',
    label_dir='labels/',
    output_dir='output_90/',
    rotation_type=RotationType.MULTIPLE_OF_90
)

preprocessor.process()
print(f"Processed {len(preprocessor.processed_images)} images with 90-degree rotations")
```

### API 参考

```{eval-rst}
.. automodule:: coreXAlgo.file_processing.data_preprocessing
   :members:
   :undoc-members:
   :show-inheritance:
```