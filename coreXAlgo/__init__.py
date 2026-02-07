"""CoreXAlgo 核心算法库

本库提供了多种算法和工具，包括：
- 文件处理（file_processing）：数据预处理、标注转换、XML处理等
- 高级计算机视觉（adv_cv）：图像处理算法
- 工具函数（utils）：日志、FTP/SFTP客户端、数据库客户端等

版本信息：__version__
"""
from .version import __version__
from . import utils, adv_cv, file_processing

__all__ = [
    '__version__',
    *adv_cv.__all__,
    *file_processing.__all__,
    *utils.__all__,
]
