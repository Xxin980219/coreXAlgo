"""
文件压缩解压管理模块

此模块提供了一个功能强大的 `ArchiveManager` 类，支持多种压缩格式的文件压缩和解压操作。

主要特性：
- 支持多种压缩格式：ZIP、TAR、TAR.GZ、TAR.BZ2、TAR.XZ、GZ、BZ2、XZ、7Z、RAR
- 支持压缩级别设置
- 支持排除特定目录和文件扩展名
- 支持密码保护（部分格式）
- 支持进度条显示
- 支持分块处理大文件
- 完善的错误处理和日志记录

使用示例：
    >>> from coreXAlgo.file_processing import ArchiveManager, CompressionFormat
    >>>
    >>> # 创建压缩管理器实例
    >>> manager = ArchiveManager(verbose=True)
    >>>
    >>> # 压缩文件夹为 ZIP
    >>> manager.compress(
    ...     source='./my_folder',
    ...     output_path='./output.zip',
    ...     format=CompressionFormat.ZIP,
    ...     compression_level=9,
    ...     exclude_dirs=['__pycache__', '.git'],
    ...     exclude_exts=['.log', '.tmp']
    ... )
    >>>
    >>> # 解压 ZIP 文件
    >>> manager.extract(
    ...     archive_path='./archive.zip',
    ...     extract_to='./extracted',
    ...     skip_existing=True
    ... )
"""
import os
import time
import zipfile
from typing import Optional, Union, List
from enum import Enum
from tqdm import tqdm

from ..utils.basic import set_logging


class CompressionFormat(Enum):
    """
    压缩格式枚举类
    
    定义了支持的所有压缩格式，包括：
    - ZIP: ZIP 格式
    - TAR: 未压缩的 TAR 格式
    - TAR_GZ: GZIP 压缩的 TAR 格式
    - TAR_BZ2: BZIP2 压缩的 TAR 格式
    - TAR_XZ: XZ 压缩的 TAR 格式
    - GZ: 单个文件的 GZIP 压缩格式
    - BZ2: 单个文件的 BZIP2 压缩格式
    - XZ: 单个文件的 XZ 压缩格式
    - SEVEN_Z: 7-Zip 格式
    - RAR: RAR 格式
    """
    ZIP = 'zip'
    TAR = 'tar'
    TAR_GZ = 'tar.gz'
    TAR_BZ2 = 'tar.bz2'
    TAR_XZ = 'tar.xz'
    GZ = 'gz'
    BZ2 = 'bz2'
    XZ = 'xz'
    SEVEN_Z = '7z'
    RAR = 'rar'


