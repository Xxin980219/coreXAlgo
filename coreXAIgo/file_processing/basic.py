import shutil
import time
import zipfile
from typing import Optional, Union, List, Set
import os
from tqdm import tqdm

from ..utils import set_logging

logger = set_logging(__name__)

__all__ = ['get_files', 'extract_large_zip', 'zip_folder']


def get_files(directory: str, extensions: Union[str, List[str]] = '.jpg',
              exclude_dirs: Union[str, List[str]] = None) -> List[str]:
    """
    查找指定目录下所有匹配给定扩展名的文件路径

    Args:
        directory: 要搜索的目录路径
        extensions: 要匹配的文件扩展名，可以是单个字符串（如 '.jpg'）或列表（如 ['.jpg', '.png']）
        exclude_dirs: 要排除的目录名，可以是单个字符串或列表（支持相对路径或绝对路径）

    Returns:
        匹配文件的完整路径列表（按字母顺序排序）

    Example:
        >>> # 基本用法：查找所有jpg文件
        >>> jpg_files = get_files('./images', '.jpg')
        >>> print(f"找到 {len(jpg_files)} 个JPG文件")
        >>>
        >>> # 查找多种图片格式
        >>> image_files = get_files('./photos', ['.jpg', '.jpeg', '.png', '.gif'])
        >>> for file in image_files:
        >>>     print(file)
        >>>
        >>> # 排除缓存和临时目录
        >>> data_files = get_files('./data', '.csv',
        >>>                      exclude_dirs=['temp', 'cache', 'backup'])
        >>>
        >>> # 排除嵌套目录（相对路径）
        >>> config_files = get_files('/etc/app', '.conf',
        >>>                        exclude_dirs=['logs/old', 'tmp/sessions'])
        >>>
        >>> # 查找所有Python文件，排除测试和文档目录
        >>> python_files = get_files('./src', '.py',
        >>>                        exclude_dirs=['tests', 'docs', '__pycache__'])

    Notes:
        - 扩展名匹配不区分大小写（.JPG 和 .jpg 都会被匹配）
        - 排除目录基于名称匹配，区分大小写
        - 返回的路径是文件的绝对路径
        - 如果extensions为None或空列表，则匹配所有文件类型
    """
    # 参数验证
    if not os.path.isdir(directory):
        raise ValueError(f"无效的目录路径: {directory}")

    if not isinstance(extensions, (str, list)):
        raise TypeError("扩展名参数必须是字符串或列表")

        # 处理排除目录参数
    if exclude_dirs is None:
        exclude_dirs = []
    elif isinstance(exclude_dirs, str):
        exclude_dirs = [exclude_dirs]
    elif not isinstance(exclude_dirs, list):
        raise TypeError("排除目录参数必须是字符串、列表或None")

    # 统一处理扩展名格式
    if isinstance(extensions, str):
        extensions = [extensions]

    # 确保扩展名以点开头
    extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]

    # 规范化排除目录路径，确保正确比较
    normalized_exclude_dirs = []
    for exclude_dir in exclude_dirs:
        # 如果是相对路径，转换为绝对路径
        if not os.path.isabs(exclude_dir):
            exclude_dir = os.path.abspath(os.path.join(directory, exclude_dir))
        normalized_exclude_dirs.append(os.path.normpath(exclude_dir))

    # 使用生成器表达式提高内存效率
    file_paths = []
    for root, dirs, files in os.walk(directory):
        # 检查当前目录是否在排除列表中
        current_dir_abs = os.path.abspath(root)
        if any(os.path.samefile(current_dir_abs, exclude_dir) for exclude_dir in normalized_exclude_dirs):
            # 跳过排除目录及其所有子目录
            dirs[:] = []
            continue

        # 检查当前目录的父目录是否在排除列表中（防止遍历到排除目录的子目录）
        for exclude_dir in normalized_exclude_dirs:
            if current_dir_abs.startswith(exclude_dir + os.sep):
                dirs[:] = []
                continue

        # 收集匹配的文件
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_paths.append(os.path.join(root, file))

    # 返回排序后的列表以便可预测的顺序
    return sorted(file_paths)


