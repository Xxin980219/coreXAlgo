"""高级计算机视觉模块

提供高级图像处理算法和函数，包括：
- ncc_tensor：归一化互相关张量计算
- apply_clahe：应用对比度受限的自适应直方图均衡化
"""
from .basic import ncc_tensor, apply_clahe

basic_all = ["ncc_tensor", "apply_clahe"]

__all__ = basic_all
