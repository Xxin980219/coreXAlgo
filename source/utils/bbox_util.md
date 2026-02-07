# Bbox_util

边界框处理和可视化

## 核心功能

- **多边形处理**：将多边形转换为边界框、将轮廓转换为多边形、将掩码转换为多边形
- **边界框合并**：支持多种合并算法，包括基于扩展的合并、基于多条件的合并、基于相邻关系的合并
- **目标检测可视化**：支持快速模式（OpenCV）和高质量模式（Matplotlib）的检测结果可视化
- **智能标签位置**：根据形状位置自动调整标签显示位置，避免遮挡
- **自适应参数**：根据图像尺寸自动调整线宽、字体大小等参数
- **多形状支持**：支持矩形框、线段、多边形等多种形状的绘制

## 使用示例

### 多边形处理

```python
from coreXAlgo.utils import polygon_to_bbox, mask_to_polygon
import numpy as np

# 多边形转边界框
polygon = [10, 10, 50, 10, 50, 50, 10, 50]
bbox = polygon_to_bbox(polygon)
print(bbox)  # 输出: [10, 10, 50, 50]

# 掩码转多边形
mask = np.zeros((100, 100), dtype=np.uint8)
mask[20:80, 20:80] = 1  # 创建一个方形区域
polygon = mask_to_polygon(mask)
print(f"多边形坐标长度: {len(polygon)}")
```

### 边界框合并

```python
from coreXAlgo.utils import merge_boxes_by_conditions

# 定义检测框（格式：[置信度, 左, 上, 右, 下]）
detections = [
    [0.9, 10, 10, 50, 50],
    [0.8, 30, 30, 70, 70],
    [0.7, 100, 100, 150, 150]
]

# 合并重叠和邻近的框
merged = merge_boxes_by_conditions(detections, merge_threshold=50, touching_threshold=5)
print(f"合并前: {len(detections)} 个框")
print(f"合并后: {len(merged)} 个框")
for box in merged:
    print(f"  置信度: {box[0]:.2f}, 框: {box[1:]}")
```

### 目标检测可视化

```python
from coreXAlgo.utils import DetectionVisualizer
import cv2

# 读取图像
image = cv2.imread('image.jpg')

# 定义检测结果（新格式）
detections = [
    {'label': 'person', 'shapeType': 'rectangle', 'points': [[50, 50], [150, 150]], 'result': {'confidence': 0.95}},
    {'label': 'car', 'shapeType': 'rectangle', 'points': [[200, 100], [350, 200]], 'result': {'confidence': 0.87}},
    {'label': 'line', 'shapeType': 'line', 'points': [[100, 100], [200, 200]], 'result': {'confidence': 0.9}},
    {'label': 'polygon', 'shapeType': 'polygon', 'points': [[300, 300], [400, 300], [350, 400]], 'result': {'confidence': 0.85}}
]

# 创建可视化器实例
visualizer = DetectionVisualizer()

# 快速模式可视化（OpenCV）
result_fast = visualizer.visualize(image, detections, mode='fast')
cv2.imshow('Fast Mode', result_fast)

# 高质量模式可视化（Matplotlib）
result_hq = visualizer.visualize(image, detections, mode='high')
cv2.imshow('High Quality Mode', result_hq)

cv2.waitKey(0)
cv2.destroyAllWindows()

# 保存可视化结果
visualizer.visualize(image, detections, mode='high', output_path='result.jpg')
```

### 兼容旧格式的可视化

```python
from coreXAlgo.utils import DetectionVisualizer
import cv2

# 读取图像
image = cv2.imread('image.jpg')

# 旧格式检测结果（[标签, 置信度, 左, 上, 右, 下]）
old_format_detections = [
    ['person', 0.95, 50, 50, 150, 150],
    ['car', 0.87, 200, 100, 350, 200]
]

# 使用兼容方法
visualizer = DetectionVisualizer()
result = visualizer.draw_bounding_boxes(image, old_format_detections, mode='high')
cv2.imshow('Old Format Visualization', result)
cv2.waitKey(0)
cv2.destroyAllWindows()
```

### API 参考

```{eval-rst}
.. automodule:: coreXAlgo.utils.bbox_util
   :members:
   :undoc-members:
   :show-inheritance:
```