def extract_large_zip(zip_path: str, extract_to: str, chunk_size: int = 8192, skip_existing: bool = True):
    """
    高效解压大ZIP文件

    Args:
        zip_path: ZIP文件路径
        extract_to: 解压目标目录（如果不存在会自动创建）
        chunk_size: 解压缓冲区大小（字节），默认为8KB。处理大文件时可增大此值（如81920）
        skip_existing: 是否跳过已存在的文件，避免重复解压

    Example:
        >>> # 基本用法：解压到当前目录下的output文件夹
        >>> extract_large_zip('large_archive.zip', './output')
        >>>
        >>> # 解压到指定目录，跳过已存在文件（默认行为）
        >>> extract_large_zip('/backup/data.zip', '/home/user/extracted_data')
        >>>
        >>> # 强制重新解压（覆盖已存在文件），使用更大的缓冲区
        >>> extract_large_zip('big_file.zip', './data',
        >>>                  chunk_size=65536,  # 64KB缓冲区
        >>>                  skip_existing=False)  # 覆盖现有文件
        >>>
        >>> # 处理非常大的压缩文件（如图片库备份）
        >>> extract_large_zip('photos_backup.zip', '/media/external_drive/photos',
        >>>                  chunk_size=131072)  # 128KB缓冲区

    Notes:
        - 对于特别大的ZIP文件（GB级别），建议增大chunk_size到64KB或128KB以提高性能
    """
    # 验证ZIP文件
    if not os.path.isfile(zip_path):
        raise FileNotFoundError(f"ZIP文件不存在: {zip_path}")

    # 创建目标目录
    os.makedirs(extract_to, exist_ok=True)
    logger.info(f"准备解压: {zip_path} → {extract_to}")

    # 打开ZIP文件
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 获取文件列表并过滤目录
            file_list = [f for f in zip_ref.namelist() if not f.endswith('/')]
            total_size = sum(zip_ref.getinfo(f).file_size for f in file_list)

            # 带进度条解压
            with tqdm(
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    desc=f"解压 {os.path.basename(zip_path)}"
            ) as pbar:
                for file in file_list:
                    try:
                        # 检查文件是否已存在
                        dest_path = os.path.join(extract_to, file)
                        if skip_existing and os.path.exists(dest_path):
                            file_size = zip_ref.getinfo(file).file_size
                            pbar.update(file_size)
                            continue

                        # 确保目标目录存在
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                        # 分块解压大文件
                        with zip_ref.open(file) as src, open(dest_path, 'wb') as dst:
                            while True:
                                chunk = src.read(chunk_size)
                                if not chunk:
                                    break
                                dst.write(chunk)
                                pbar.update(len(chunk))

                    except Exception as e:
                        logger.error(f"❌ 解压失败: {file} - {str(e)}")
                        if os.path.exists(dest_path):
                            os.remove(dest_path)

    except zipfile.BadZipFile as e:
        logger.error(f"❌ ZIP文件损坏: {zip_path} - {str(e)}")
        raise
    except Exception as e:
        logger.error(f"❌ 解压过程中发生错误: {str(e)}")
        raise

    logger.info(f"✅ 解压完成: {extract_to}")


