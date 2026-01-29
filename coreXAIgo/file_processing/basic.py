import shutil
import time
import zipfile
from typing import Optional, Union, List, Set
import os
from tqdm import tqdm

from ..utils.basic import set_logging


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

    Args:
        source_dir: 源文件目录
        file_ext: 文件扩展名
        distribution: 每个目标目录分配的文件数量

    Returns:
        返回的是随机抽取的文件的路径列表
    """
    logger = set_logging("randomly_select_files", verbose=verbose)
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
