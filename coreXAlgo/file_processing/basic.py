import shutil
import time
import zipfile
from pathlib import Path
from typing import Optional, Union, List, Set
import os
from tqdm import tqdm

from ..utils.basic import set_logging
from ..utils.constants import IMAGE_TYPE_FORMAT


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


def get_filenames(directory: str, extensions: Union[str, List[str]] = '.jpg',
                  exclude_dirs: Union[str, List[str]] = None) -> List[str]:
    """
    查找指定目录下所有匹配给定扩展名的文件名（不包含路径）

    Args:
        directory: 要搜索的目录路径
        extensions: 要匹配的文件扩展名，可以是单个字符串（如 '.jpg'）或列表（如 ['.jpg', '.png']）
        exclude_dirs: 要排除的目录名，可以是单个字符串或列表（支持相对路径或绝对路径）

    Returns:
        匹配文件的文件名列表（按字母顺序排序）

    Example:
        >>> # 查找所有jpg文件名
        >>> jpg_files = get_filenames('./images', '.jpg')
        >>> print(f"找到 {len(jpg_files)} 个JPG文件")
        >>> # 输出示例: ['cat.jpg', 'dog.jpg']
    """
    # 参数验证（与原函数相同）
    if not os.path.isdir(directory):
        raise ValueError(f"无效的目录路径: {directory}")

    if not isinstance(extensions, (str, list)):
        raise TypeError("扩展名参数必须是字符串或列表")

    if exclude_dirs is None:
        exclude_dirs = []
    elif isinstance(exclude_dirs, str):
        exclude_dirs = [exclude_dirs]
    elif not isinstance(exclude_dirs, list):
        raise TypeError("排除目录参数必须是字符串、列表或None")

    # 统一处理扩展名格式
    if isinstance(extensions, str):
        extensions = [extensions]
    extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]

    # 规范化排除目录路径
    normalized_exclude_dirs = []
    for exclude_dir in exclude_dirs:
        if not os.path.isabs(exclude_dir):
            exclude_dir = os.path.abspath(os.path.join(directory, exclude_dir))
        normalized_exclude_dirs.append(os.path.normpath(exclude_dir))

    # 收集文件名（不包含路径）
    file_names = []
    for root, dirs, files in os.walk(directory):
        # 检查是否在排除目录中
        current_dir_abs = os.path.abspath(root)
        if any(os.path.samefile(current_dir_abs, exclude_dir) for exclude_dir in normalized_exclude_dirs):
            dirs[:] = []
            continue

        # 检查父目录是否在排除列表中
        for exclude_dir in normalized_exclude_dirs:
            if current_dir_abs.startswith(exclude_dir + os.sep):
                dirs[:] = []
                continue

        # 收集匹配的文件名
        for file in files:
            if any(file.lower().endswith(ext.lower()) for ext in extensions):
                file_names.append(file)  # 只添加文件名，不包含路径

    return sorted(file_names)


def get_duplicate_files(source_dir: str, compare_dir: str) -> List[str]:
    """
    查找source_dir中在compare_dir里有重复文件名的文件

    Args:
        source_dir: 要查询的目录（只返回这个目录中的重复文件）
        compare_dir: 比较的目录

    Returns:
        source_dir中重复文件的完整路径列表
    """
    # 获取文件列表
    from coreXAlgo.utils import IMAGE_TYPE_FORMAT
    source_files = get_files(source_dir, IMAGE_TYPE_FORMAT)
    compare_files = get_files(compare_dir, IMAGE_TYPE_FORMAT)

    # 提取compare_dir中的文件名集合
    compare_filenames = {os.path.basename(p) for p in compare_files}

    # 找出source_dir中在compare_dir里有重复的文件
    duplicate_files = []
    for file_path in source_files:
        filename = os.path.basename(file_path)
        if filename in compare_filenames:
            duplicate_files.append(file_path)

    return duplicate_files

def generate_sequential_filename(file_path):
    """
    生成带序号的文件名

    Args:
        file_path: 原始文件路径

    Returns:
        str: 新的带序号文件路径
    """
    dir_path, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)

    index = 1
    while True:
        if index == 1:
            # 第一次尝试：在原文件名后加_1
            new_filename = f"{name}_1{ext}"
        else:
            # 后续尝试：递增序号
            new_filename = f"{name}_{index}{ext}"

        new_path = os.path.join(dir_path, new_filename)

        # 检查文件是否已存在
        if not os.path.exists(new_path):
            return new_path

        # 如果文件已存在，增加索引继续尝试
        index += 1