def zip_folder(folder_path: str, output_path: str, compression_level: int = 9,
               exclude_dirs: Optional[list] = None,
               exclude_exts: Optional[list] = None,
               show_progress: bool = True
               ) -> None:
    """
    高效压缩文件夹为ZIP文件

    Args:
        folder_path: 要压缩的文件夹路径
        output_path: 输出的ZIP文件路径
        compression_level: 压缩级别（0-9，0=不压缩/最快，9=最大压缩/最慢）
        exclude_dirs: 要排除的目录名列表
        exclude_exts: 要排除的文件扩展名列表
        show_progress: 是否显示进度条

    Example:
        >>> # 基本用法：压缩当前目录到archive.zip
        >>> zip_folder('./my_project', './archive.zip')
        >>>
        >>> # 排除缓存和版本控制目录，并显示进度
        >>> zip_folder('./src', './src_backup.zip',
        >>>           exclude_dirs=['__pycache__', '.git', 'node_modules'],
        >>>           exclude_exts=['.log', '.tmp'],
        >>>           show_progress=True)
        >>>
        >>> # 快速压缩（不压缩），仅打包
        >>> zip_folder('/path/to/data', '/backup/data.zip',
        >>>           compression_level=0,
        >>>           show_progress=False)

    Notes:
        - 排除规则基于名称匹配，区分大小写
        - 压缩大文件时建议使用压缩级别6-8，在速度和压缩率间取得平衡
    """
    # 参数验证
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"文件夹不存在: {folder_path}")

    if not 0 <= compression_level <= 9:
        raise ValueError("压缩级别必须在0-9之间")

    # 初始化排除列表
    exclude_dirs = set(exclude_dirs or [])
    exclude_exts = set(ext.lower() for ext in (exclude_exts or []))

    # 准备文件列表
    file_paths = []
    total_size = 0

    for root, dirs, files in os.walk(folder_path):
        # 过滤排除目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        # 收集文件信息
        for file in files:
            if exclude_exts and os.path.splitext(file)[1].lower() in exclude_exts:
                continue

            file_path = os.path.join(root, file)
            file_paths.append(file_path)
            total_size += os.path.getsize(file_path)

        # 处理空文件夹
        if not files and not dirs:
            rel_path = os.path.relpath(root, folder_path)
            file_paths.append((root, rel_path))  # 标记为目录

    # 创建ZIP文件
    with zipfile.ZipFile(
            output_path,
            'w',
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=compression_level
    ) as zipf:
        # 进度条设置
        pbar = tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            desc=f"压缩 {os.path.basename(folder_path)}",
            disable=not show_progress
        )

        for item in file_paths:
            try:
                if isinstance(item, tuple):  # 空目录处理
                    root, rel_path = item
                    zipf.writestr(os.path.join(rel_path, '.keep'), '')
                else:
                    file_path = item
                    arcname = os.path.relpath(file_path, folder_path)
                    zinfo = zipfile.ZipInfo.from_file(file_path, arcname)
                    zinfo.compress_type = zipfile.ZIP_DEFLATED
                    zinfo.date_time = time.localtime()[:6]

                    # 分块读取大文件
                    with zipf.open(zinfo, 'w') as zf, open(file_path, 'rb') as f:
                        remaining = os.path.getsize(file_path)
                        chunk_size = 8192
                        while remaining > 0:
                            chunk = f.read(min(chunk_size, remaining))
                            zf.write(chunk)
                            remaining -= len(chunk)
                            pbar.update(len(chunk))
            except Exception as e:
                logger.error(f"\n❌ 文件压缩失败: {arcname} - {str(e)}")
                continue

        pbar.close()


def copy_file(copy_file_path, copy_des_path):
    """ 单个文件拷贝 """
    root_path = os.path.dirname(copy_des_path)
    if not os.path.exists(root_path):
        os.makedirs(root_path, exist_ok=True)
    shutil.copy(copy_file_path, copy_des_path)
    return True


def move_file(move_file_path, move_des_path):
    """ 单个文件移动 """
    root_path = os.path.dirname(move_des_path)
    if not os.path.exists(root_path):
        os.makedirs(root_path, exist_ok=True)
    shutil.move(move_file_path, move_des_path)
    return True


def get_missing_files(source_dir: str,
                      target_dir: str,
                      source_ext: str = '.jpg',
                      target_ext: str = '.xml'
                      ) -> Set[str]:
    """
    找出源目录中存在但目标目录中不存在的文件

    Args:
        source_dir: 源文件目录（如图片目录）
        target_dir: 目标文件目录（如XML目录）
        source_ext: 源文件扩展名（默认.jpg）
        target_ext: 目标文件扩展名（默认.xml）

    Returns:
        缺失的文件名集合（不含扩展名）
    """
    # 获取源文件和目标文件列表
    source_files = get_files(source_dir, source_ext)
    target_files = get_files(target_dir, target_ext)

    # 提取不带扩展名的文件名
    source_names = {os.path.basename(f).split('.')[0] for f in source_files}
    target_names = {os.path.basename(f).split('.')[0] for f in target_files}

    # 返回存在于source但不在target中的文件
    return set(source_names) - set(target_names)


def randomly_select_files(source_dir: str, file_ext: str = '.jpg', distribution: List[int] = None):
    """
    从源目录按照分配到多个目标目录的数量进行随机抽取文件

    Args:
        source_dir: 源文件目录
        file_ext: 文件扩展名
        distribution: 每个目标目录分配的文件数量

    Returns:
        返回的是随机抽取的文件的路径列表
    """
    # 获取源文件路径列表
    source_files = get_files(source_dir, file_ext)

    if not source_files:
        logger.warning(f"警告: 源目录 {source_dir} 中没有找到 {file_ext} 文件")
        return

    # 随机抽样
    total_files_needed = sum(distribution)
    import random
    random_files = random.sample(source_files, total_files_needed)
    random.shuffle(random_files)
    return random_files
