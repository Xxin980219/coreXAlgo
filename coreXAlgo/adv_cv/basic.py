def ncc_tensor(x, y):
    """
    两个张量之间的归一化互相关计算（功能类似于 cv2.TM_CCOEFF_NORMED）

    Args:
        x: (M, K) 维张量
        y: (N, K) 维张量

    Returns:
        (M, N) 维张量，数值范围在 [-1, 1] 之间
    """
    import torch

    # 对x和y进行零均值化（减去均值）
    x = x - x.mean(dim=-1, keepdim=True)
    y = y - y.mean(dim=-1, keepdim=True)

    # 计算分子部分：x和y的互相关
    numerator = torch.einsum('ij,kj->ik', x, y)

    # 计算分母部分（保持数值稳定性）
    x_norm = torch.norm(x, p=2, dim=-1)  # 计算x的L2范数
    y_norm = torch.norm(y, p=2, dim=-1)  # 计算y的L2范数
    denominator = torch.outer(x_norm, y_norm).clamp_min(1e-7)  # 外积并设置最小值避免除零

    # 返回归一化结果，并限制在[-1, 1]范围内
    return (numerator / denominator).clamp_(-1, 1)


def apply_clahe(img, clipLimit, tileGridSize):
    """
    对单通道灰度图像和三通道彩色图像进行对比度限制的自适应直方图均衡化（CLAHE）处理

    CLAHE（Contrast Limited Adaptive Histogram Equalization）是一种改进的直方图均衡化算法，
    通过限制对比度增强来避免噪声放大，特别适用于医学图像、遥感图像等对比度较低的图像增强。

    Args:
        img (numpy.ndarray): 输入图像，支持灰度图（单通道）或彩色图（三通道BGR格式）
        clipLimit (float): 对比度限制阈值，用于限制直方图的裁剪
            - 较低值（1.0-2.0）：对比度增强较温和，避免噪声放大
            - 较高值（3.0-4.0）：对比度增强较强，可能引入噪声
        tileGridSize (Tuple[int, int]): 图像分割的瓦片大小，格式为(rows, cols)
            - 较小值（如(4,4)）：局部细节增强更明显，但可能产生块状效应
            - 较大值（如(16,16)）：增强效果更平滑，但局部对比度提升有限

    Returns:
        numpy.ndarray: 增强后的图像，保持与输入相同的通道数和数据类型

    Example:
        >>> # 处理灰度图像
        >>> gray_img = cv2.imread('gray_image.png', cv2.IMREAD_GRAYSCALE)
        >>> enhanced_gray = apply_clahe(gray_img, clipLimit=2.0, tileGridSize=(8, 8))
        >>>
        >>> # 处理彩色图像
        >>> color_img = cv2.imread('color_image.jpg')
        >>> enhanced_color = apply_clahe(color_img, clipLimit=3.0, tileGridSize=(4, 4))
    """
    import cv2
    global enhanced_img
    if len(img.shape) == 2:  # 单通道灰度图像
        clahe = cv2.createCLAHE(clipLimit=clipLimit, tileGridSize=tileGridSize)
        enhanced_img = clahe.apply(img)
        enhanced_img = cv2.cvtColor(enhanced_img, cv2.COLOR_GRAY2BGR)
    elif len(img.shape) == 3:  # 三通道彩色图像
        # 分离通道
        b, g, r = cv2.split(img)
        # 对每个通道分别应用 CLAHE
        clahe = cv2.createCLAHE(clipLimit=clipLimit, tileGridSize=tileGridSize)
        enhanced_b = clahe.apply(b)
        enhanced_g = clahe.apply(g)
        enhanced_r = clahe.apply(r)
        # 合并通道
        enhanced_img = cv2.merge((enhanced_b, enhanced_g, enhanced_r))
    return enhanced_img