class ArchiveManager:
    """
    压缩解压管理器类
    
    提供统一的接口来处理多种压缩格式的文件压缩和解压操作。
    
    Attributes:
        verbose (bool): 是否启用详细日志
        logger: 日志记录器实例
    
    Methods:
        compress: 压缩文件或文件夹
        extract: 解压压缩文件
    """
    def __init__(self, verbose: bool = False):
        """
        初始化 ArchiveManager 实例
        
        Args:
            verbose (bool): 是否启用详细日志，默认为 False
        """
        self.verbose = verbose
        self.logger = set_logging("ArchiveManager", verbose=verbose)

    def compress(self, source: str, output_path: str, 
                 format: Union[str, CompressionFormat] = CompressionFormat.ZIP,
                 compression_level: int = 9,
                 exclude_dirs: Optional[List[str]] = None,
                 exclude_exts: Optional[List[str]] = None,
                 show_progress: bool = True,
                 password: Optional[str] = None) -> None:
        """
        压缩文件或文件夹
        
        Args:
            source (str): 要压缩的文件或文件夹路径
            output_path (str): 输出压缩文件的路径
            format (Union[str, CompressionFormat]): 压缩格式，可以是字符串或 CompressionFormat 枚举值
            compression_level (int): 压缩级别（0-9，0=不压缩/最快，9=最大压缩/最慢）
            exclude_dirs (Optional[List[str]]): 要排除的目录名列表
            exclude_exts (Optional[List[str]]): 要排除的文件扩展名列表
            show_progress (bool): 是否显示进度条
            password (Optional[str]): 压缩密码（仅支持 ZIP、7Z、RAR 格式）
        
        Raises:
            ValueError: 如果压缩格式不支持或参数无效
            FileNotFoundError: 如果源文件或文件夹不存在
        
        Example:
            >>> # 压缩文件夹为 ZIP
            >>> manager.compress(
            ...     source='./my_folder',
            ...     output_path='./output.zip',
            ...     format=CompressionFormat.ZIP,
            ...     compression_level=9,
            ...     exclude_dirs=['__pycache__', '.git'],
            ...     exclude_exts=['.log', '.tmp']
            ... )
            >>>
            >>> # 压缩单个文件为 7Z
            >>> manager.compress(
            ...     source='./data.txt',
            ...     output_path='./data.7z',
            ...     format='7z',
            ...     password='secure_password'
            ... )
        """
        if isinstance(format, str):
            try:
                format = CompressionFormat(format.lower())
            except ValueError:
                raise ValueError(f"不支持的压缩格式: {format}")

        if format == CompressionFormat.ZIP:
            self._compress_zip(source, output_path, compression_level, 
                             exclude_dirs, exclude_exts, show_progress, password)
        elif format == CompressionFormat.TAR:
            self._compress_tar(source, output_path, '', exclude_dirs, 
                             exclude_exts, show_progress)
        elif format == CompressionFormat.TAR_GZ:
            self._compress_tar(source, output_path, 'gz', exclude_dirs, 
                             exclude_exts, show_progress)
        elif format == CompressionFormat.TAR_BZ2:
            self._compress_tar(source, output_path, 'bz2', exclude_dirs, 
                             exclude_exts, show_progress)
        elif format == CompressionFormat.TAR_XZ:
            self._compress_tar(source, output_path, 'xz', exclude_dirs, 
                             exclude_exts, show_progress)
        elif format == CompressionFormat.GZ:
            self._compress_gz(source, output_path, compression_level, show_progress)
        elif format == CompressionFormat.BZ2:
            self._compress_bz2(source, output_path, compression_level, show_progress)
        elif format == CompressionFormat.XZ:
            self._compress_xz(source, output_path, show_progress)
        elif format == CompressionFormat.SEVEN_Z:
            self._compress_7z(source, output_path, compression_level, 
                            exclude_dirs, exclude_exts, show_progress, password)
        elif format == CompressionFormat.RAR:
            self._compress_rar(source, output_path, compression_level, 
                             exclude_dirs, exclude_exts, show_progress, password)
        else:
            raise ValueError(f"不支持的压缩格式: {format}")

    def extract(self, archive_path: str, extract_to: str,
                chunk_size: int = 8192,
                skip_existing: bool = True,
                show_progress: bool = True,
                password: Optional[str] = None) -> None:
        """
        解压压缩文件
        
        Args:
            archive_path (str): 压缩文件的路径
            extract_to (str): 解压目标目录
            chunk_size (int): 解压缓冲区大小（字节），默认为 8KB
            skip_existing (bool): 是否跳过已存在的文件
            show_progress (bool): 是否显示进度条
            password (Optional[str]): 解压密码（仅支持 ZIP、7Z、RAR 格式）
        
        Raises:
            FileNotFoundError: 如果压缩文件不存在
            ValueError: 如果压缩格式不支持
            ImportError: 如果缺少必要的依赖库
        
        Example:
            >>> # 解压 ZIP 文件
            >>> manager.extract(
            ...     archive_path='./archive.zip',
            ...     extract_to='./extracted',
            ...     skip_existing=True
            ... )
            >>>
            >>> # 解压带密码的 7Z 文件
            >>> manager.extract(
            ...     archive_path='./data.7z',
            ...     extract_to='./extracted_data',
            ...     password='secure_password'
            ... )
            >>>
            >>> # 解压大文件时使用更大的缓冲区
            >>> manager.extract(
            ...     archive_path='./large_file.zip',
            ...     extract_to='./output',
            ...     chunk_size=65536  # 64KB 缓冲区
            ... )
        """
        if not os.path.isfile(archive_path):
            raise FileNotFoundError(f"压缩文件不存在: {archive_path}")

        ext = self._get_archive_format(archive_path)
        
        if ext == CompressionFormat.ZIP:
            self._extract_zip(archive_path, extract_to, chunk_size, 
                           skip_existing, show_progress, password)
        elif ext in [CompressionFormat.TAR, CompressionFormat.TAR_GZ, 
                    CompressionFormat.TAR_BZ2, CompressionFormat.TAR_XZ]:
            self._extract_tar(archive_path, extract_to, show_progress)
        elif ext == CompressionFormat.GZ:
            self._extract_gz(archive_path, extract_to, show_progress)
        elif ext == CompressionFormat.BZ2:
            self._extract_bz2(archive_path, extract_to, show_progress)
        elif ext == CompressionFormat.XZ:
            self._extract_xz(archive_path, extract_to, show_progress)
        elif ext == CompressionFormat.SEVEN_Z:
            self._extract_7z(archive_path, extract_to, show_progress, password)
        elif ext == CompressionFormat.RAR:
            self._extract_rar(archive_path, extract_to, show_progress, password)
        else:
            raise ValueError(f"不支持的压缩格式: {ext}")

    def _compress_zip(self, source: str, output_path: str, 
                     compression_level: int,
                     exclude_dirs: Optional[List[str]],
                     exclude_exts: Optional[List[str]],
                     show_progress: bool,
                     password: Optional[str]) -> None:
        if os.path.isfile(source):
            self._compress_single_file_zip(source, output_path, 
                                          compression_level, show_progress, password)
        else:
            # 参数验证
            if not os.path.isdir(source):
                raise FileNotFoundError(f"文件夹不存在: {source}")

            if not 0 <= compression_level <= 9:
                raise ValueError("压缩级别必须在0-9之间")

            # 初始化排除列表
            exclude_dirs = set(exclude_dirs or [])
            exclude_exts = set(ext.lower() for ext in (exclude_exts or []))

            # 准备文件列表
            file_paths = []
            total_size = 0

            for root, dirs, files in os.walk(source):
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
                    rel_path = os.path.relpath(root, source)
                    file_paths.append((root, rel_path))  # 标记为目录

            # 创建ZIP文件
            with zipfile.ZipFile(
                    output_path,
                    'w',
                    compression=zipfile.ZIP_DEFLATED,
                    compresslevel=compression_level
            ) as zipf:
                if password:
                    zipf.setpassword(password.encode())
                # 进度条设置
                pbar = tqdm(
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    desc=f"压缩 {os.path.basename(source)}",
                    disable=not show_progress
                )

                for item in file_paths:
                    try:
                        if isinstance(item, tuple):  # 空目录处理
                            root, rel_path = item
                            zipf.writestr(os.path.join(rel_path, '.keep'), '')
                        else:
                            file_path = item
                            arcname = os.path.relpath(file_path, source)
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
                        self.logger.error(f"\n❌ 文件压缩失败: {arcname} - {str(e)}")
                        continue

                pbar.close()

            self.logger.info(f"✅ 压缩完成: {output_path}")

    def _compress_single_file_zip(self, source: str, output_path: str,
                                 compression_level: int,
                                 show_progress: bool,
                                 password: Optional[str]) -> None:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with zipfile.ZipFile(
            output_path, 'w',
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=compression_level
        ) as zipf:
            if password:
                zipf.setpassword(password.encode())
            
            file_size = os.path.getsize(source)
            pbar = tqdm(
                total=file_size,
                unit='B',
                unit_scale=True,
                desc=f"压缩 {os.path.basename(source)}",
                disable=not show_progress
            )
            
            with open(source, 'rb') as f:
                chunk_size = 8192
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    zipf.writestr(os.path.basename(source), chunk)
                    pbar.update(len(chunk))
            
            pbar.close()
        
        self.logger.info(f"✅ 压缩完成: {output_path}")

    def _extract_zip(self, zip_path: str, extract_to: str,
                    chunk_size: int,
                    skip_existing: bool,
                    show_progress: bool,
                    password: Optional[str]) -> None:
        # 验证ZIP文件
        if not os.path.isfile(zip_path):
            raise FileNotFoundError(f"ZIP文件不存在: {zip_path}")

        # 创建目标目录
        os.makedirs(extract_to, exist_ok=True)
        self.logger.info(f"准备解压: {zip_path} → {extract_to}")

        # 处理密码
        pwd = password.encode() if password else None

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
                        desc=f"解压 {os.path.basename(zip_path)}",
                        disable=not show_progress
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

                            # 分块解压大文件（带密码支持）
                            with zip_ref.open(file, pwd=pwd) as src, open(dest_path, 'wb') as dst:
                                while True:
                                    chunk = src.read(chunk_size)
                                    if not chunk:
                                        break
                                    dst.write(chunk)
                                    pbar.update(len(chunk))

                        except Exception as e:
                            self.logger.error(f"❌ 解压失败: {file} - {str(e)}")
                            if os.path.exists(dest_path):
                                os.remove(dest_path)

        except zipfile.BadZipFile as e:
            self.logger.error(f"❌ ZIP文件损坏: {zip_path} - {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"❌ 解压过程中发生错误: {str(e)}")
            raise

        self.logger.info(f"✅ 解压完成: {extract_to}")

    def _compress_tar(self, source: str, output_path: str,
                     mode: str,
                     exclude_dirs: Optional[List[str]],
                     exclude_exts: Optional[List[str]],
                     show_progress: bool) -> None:
        import tarfile
        
        if not os.path.isdir(source):
            raise ValueError(f"TAR压缩只支持目录: {source}")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        exclude_dirs = set(exclude_dirs or [])
        exclude_exts = set(ext.lower() for ext in (exclude_exts or []))
        
        file_paths = []
        total_size = 0
        
        for root, dirs, files in os.walk(source):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if exclude_exts and os.path.splitext(file)[1].lower() in exclude_exts:
                    continue
                
                file_path = os.path.join(root, file)
                file_paths.append(file_path)
                total_size += os.path.getsize(file_path)
        
        compression_map = {'': '', 'gz': 'gz', 'bz2': 'bz2', 'xz': 'xz'}
        tar_mode = f'w:{compression_map.get(mode, "")}'
        
        with tarfile.open(output_path, tar_mode) as tar:
            pbar = tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                desc=f"压缩 {os.path.basename(source)}",
                disable=not show_progress
            )
            
            for file_path in file_paths:
                arcname = os.path.relpath(file_path, source)
                tar.add(file_path, arcname=arcname)
                pbar.update(os.path.getsize(file_path))
            
            pbar.close()
        
        self.logger.info(f"✅ 压缩完成: {output_path}")

    def _extract_tar(self, tar_path: str, extract_to: str,
                    show_progress: bool) -> None:
        import tarfile
        
        os.makedirs(extract_to, exist_ok=True)
        self.logger.info(f"准备解压: {tar_path} → {extract_to}")
        
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            total_size = sum(m.size for m in members if m.isfile())
            
            pbar = tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                desc=f"解压 {os.path.basename(tar_path)}",
                disable=not show_progress
            )
            
            for member in members:
                tar.extract(member, extract_to)
                if member.isfile():
                    pbar.update(member.size)
            
            pbar.close()
        
        self.logger.info(f"✅ 解压完成: {extract_to}")

    def _compress_gz(self, source: str, output_path: str,
                    compression_level: int,
                    show_progress: bool) -> None:
        import gzip
        
        if not os.path.isfile(source):
            raise ValueError(f"GZ压缩只支持单个文件: {source}")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        file_size = os.path.getsize(source)
        pbar = tqdm(
            total=file_size,
            unit='B',
            unit_scale=True,
            desc=f"压缩 {os.path.basename(source)}",
            disable=not show_progress
        )
        
        with open(source, 'rb') as f_in:
            with gzip.open(output_path, 'wb', compresslevel=compression_level) as f_out:
                chunk_size = 8192
                while True:
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    pbar.update(len(chunk))
        
        pbar.close()
        self.logger.info(f"✅ 压缩完成: {output_path}")

    def _extract_gz(self, gz_path: str, extract_to: str,
                    show_progress: bool) -> None:
        import gzip
        
        os.makedirs(extract_to, exist_ok=True)
        
        output_file = os.path.join(extract_to, os.path.basename(gz_path).replace('.gz', ''))
        file_size = os.path.getsize(gz_path)
        
        pbar = tqdm(
            total=file_size,
            unit='B',
            unit_scale=True,
            desc=f"解压 {os.path.basename(gz_path)}",
            disable=not show_progress
        )
        
        with gzip.open(gz_path, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                chunk_size = 8192
                while True:
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    pbar.update(len(chunk))
        
        pbar.close()
        self.logger.info(f"✅ 解压完成: {output_file}")

    def _compress_bz2(self, source: str, output_path: str,
                     compression_level: int,
                     show_progress: bool) -> None:
        import bz2
        
        if not os.path.isfile(source):
            raise ValueError(f"BZ2压缩只支持单个文件: {source}")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        file_size = os.path.getsize(source)
        pbar = tqdm(
            total=file_size,
            unit='B',
            unit_scale=True,
            desc=f"压缩 {os.path.basename(source)}",
            disable=not show_progress
        )
        
        with open(source, 'rb') as f_in:
            with bz2.open(output_path, 'wb', compresslevel=compression_level) as f_out:
                chunk_size = 8192
                while True:
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    pbar.update(len(chunk))
        
        pbar.close()
        self.logger.info(f"✅ 压缩完成: {output_path}")

    def _extract_bz2(self, bz2_path: str, extract_to: str,
                    show_progress: bool) -> None:
        import bz2
        
        os.makedirs(extract_to, exist_ok=True)
        
        output_file = os.path.join(extract_to, os.path.basename(bz2_path).replace('.bz2', ''))
        file_size = os.path.getsize(bz2_path)
        
        pbar = tqdm(
            total=file_size,
            unit='B',
            unit_scale=True,
            desc=f"解压 {os.path.basename(bz2_path)}",
            disable=not show_progress
        )
        
        with bz2.open(bz2_path, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                chunk_size = 8192
                while True:
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    pbar.update(len(chunk))
        
        pbar.close()
        self.logger.info(f"✅ 解压完成: {output_file}")

    def _compress_xz(self, source: str, output_path: str,
                    show_progress: bool) -> None:
        try:
            import lzma
        except ImportError:
            raise ImportError("需要安装 pylzma 或使用 Python 3.3+ 内置 lzma 模块")
        
        if not os.path.isfile(source):
            raise ValueError(f"XZ压缩只支持单个文件: {source}")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        file_size = os.path.getsize(source)
        pbar = tqdm(
            total=file_size,
            unit='B',
            unit_scale=True,
            desc=f"压缩 {os.path.basename(source)}",
            disable=not show_progress
        )
        
        with open(source, 'rb') as f_in:
            with lzma.open(output_path, 'wb') as f_out:
                chunk_size = 8192
                while True:
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    pbar.update(len(chunk))
        
        pbar.close()
        self.logger.info(f"✅ 压缩完成: {output_path}")

    def _extract_xz(self, xz_path: str, extract_to: str,
                    show_progress: bool) -> None:
        try:
            import lzma
        except ImportError:
            raise ImportError("需要安装 pylzma 或使用 Python 3.3+ 内置 lzma 模块")
        
        os.makedirs(extract_to, exist_ok=True)
        
        output_file = os.path.join(extract_to, os.path.basename(xz_path).replace('.xz', ''))
        file_size = os.path.getsize(xz_path)
        
        pbar = tqdm(
            total=file_size,
            unit='B',
            unit_scale=True,
            desc=f"解压 {os.path.basename(xz_path)}",
            disable=not show_progress
        )
        
        with lzma.open(xz_path, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                chunk_size = 8192
                while True:
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    pbar.update(len(chunk))
        
        pbar.close()
        self.logger.info(f"✅ 解压完成: {output_file}")

    def _compress_7z(self, source: str, output_path: str,
                    compression_level: int,
                    exclude_dirs: Optional[List[str]],
                    exclude_exts: Optional[List[str]],
                    show_progress: bool,
                    password: Optional[str]) -> None:
        try:
            import py7zr
        except ImportError:
            raise ImportError("需要安装 py7zr: pip install py7zr")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        exclude_dirs = set(exclude_dirs or [])
        exclude_exts = set(ext.lower() for ext in (exclude_exts or []))
        
        file_paths = []
        if os.path.isfile(source):
            file_paths.append(source)
        else:
            for root, dirs, files in os.walk(source):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                for file in files:
                    if exclude_exts and os.path.splitext(file)[1].lower() in exclude_exts:
                        continue
                    
                    file_path = os.path.join(root, file)
                    file_paths.append(file_path)
        
        # 适配不同版本的 py7zr
        try:
            # 尝试使用 compression_level 参数（较新版本）
            with py7zr.SevenZipFile(
                output_path, 'w',
                compression_level=compression_level,
                password=password
            ) as archive:
                self._write_7z_files(archive, file_paths, source, show_progress)
        except TypeError:
            # 回退到不使用 compression_level 参数（较旧版本）
            with py7zr.SevenZipFile(
                output_path, 'w',
                password=password
            ) as archive:
                self._write_7z_files(archive, file_paths, source, show_progress)
        
        self.logger.info(f"✅ 压缩完成: {output_path}")
    
    def _write_7z_files(self, archive, file_paths, source, show_progress):
        """
        向 7z 归档写入文件
        
        Args:
            archive: py7zr.SevenZipFile 实例
            file_paths: 文件路径列表
            source: 源路径
            show_progress: 是否显示进度条
        """
        pbar = tqdm(
            total=len(file_paths),
            unit='file',
            desc=f"压缩 {os.path.basename(source)}",
            disable=not show_progress
        )
        
        for file_path in file_paths:
            if os.path.isfile(source):
                archive.write(file_path, os.path.basename(file_path))
            else:
                archive.write(file_path, os.path.relpath(file_path, source))
            pbar.update(1)
        
        pbar.close()

    def _extract_7z(self, archive_path: str, extract_to: str,
                    show_progress: bool,
                    password: Optional[str]) -> None:
        try:
            import py7zr
        except ImportError:
            raise ImportError("需要安装 py7zr: pip install py7zr")
        
        os.makedirs(extract_to, exist_ok=True)
        self.logger.info(f"准备解压: {archive_path} → {extract_to}")
        
        with py7zr.SevenZipFile(archive_path, mode='r', password=password) as archive:
            file_list = archive.getnames()
            
            pbar = tqdm(
                total=len(file_list),
                unit='file',
                desc=f"解压 {os.path.basename(archive_path)}",
                disable=not show_progress
            )
            
            archive.extractall(path=extract_to)
            pbar.update(len(file_list))
            pbar.close()
        
        self.logger.info(f"✅ 解压完成: {extract_to}")

    def _compress_rar(self, source: str, output_path: str,
                     compression_level: int,
                     exclude_dirs: Optional[List[str]],
                     exclude_exts: Optional[List[str]],
                     show_progress: bool,
                     password: Optional[str]) -> None:
        try:
            import rarfile
        except ImportError:
            raise ImportError("需要安装 rarfile: pip install rarfile")
        
        if not os.path.isdir(source):
            raise ValueError(f"RAR压缩只支持目录: {source}")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        exclude_dirs = set(exclude_dirs or [])
        exclude_exts = set(ext.lower() for ext in (exclude_exts or []))
        
        file_paths = []
        total_size = 0
        
        for root, dirs, files in os.walk(source):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if exclude_exts and os.path.splitext(file)[1].lower() in exclude_exts:
                    continue
                
                file_path = os.path.join(root, file)
                file_paths.append(file_path)
                total_size += os.path.getsize(file_path)
        
        with rarfile.RarFile(output_path, 'w') as rf:
            pbar = tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                desc=f"压缩 {os.path.basename(source)}",
                disable=not show_progress
            )
            
            for file_path in file_paths:
                arcname = os.path.relpath(file_path, source)
                rf.write(file_path, arcname=arcname)
                pbar.update(os.path.getsize(file_path))
            
            pbar.close()
        
        self.logger.info(f"✅ 压缩完成: {output_path}")

    def _extract_rar(self, rar_path: str, extract_to: str,
                    show_progress: bool,
                    password: Optional[str]) -> None:
        try:
            import rarfile
        except ImportError:
            raise ImportError("需要安装 rarfile: pip install rarfile")
        
        os.makedirs(extract_to, exist_ok=True)
        self.logger.info(f"准备解压: {rar_path} → {extract_to}")
        
        with rarfile.RarFile(rar_path, 'r') as rf:
            file_list = rf.namelist()
            
            pbar = tqdm(
                total=len(file_list),
                unit='file',
                desc=f"解压 {os.path.basename(rar_path)}",
                disable=not show_progress
            )
            
            rf.extractall(extract_to, pwd=password)
            pbar.update(len(file_list))
            pbar.close()
        
        self.logger.info(f"✅ 解压完成: {extract_to}")

    def _get_archive_format(self, archive_path: str) -> CompressionFormat:
        """
        根据文件扩展名识别压缩格式
        
        Args:
            archive_path (str): 压缩文件路径
        
        Returns:
            CompressionFormat: 识别出的压缩格式
        
        Raises:
            ValueError: 如果无法识别压缩格式
        """
        filename = os.path.basename(archive_path).lower()
        
        if filename.endswith('.7z'):
            return CompressionFormat.SEVEN_Z
        elif filename.endswith('.rar'):
            return CompressionFormat.RAR
        elif filename.endswith('.tar.gz') or filename.endswith('.tgz'):
            return CompressionFormat.TAR_GZ
        elif filename.endswith('.tar.bz2') or filename.endswith('.tbz2'):
            return CompressionFormat.TAR_BZ2
        elif filename.endswith('.tar.xz') or filename.endswith('.txz'):
            return CompressionFormat.TAR_XZ
        elif filename.endswith('.tar'):
            return CompressionFormat.TAR
        elif filename.endswith('.gz'):
            return CompressionFormat.GZ
        elif filename.endswith('.bz2'):
            return CompressionFormat.BZ2
        elif filename.endswith('.xz'):
            return CompressionFormat.XZ
        elif filename.endswith('.zip'):
            return CompressionFormat.ZIP
        else:
            raise ValueError(f"无法识别的压缩格式: {archive_path}")