def copy_file(source_path, destination, overwrite=False, rename_if_exists=False):
    """
    单个文件拷贝，支持目录或文件路径，包含错误处理

    Args:
        source_path: 源文件路径
        destination: 目标路径（目录或文件路径）
        overwrite: 是否覆盖已存在的目标文件（默认为False）
        rename_if_exists: 当目标文件已存在时是否重命名继续拷贝（默认为False）

    Returns:
        str: 拷贝后的完整目标路径
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"源文件不存在: {source_path}")

    if not os.path.isfile(source_path):
        raise ValueError(f"源路径不是文件: {source_path}")

    # 确定目标路径
    if os.path.isdir(destination):
        # destination是目录
        target_dir = destination.rstrip(os.sep)
        filename = os.path.basename(source_path)
        target_path = os.path.join(target_dir, filename)
    else:
        # 检查destination是否应该被视为目录
        dest_dir, dest_name = os.path.split(destination)
        if not dest_name or (not os.path.splitext(destination)[1] and not os.path.exists(destination)):
            # 没有文件名或没有扩展名且路径不存在，视为目录
            if destination and not destination.endswith(os.sep):
                destination += os.sep
            filename = os.path.basename(source_path)
            target_path = os.path.join(destination, filename)
            target_dir = destination.rstrip(os.sep) if destination else ""
        else:
            # 视为文件路径
            target_path = destination
            target_dir = dest_dir

    # 检查目标文件是否已存在
    original_target_path = target_path
    if os.path.exists(target_path):
        if overwrite:
            # 如果允许覆盖，先尝试删除已存在的文件
            try:
                os.remove(target_path)
                print(f"已删除已存在的目标文件: {target_path}")
            except Exception as e:
                raise PermissionError(f"无法删除已存在的目标文件 {target_path}: {e}")

        elif rename_if_exists:
            # 如果允许重命名，在原文件名基础上添加序号
            target_path = generate_sequential_filename(original_target_path)
            print(f"目标文件已存在，重命名为: {target_path}")

        else:
            # 既不覆盖也不重命名，抛出异常
            raise FileExistsError(f"目标文件已存在: {target_path}")

    # 创建目标目录（如果不存在）
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
        print(f"已创建/确认目标目录: {target_dir}")

    try:
        # 执行拷贝
        shutil.copy2(source_path, target_path)
        print(f"成功拷贝: {source_path} -> {target_path}")

        # 验证拷贝是否成功
        if not os.path.exists(target_path):
            raise shutil.Error(f"拷贝后目标文件不存在: {target_path}")

        # 获取文件大小并验证
        source_size = os.path.getsize(source_path)
        target_size = os.path.getsize(target_path)

        if source_size != target_size:
            print(f"警告: 源文件大小({source_size}字节)和目标文件大小({target_size}字节)不一致")
        else:
            print(f"文件大小验证成功: {source_size}字节")

        return target_path

    except PermissionError as e:
        print(f"权限错误: 无法访问 {source_path} 或写入 {target_path}")
        raise
    except shutil.Error as e:
        print(f"拷贝过程出错: {source_path} -> {target_path}, 错误: {e}")
        raise
    except Exception as e:
        print(f"未知错误: 拷贝 {source_path} -> {target_path}, 错误: {e}")
        raise


def move_file(source_path, destination, overwrite=False, rename_if_exists=False):
    """
    单个文件移动，支持目录或文件路径，包含错误处理

    Args:
        source_path: 源文件路径
        destination: 目标路径（目录或文件路径）
        overwrite: 是否覆盖已存在的目标文件（默认为False）
        rename_if_exists: 当目标文件已存在时是否重命名继续移动（默认为False）

    Returns:
        str: 移动后的完整目标路径
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"源文件不存在: {source_path}")

    # 确定目标路径
    if os.path.isdir(destination):
        target_dir = destination.rstrip(os.sep)
        filename = os.path.basename(source_path)
        target_path = os.path.join(target_dir, filename)
    else:
        dest_dir, dest_name = os.path.split(destination)
        if not dest_name or (not os.path.splitext(destination)[1] and not os.path.exists(destination)):
            if destination and not destination.endswith(os.sep):
                destination += os.sep
            filename = os.path.basename(source_path)
            target_path = os.path.join(destination, filename)
            target_dir = destination.rstrip(os.sep) if destination else ""
        else:
            target_path = destination
            target_dir = dest_dir

    # 检查目标文件是否已存在
    original_target_path = target_path
    if os.path.exists(target_path):
        if overwrite:
            try:
                os.remove(target_path)
                print(f"已删除已存在的目标文件: {target_path}")
            except Exception as e:
                raise PermissionError(f"无法删除已存在的目标文件 {target_path}: {e}")

        elif rename_if_exists:
            target_path = generate_sequential_filename(original_target_path)
            print(f"目标文件已存在，重命名为: {target_path}")

        else:
            raise FileExistsError(f"目标文件已存在: {target_path}")

    # 创建目标目录（如果不存在）
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
        print(f"已创建/确认目标目录: {target_dir}")

    try:
        # 执行移动
        shutil.move(source_path, target_path)
        print(f"成功移动: {source_path} -> {target_path}")
        return target_path
    except Exception as e:
        print(f"移动文件失败: {source_path} -> {target_path}, 错误: {e}")
        raise


