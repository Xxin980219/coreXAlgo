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
import cv2

# 读取图像
image = cv2.imread('input.jpg')

# 滑动窗口裁剪图像
crops = sliding_crop_image(
    image,
    crop_size=512,
    stride=320
)
print(f"生成了 {len(crops)} 个裁剪图像块")

# 访问裁剪块
for i, (crop_img, x, y) in enumerate(crops):
    cv2.imwrite(f'crop_{i}.jpg', crop_img)
    print(f"裁剪块 {i}: 位置 ({x}, {y})")
```

### 带标签的图像裁剪

```python
from coreXAlgo.file_processing import TaggedImageCrop

# 创建带标签的图像裁剪实例
processor = TaggedImageCrop(
    retrain_no_detect=True,
    separate_ok_ng=True,
    save_dir='crops/',
    target_size=(2000, 1500),
    crop_size=640,
    stride=320,
    separate_images_xml=True,
    generate_ok_xml=True,
    verbose=True
)

# 执行裁剪
stats = processor.crop_image_and_labels('input.jpg', 'annotation.xml')
print(f"总裁剪块: {stats['total_crops']}, 有目标块: {stats['ng_crops']}, 无目标块: {stats['ok_crops']}")
```

### 多线程批量裁剪

```python
from coreXAlgo.file_processing import TaggedImageCrop, batch_multithreaded_image_cropping

# 创建裁剪处理器
processor = TaggedImageCrop(
    retrain_no_detect=True,
    separate_ok_ng=True,
    save_dir='crops/',
    crop_size=640,
    stride=320,
    separate_images_xml=True,
    generate_ok_xml=True
)

# 批量多线程裁剪图像
image_paths = ['image1.jpg', 'image2.jpg', 'image3.jpg']

# 执行批量处理
stats = batch_multithreaded_image_cropping(
    image_paths,
    processor,
    max_workers=4,
    verbose=True
)
print(f"成功处理: {stats['success_count']}/{stats['total_images']} 张图片")
print(f"总裁剪块: {stats['total_crops']}, 有目标块: {stats['total_ng']}, 无目标块: {stats['total_ok']}")
```

### 边界框调整

```python
from coreXAlgo.file_processing import resize_box_to_target

# 调整边界框坐标
original_box = [100, 50, 200, 150]  # 原始边界框坐标
original_size = (1600, 1200)  # 原始图像尺寸
target_size = (800, 600)  # 目标图像尺寸

resized_box = resize_box_to_target(original_box, target_size, original_size)
print(f"调整后的边界框: {resized_box}")
```

## API 参考

```{eval-rst}
.. automodule:: coreXAlgo.file_processing.image_crop
   :members:
   :show-inheritance:
```