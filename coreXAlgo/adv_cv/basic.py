__all__ = ['ncc_tensor']


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
