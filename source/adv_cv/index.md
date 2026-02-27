# Adv_cv Module

<div class="module-header">
  <div class="module-content">
    <h1>Adv_cv Module</h1>
    <p class="module-description">高级计算机视觉模块</p>
    <p class="module-detail">集成了算法开发中常用的计算机视觉技术和处理方法，以及对CV库部分常用函数的改进版</p>
  </div>
</div>

<style>
  .module-header {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    padding: 1.5rem;
    border-radius: 8px;
    margin-bottom: 1.5rem;
    color: white;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }
  
  .module-content {
    max-width: 800px;
    margin: 0 auto;
  }
  
  .module-content h1 {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    font-weight: bold;
  }
  
  .module-description {
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
    opacity: 0.9;
  }
  
  .module-detail {
    font-size: 0.9rem;
    opacity: 0.8;
  }
  
  .component-card {
    border-radius: 8px;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    border: 1px solid #e9ecef;
  }
  
  .component-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
  }
  
  .component-icon {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
  }
</style>

## 📋 模块概览

**Adv_cv** 模块提供了一系列高级计算机视觉处理功能，旨在简化算法开发过程中的常见视觉任务。该模块包含了对OpenCV等库函数的改进实现，以及一些专门针对算法开发场景的自定义功能。

## 🚀 核心功能

- **图像处理**：图像增强、预处理、变换
- **特征提取**：边缘检测、特征点提取
- **归一化**：归一化互相关计算
- **直方图处理**：对比度限制的自适应直方图均衡化

## 📁 组件列表

::::{grid} 2 2 2 3
:gutter: 2
:padding: 1

:::{grid-item-card} {octicon}`codescan` Basic
:link: basic
:link-type: doc
:class-card: component-card

**基础函数**

提供核心的计算机视觉处理函数，包括归一化互相关计算和对比度限制的自适应直方图均衡化等基础功能。
:::

::::

## 🔧 使用示例

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

## 🎯 应用场景

- **目标检测**：特征匹配、模板匹配
- **图像增强**：对比度调整、直方图均衡化
- **模式识别**：特征提取、相似度计算
- **工业视觉**：缺陷检测、质量控制

## 📚 相关资源

- [OpenCV 官方文档](https://docs.opencv.org/)
- [PyTorch 计算机视觉教程](https://pytorch.org/tutorials/intermediate/torchvision_tutorial.html)
- [计算机视觉算法原理](https://github.com/topics/computer-vision)

```{toctree}
:caption: adv_cv
:hidden:

basic
```
