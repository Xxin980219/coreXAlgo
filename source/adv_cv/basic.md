# Basic

基础函数

## 核心功能

- **NCC 模板匹配**：使用张量计算优化的归一化互相关模板匹配算法
- **CLAHE 图像增强**：应用对比度受限的自适应直方图均衡化，增强图像对比度

## 使用示例

### NCC 模板匹配

```python
import cv2
import numpy as np
from coreXAlgo.adv_cv import ncc_tensor

# 读取图像和模板
image = cv2.imread('image.jpg', 0)
template = cv2.imread('template.jpg', 0)

# 执行模板匹配
result = ncc_tensor(image, template)

# 找到最佳匹配位置
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
top_left = max_loc
bottom_right = (top_left[0] + template.shape[1], top_left[1] + template.shape[0])

# 绘制匹配结果
cv2.rectangle(image, top_left, bottom_right, 255, 2)
cv2.imshow('Matching Result', image)
cv2.waitKey(0)
cv2.destroyAllWindows()
```

### CLAHE 图像增强

```python
import cv2
from coreXAlgo.adv_cv import apply_clahe

# 读取图像
image = cv2.imread('image.jpg')

# 应用 CLAHE 增强
enhanced_image = apply_clahe(image)

# 显示结果
cv2.imshow('Original', image)
cv2.imshow('Enhanced', enhanced_image)
cv2.waitKey(0)
cv2.destroyAllWindows()
```

## API 参考

```{eval-rst}
.. automodule:: coreXAlgo.adv_cv.basic
   :members:
   :undoc-members:
   :show-inheritance:
```