def copy_files(file_list, destination_dir, overwrite=False, rename_if_exists=False,
               create_subdirs=False, log_file=None):
    """
    批量拷贝文件

    Args:
        file_list: 文件路径列表
        destination_dir: 目标目录
        overwrite: 是否覆盖已存在的目标文件
        rename_if_exists: 当目标文件已存在时是否重命名
        create_subdirs: 是否在目标目录中保持源文件的目录结构
        log_file: 日志文件路径（可选）

    Returns:
        tuple: (成功拷贝的文件列表, 失败的文件列表)
    """
    successful_copies = []
    failed_copies = []

    def write_log(message):
        print(message)
        if log_file:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

    import time
    start_time = time.time()

    write_log(f"\n{'=' * 50}")
    write_log(f"开始批量拷贝: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    write_log(f"源文件数量: {len(file_list)}")
    write_log(f"目标目录: {destination_dir}")
    write_log(f"覆盖模式: {overwrite}")
    write_log(f"重命名模式: {rename_if_exists}")
    write_log(f"保持目录结构: {create_subdirs}")
    write_log(f"{'=' * 50}")

    for i, source_path in enumerate(file_list, 1):
        try:
            if not os.path.exists(source_path):
                write_log(f"[{i}/{len(file_list)}] 跳过: 源文件不存在 - {source_path}")
                failed_copies.append((source_path, "源文件不存在"))
                continue

            if create_subdirs:
                if len(file_list) > 1:
                    common_path = os.path.commonpath([os.path.dirname(f) for f in file_list])
                    rel_path = os.path.relpath(source_path, common_path)
                else:
                    rel_path = os.path.basename(source_path)
                dest_path = os.path.join(destination_dir, rel_path)
            else:
                dest_path = os.path.join(destination_dir, os.path.basename(source_path))

            write_log(f"[{i}/{len(file_list)}] 正在拷贝: {source_path}")
            copied_path = copy_file(source_path, dest_path, overwrite=overwrite,
                                    rename_if_exists=rename_if_exists)
            successful_copies.append(copied_path)
            write_log(f"[{i}/{len(file_list)}] 成功: {source_path} -> {copied_path}")

        except FileExistsError as e:
            write_log(f"[{i}/{len(file_list)}] 跳过: 目标文件已存在 - {source_path}")
            failed_copies.append((source_path, "目标文件已存在"))
        except PermissionError as e:
            write_log(f"[{i}/{len(file_list)}] 失败: 权限错误 - {source_path}")
            failed_copies.append((source_path, "权限错误"))
        except Exception as e:
            write_log(f"[{i}/{len(file_list)}] 失败: {e} - {source_path}")
            failed_copies.append((source_path, str(e)))

    end_time = time.time()

    write_log(f"\n{'=' * 50}")
    write_log(f"批量拷贝完成: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    write_log(f"总耗时: {end_time - start_time:.2f}秒")
    write_log(f"成功: {len(successful_copies)} 个文件")
    write_log(f"失败: {len(failed_copies)} 个文件")
    write_log(f"成功率: {len(successful_copies) / len(file_list) * 100:.1f}%" if file_list else "N/A")

    if failed_copies:
        write_log("\n失败文件列表:")
        for file_path, error in failed_copies:
            write_log(f"  - {file_path}: {error}")

    write_log(f"{'=' * 50}\n")

    return successful_copies, failed_copies


def move_files(file_list, destination_dir, overwrite=False, rename_if_exists=False,
               create_subdirs=False, log_file=None):
    """
    批量移动文件

    Args:
        file_list: 文件路径列表
        destination_dir: 目标目录
        overwrite: 是否覆盖已存在的目标文件
        rename_if_exists: 当目标文件已存在时是否重命名
        create_subdirs: 是否在目标目录中保持源文件的目录结构
        log_file: 日志文件路径（可选）

    Returns:
        tuple: (成功移动的文件列表, 失败的文件列表)
    """
    successful_moves = []
    failed_moves = []

    def write_log(message):
        print(message)
        if log_file:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

    import time
    start_time = time.time()

    write_log(f"\n{'=' * 50}")
    write_log(f"开始批量移动: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    write_log(f"源文件数量: {len(file_list)}")
    write_log(f"目标目录: {destination_dir}")
    write_log(f"覆盖模式: {overwrite}")
    write_log(f"重命名模式: {rename_if_exists}")
    write_log(f"保持目录结构: {create_subdirs}")
    write_log(f"{'=' * 50}")

    for i, source_path in enumerate(file_list, 1):
        try:
            if not os.path.exists(source_path):
                write_log(f"[{i}/{len(file_list)}] 跳过: 源文件不存在 - {source_path}")
                failed_moves.append((source_path, "源文件不存在"))
                continue

            if create_subdirs:
                if len(file_list) > 1:
                    common_path = os.path.commonpath([os.path.dirname(f) for f in file_list])
                    rel_path = os.path.relpath(source_path, common_path)
                else:
                    rel_path = os.path.basename(source_path)
                dest_path = os.path.join(destination_dir, rel_path)
            else:
                dest_path = os.path.join(destination_dir, os.path.basename(source_path))

            write_log(f"[{i}/{len(file_list)}] 正在移动: {source_path}")
            moved_path = move_file(source_path, dest_path, overwrite=overwrite,
                                   rename_if_exists=rename_if_exists)
            successful_moves.append(moved_path)
            write_log(f"[{i}/{len(file_list)}] 成功: {source_path} -> {moved_path}")

        except FileExistsError as e:
            write_log(f"[{i}/{len(file_list)}] 跳过: 目标文件已存在 - {source_path}")
            failed_moves.append((source_path, "目标文件已存在"))
        except PermissionError as e:
            write_log(f"[{i}/{len(file_list)}] 失败: 权限错误 - {source_path}")
            failed_moves.append((source_path, "权限错误"))
        except Exception as e:
            write_log(f"[{i}/{len(file_list)}] 失败: {e} - {source_path}")
            failed_moves.append((source_path, str(e)))

    end_time = time.time()

    write_log(f"\n{'=' * 50}")
    write_log(f"批量移动完成: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    write_log(f"总耗时: {end_time - start_time:.2f}秒")
    write_log(f"成功: {len(successful_moves)} 个文件")
    write_log(f"失败: {len(failed_moves)} 个文件")
    write_log(f"成功率: {len(successful_moves) / len(file_list) * 100:.1f}%" if file_list else "N/A")

    if failed_moves:
        write_log("\n失败文件列表:")
        for file_path, error in failed_moves:
            write_log(f"  - {file_path}: {error}")

    write_log(f"{'=' * 50}\n")

    return successful_moves, failed_moves


def get_missing_files(source_dir: str, target_dir: str, source_ext: str = '.jpg', target_ext: str = '.xml') -> Set[str]:
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


def randomly_select_files(source_dir: str, file_ext: str = '.jpg', distribution: List[int] = None,
                          verbose: bool = False):
    """
    从源目录按照分配到多个目标目录的数量进行随机抽取文件
    
    该函数用于从指定目录中随机抽取文件，主要应用于数据集划分场景，
    如将数据集划分为训练集、验证集和测试集。函数会返回随机打乱后的文件路径列表，
    可以直接按照 distribution 参数指定的数量分配到不同目录。

    Args:
        source_dir (str): 源文件目录路径，必须是存在的有效目录
        file_ext (str): 文件扩展名，默认为 '.jpg'，支持常见图片格式如 '.png', '.jpeg' 等
        distribution (List[int]): 每个目标目录分配的文件数量列表，如 [100, 50, 50] 表示
                                  第一个目标目录分配100个文件，第二个分配50个，第三个分配50个
        verbose (bool): 是否显示详细日志信息，默认为 False。设置为 True 时会显示
                        文件扫描和抽取过程的详细信息

    Returns:
        List[str] or None: 返回随机抽取的文件路径列表，如果源目录中没有找到文件则返回 None
                          文件列表已经过随机打乱，可以直接按顺序分配给目标目录

    Raises:
        ValueError: 当 distribution 为 None 或空列表时
        IndexError: 当请求的文件数量超过源目录中实际文件数量时
        FileNotFoundError: 当 source_dir 不存在时

    示例:
        >>> # 示例1: 基本用法 - 从目录中随机抽取10个文件
        >>> files = randomly_select_files('data/images', '.jpg', [10])
        >>> print(f"抽取了 {len(files)} 个文件")
        抽取了 10 个文件
        
        >>> # 示例2: 数据集划分 - 按 8:1:1 比例划分数据集
        >>> distribution = [800, 100, 100]  # 训练集800，验证集100，测试集100
        >>> files = randomly_select_files('dataset/images', '.jpg', distribution)
        >>> 
        >>> # 分配到不同目录
        >>> train_files = files[:800]
        >>> val_files = files[800:900]
        >>> test_files = files[900:]
        >>> 
        >>> print(f"训练集: {len(train_files)} 个文件")
        >>> print(f"验证集: {len(val_files)} 个文件")
        >>> print(f"测试集: {len(test_files)} 个文件")
        训练集: 800 个文件
        验证集: 100 个文件
        测试集: 100 个文件
        
        >>> # 示例3: 处理不同文件类型
        >>> # 处理文本文件
        >>> text_files = randomly_select_files('corpus', '.txt', [50])
        >>> 
        >>> # 处理XML标签文件
        >>> xml_files = randomly_select_files('annotations', '.xml', [30])
        
        >>> # 示例4: 结合文件复制操作
        >>> import shutil
        >>> from pathlib import Path
        >>> 
        >>> # 随机抽取文件
        >>> files = randomly_select_files('source', '.jpg', [10, 10])
        >>> 
        >>> # 复制到目标目录
        >>> dest_dirs = ['train', 'val']
        >>> start = 0
        >>> for i, count in enumerate([10, 10]):
        >>>     end = start + count
        >>>     subset = files[start:end]
        >>>     dest_path = Path(dest_dirs[i])
        >>>     dest_path.mkdir(exist_ok=True)
        >>>     
        >>>     for file_path in subset:
        >>>         shutil.copy(file_path, dest_path / Path(file_path).name)
        >>>     
        >>>     start = end
        >>>     print(f"已复制 {count} 个文件到 {dest_path}")
    """
    import random
    
    # 设置日志记录器，用于记录函数执行过程中的信息
    logger = set_logging("randomly_select_files", verbose=verbose)
    
    # 获取源文件路径列表
    # get_files 函数会递归搜索目录，返回所有匹配扩展名的文件路径
    source_files = get_files(source_dir, file_ext)

    # 检查是否找到文件
    if not source_files:
        logger.warning(f"警告: 源目录 {source_dir} 中没有找到 {file_ext} 文件")
        return None

    # 计算需要抽取的文件总数
    # distribution 是一个列表，sum 函数计算列表中所有元素的和
    total_files_needed = sum(distribution)
    
    # 随机抽样
    # random.sample 从源文件中随机抽取指定数量的文件，确保不重复
    # 如果 total_files_needed 超过 source_files 的长度，会引发 IndexError
    random_files = random.sample(source_files, total_files_needed)
    
    # 打乱文件顺序
    # shuffle 函数会原地打乱列表顺序，增加随机性
    # 这样可以确保分配给不同目标目录的文件是完全随机的
    random.shuffle(random_files)
    
    return random_files

def clean_unmatched_files(folder_path, img_exts=None, label_ext=None, delete_images=True, delete_labels=True, dry_run=True):
    """
    删除或移动没有对应匹配的文件（图片或标签文件）

    参数:
    folder_path: 文件夹路径
    img_exts: 图片扩展名列表，默认从 coreXAlgo.utils.IMAGE_TYPE_FORMAT 获取
    label_ext: 标签文件扩展名（单个字符串，如 '.txt' 或 '.xml'）
    delete_images: True=删除没有对应标签的图片，False=移动到no_label_images文件夹
    delete_labels: True=删除没有对应图片的标签，False=移动到no_image_labels文件夹
    dry_run: 是否只是模拟运行（True=只显示不删除/不移动，False=实际操作）
    
    示例:
        >>> # 示例1: 模拟运行 - 查看需要清理的文件
        >>> clean_unmatched_files(
        >>>     folder_path='dataset/train',
        >>>     label_ext='.txt',
        >>>     dry_run=True
        >>> )
        # 输出会显示文件匹配情况和计划的操作
        
        >>> # 示例2: 实际删除不匹配的文件
        >>> clean_unmatched_files(
        >>>     folder_path='dataset/val',
        >>>     label_ext='.xml',
        >>>     delete_images=True,
        >>>     delete_labels=True,
        >>>     dry_run=False
        >>> )
        # 会删除没有对应标签的图片和没有对应图片的标签文件
        
        >>> # 示例3: 移动不匹配的文件到单独的文件夹
        >>> clean_unmatched_files(
        >>>     folder_path='dataset/test',
        >>>     label_ext='.txt',
        >>>     delete_images=False,  # 移动而不是删除
        >>>     delete_labels=False,  # 移动而不是删除
        >>>     dry_run=False
        >>> )
        # 会将无标签的图片移动到 no_label_images 文件夹
        # 将无图片的标签移动到 no_image_labels 文件夹
        
        >>> # 示例4: 自定义图片扩展名
        >>> clean_unmatched_files(
        >>>     folder_path='dataset/custom',
        >>>     img_exts=['.jpg', '.png', '.bmp'],  # 只处理这些扩展名的图片
        >>>     label_ext='.json',  # 标签文件为 JSON 格式
        >>>     dry_run=True
        >>> )
        # 只检查指定扩展名的图片文件
        
        >>> # 示例5: 处理不同类型的标签文件
        >>> # 处理 YOLO 格式标签文件
        >>> clean_unmatched_files(
        >>>     folder_path='yolo_dataset',
        >>>     label_ext='.txt',
        >>>     dry_run=True
        >>> )
        
        >>> # 处理 PASCAL VOC 格式标签文件
        >>> clean_unmatched_files(
        >>>     folder_path='voc_dataset',
        >>>     label_ext='.xml',
        >>>     dry_run=True
        >>> )
    """
    # 设置默认扩展名
    if img_exts is None:
        img_exts = IMAGE_TYPE_FORMAT

    # 标签扩展名必须传入，是单个字符串
    if label_ext is None:
        raise ValueError("必须传入 label_ext 参数，指定标签文件的后缀名（如 '.txt', '.xml'）")

    # 确保标签扩展名是字符串且以点开头
    if not isinstance(label_ext, str):
        raise ValueError("label_ext 必须是字符串类型")

    label_ext = label_ext.lower()
    label_ext = label_ext if label_ext.startswith('.') else f'.{label_ext}'

    folder = Path(folder_path)
    if not folder.exists():
        print(f"错误: 文件夹 '{folder_path}' 不存在")
        return

    # 确保所有扩展名都以点开头
    img_exts = [ext.lower() for ext in img_exts]
    img_exts = [ext if ext.startswith('.') else f'.{ext}' for ext in img_exts]

    print(f"{'=' * 60}")
    print(f"清理不匹配文件工具")
    print(f"{'=' * 60}")
    print(f"图片扩展名: {img_exts}")
    print(f"标签扩展名: {label_ext}")
    print(f"文件夹: {folder.absolute()}")

    # 收集所有文件
    img_files = {}  # {文件名(不含扩展名): 文件路径}
    label_files = {}  # {文件名(不含扩展名): 文件路径}

    print(f"\n扫描文件夹...")

    try:
        file_paths = get_files(folder_path, img_exts + [label_ext])
    except NameError:
        # 如果get_files不存在，使用备用方案
        file_paths = []
        for ext in img_exts + [label_ext]:
            file_paths.extend(folder.glob(f"*{ext}"))
        file_paths.extend(folder.glob(f"*{ext.upper()}"))  # 大写扩展名

    for file_path in file_paths:
        file_path = Path(file_path) if not isinstance(file_path, Path) else file_path
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()
        name_without_ext = file_path.stem  # 文件名（不含扩展名）

        if ext in img_exts:
            img_files[name_without_ext] = file_path
        elif ext == label_ext:  # 标签扩展名精确匹配
            label_files[name_without_ext] = file_path

    print(f"找到 {len(img_files)} 个图片文件")
    print(f"找到 {len(label_files)} 个标签文件")

    # 分析匹配情况
    img_names = set(img_files.keys())
    label_names = set(label_files.keys())

    matched_names = img_names.intersection(label_names)
    only_img_names = img_names - label_names  # 只有图片，没有标签
    only_label_names = label_names - img_names  # 只有标签，没有图片

    print(f"\n{'=' * 60}")
    print(f"分析结果:")
    print(f"  ✓ 匹配的文件对: {len(matched_names):4d} 个")
    print(f"  ⚠ 只有图片没有标签: {len(only_img_names):4d} 个")
    print(f"  ⚠ 只有标签没有图片: {len(only_label_names):4d} 个")
    print(f"{'=' * 60}")

    # 处理操作
    files_to_delete = []  # 要删除的文件
    images_to_move = []  # 要移动的图片文件路径列表
    labels_to_move = []  # 要移动的标签文件路径列表

    # 创建移动文件夹的路径
    no_label_images_folder = folder.parent / "no_label_images"
    no_image_labels_folder = folder.parent / "no_image_labels"

    if only_img_names:
        for name in sorted(only_img_names):
            file_path = img_files[name]
            if delete_images:
                files_to_delete.append(file_path)
            else:
                images_to_move.append(str(file_path))

    if only_label_names:
        for name in sorted(only_label_names):
            file_path = label_files[name]
            if delete_labels:
                files_to_delete.append(file_path)
            else:
                labels_to_move.append(str(file_path))

    # 检查是否有任何需要处理的操作
    has_deletions = bool(files_to_delete)
    has_movements = bool(images_to_move or labels_to_move)

    if not has_deletions and not has_movements:
        print("\n🎉 没有需要处理的文件！所有文件都已匹配。")
        return

    # 显示将要进行的操作
    print(f"\n操作计划:")

    if files_to_delete:
        print(f"\n  🔴 将要删除 {len(files_to_delete)} 个文件:")
        for file_path in files_to_delete:
            try:
                size = file_path.stat().st_size
                size_str = f"({size / 1024:,.1f} KB)"
            except:
                size_str = ""
            print(f"     - {file_path.name} {size_str}".strip())

    if images_to_move:
        print(f"\n  📁 将要移动 {len(images_to_move)} 个图片文件到:")
        print(f"     目标: {no_label_images_folder}")
        for file_path_str in images_to_move[:5]:  # 只显示前5个
            print(f"     - {Path(file_path_str).name}")
        if len(images_to_move) > 5:
            print(f"     ... 还有 {len(images_to_move) - 5} 个")

    if labels_to_move:
        print(f"\n  📁 将要移动 {len(labels_to_move)} 个标签文件到:")
        print(f"     目标: {no_image_labels_folder}")
        for file_path_str in labels_to_move[:5]:  # 只显示前5个
            print(f"     - {Path(file_path_str).name}")
        if len(labels_to_move) > 5:
            print(f"     ... 还有 {len(labels_to_move) - 5} 个")

    if dry_run:
        print(f"\n{'=' * 60}")
        print(f"📋 模拟运行完成")
        print(f"   若要实际执行操作，请设置 dry_run=False")
        if images_to_move:
            print(f"   无标签图片将移动到: {no_label_images_folder}")
        if labels_to_move:
            print(f"   无图片标签将移动到: {no_image_labels_folder}")
        print(f"{'=' * 60}")
        return

    # 确认操作
    print(f"\n{'=' * 60}")
    confirm = input("⚠️  确认执行上述操作吗？(y/N): ").strip().lower()
    if confirm not in ['y', 'yes', '是']:
        print("操作已取消。")
        return
    print(f"{'=' * 60}")

    # 实际执行操作
    print(f"\n开始处理...")
    deleted_count = 0
    moved_count = 0
    deleted_size = 0

    # 1. 先处理移动操作
    if images_to_move:
        print(f"\n📤 移动无标签图片:")
        try:
            successful, failed = move_files(
                file_list=images_to_move,
                destination_dir=str(no_label_images_folder),
                overwrite=False,
                rename_if_exists=True,  # 重命名避免冲突
                create_subdirs=False,
                log_file=None
            )
            moved_count += len(successful)
            print(f"   成功移动: {len(successful)} 个文件")
            if failed:
                print(f"   失败: {len(failed)} 个文件")
        except Exception as e:
            print(f"   移动图片时出错: {e}")

    if labels_to_move:
        print(f"\n📤 移动无图片标签:")
        try:
            successful, failed = move_files(
                file_list=labels_to_move,
                destination_dir=str(no_image_labels_folder),
                overwrite=False,
                rename_if_exists=True,  # 重命名避免冲突
                create_subdirs=False,
                log_file=None
            )
            moved_count += len(successful)
            print(f"   成功移动: {len(successful)} 个文件")
            if failed:
                print(f"   失败: {len(failed)} 个文件")
        except Exception as e:
            print(f"   移动标签时出错: {e}")

    # 2. 再处理删除操作
    if files_to_delete:
        print(f"\n🗑️  删除文件:")
        for file_path in files_to_delete:
            try:
                file_size = file_path.stat().st_size
                file_path.unlink()  # 删除文件
                print(f"   ✓ 已删除: {file_path.name} ({file_size / 1024:,.1f} KB)")
                deleted_count += 1
                deleted_size += file_size
            except Exception as e:
                print(f"   ✗ 删除失败: {file_path.name} - {e}")

        # 显示处理结果
        print(f"\n{'=' * 60}")
        print(f"✅ 处理完成！")
        print(f"{'=' * 60}")

        if deleted_count > 0 or moved_count > 0:
            print(f"\n处理摘要:")
            if deleted_count > 0:
                print(f"  🔴 已删除: {deleted_count} 个文件 ({deleted_size / 1024 / 1024:,.2f} MB)")

            if moved_count > 0:
                print(f"  📁 已移动: {moved_count} 个文件")
                if images_to_move and no_label_images_folder.exists():
                    moved_imgs = len(list(no_label_images_folder.glob("*")))
                    print(f"    无标签图片: {moved_imgs} 个 ({no_label_images_folder.absolute()})")
                if labels_to_move and no_image_labels_folder.exists():
                    moved_labels = len(list(no_image_labels_folder.glob("*")))
                    print(f"    无图片标签: {moved_labels} 个 ({no_image_labels_folder.absolute()})")

        # 验证结果
        actual_imgs = sum(1 for f in folder.iterdir() if f.is_file() and f.suffix.lower() in img_exts)
        actual_labels = sum(1 for f in folder.iterdir() if f.is_file() and f.suffix.lower() == label_ext)
        expected_imgs = len(img_files) - len(only_img_names)
        expected_labels = len(label_files) - len(only_label_names)

        print(f"\n📊 最终统计:")
        print(f"  匹配的文件对: {len(matched_names)} 个")
        print(f"  剩余图片: {expected_imgs} 个 (预期) | {actual_imgs} 个 (实际)")
        print(f"  剩余标签: {expected_labels} 个 (预期) | {actual_labels} 个 (实际)")

        if expected_imgs == actual_imgs and expected_labels == actual_labels:
            print(f"  ✅ 验证通过")
        else:
            print(f"  ⚠ 验证失败: 预期与实际情况不一致")

        print(f"{'=' * 60}")
