# Image_crop

图像裁剪

## 核心功能

- **边界框调整**：根据目标图像尺寸调整边界框坐标
- **滑动窗口裁剪**：使用滑动窗口方式裁剪图像
- **标签图像裁剪**：支持带标注的图像裁剪
- **多线程批量裁剪**：使用多线程提高批量裁剪效率

## 使用示例

### 滑动窗口裁剪

```python
from coreXAlgo.file_processing import sliding_crop_image

# 滑动窗口裁剪图像
crop_images = sliding_crop_image(
    'input.jpg',
    crop_size=(512, 512),
    overlap=0.2,
    output_dir='crops/'
)
print(f"Generated {len(crop_images)} crop images")
```

### 带标签的图像裁剪

```python
from coreXAlgo.file_processing import TaggedImageCrop

# 创建带标签的图像裁剪实例
cropper = TaggedImageCrop(
    image_path='input.jpg',
    annotation_path='annotation.xml',
    crop_size=(512, 512),
    overlap=0.2,
    output_dir='crops/',
    annotation_format='voc'
)

# 执行裁剪
cropper.crop()
print(f"Generated {len(cropper.crop_images)} crop images with annotations")
```

### 多线程批量裁剪

```python
from coreXAlgo.file_processing import batch_multithreaded_image_cropping

# 批量多线程裁剪图像
image_annotation_pairs = [
    ('image1.jpg', 'annotation1.xml'),
    ('image2.jpg', 'annotation2.xml')
]

crop_results = batch_multithreaded_image_cropping(
    image_annotation_pairs,
    crop_size=(512, 512),
    overlap=0.2,
    output_dir='crops/',
    annotation_format='voc',
    max_workers=4
)
print(f"Processed {len(crop_results)} image-annotation pairs")
```

### 边界框调整

```python
from coreXAlgo.file_processing import resize_box_to_target

# 调整边界框坐标
original_box = [x1, y1, x2, y2]  # 原始边界框坐标
original_size = (original_width, original_height)  # 原始图像尺寸
target_size = (target_width, target_height)  # 目标图像尺寸

resized_box = resize_box_to_target(original_box, original_size, target_size)
print(f"Resized box: {resized_box}")
```

```{eval-rst}
.. automodule:: coreXAlgo.file_processing.image_crop
   :members:
   :undoc-members:
   :show-inheritance:
```