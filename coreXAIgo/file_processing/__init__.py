"""文件处理模块

提供多种文件处理功能，包括：
- 基础文件操作（basic）
- 压缩文件管理（archive）
- 标注格式转换（annotation_convert）
- 图像裁剪（image_crop）
- VOC XML处理（voc_xml_deal）
- 数据预处理（data_preprocessing）
"""
from .basic import *
from .archive import CompressionFormat, ArchiveManager
from .annotation_convert import *
from .image_crop import *
from .voc_xml_deal import *
from .data_preprocessing import YOLODataPreprocessor, RotationType

basic_all = [
    'get_files',
    'get_filenames',
    'get_duplicate_files',
    'generate_sequential_filename',
    'copy_file',
    'move_file',
    'copy_files',
    'move_files',
    'get_missing_files',
    'randomly_select_files'
]

archive_all = [
    'CompressionFormat',
    'ArchiveManager'
]

annotation_convert_all = [
    "YOLOAnnotation",
    "LabelMeAnnotation",
    "VOCAnnotation",
    "AnnotationConverter",
]

image_crop_all = [
    'resize_box_to_target',
    'sliding_crop_image',
    'TaggedImageCrop',
    'batch_multithreaded_image_cropping'
]

voc_xml_deal_all = [
    'VOCXMLProcessor'
]

data_preprocessing_all = [
    'YOLODataPreprocessor',
    'RotationType'
]

__all__ = archive_all + annotation_convert_all + basic_all + image_crop_all + voc_xml_deal_all + data_preprocessing_all
