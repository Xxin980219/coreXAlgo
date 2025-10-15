import os
import xml.etree.ElementTree as ET
from typing import Union, List, Set

from tqdm import tqdm

from ..utils.basic import set_logging


def update_xml_categories(xml_path, source_categories, target_categories, verbose=False):
    """
    更新XML标注文件中的类别名称(用于修改PASCAL VOC格式XML标注文件)

    Args:
        xml_path (str): XML标注文件的完整路径，支持相对或绝对路径
        source_categories (List[str]): 需要被替换的原始类别名称列表
                                      Example: ['PT', 'AB', 'defect_old']
        target_categories (List[str]): 替换后的目标类别名称列表，必须与source_categories
                                      一一对应
                                      Example: ['PT_new', 'AB_new', 'defect_new']

    Example:
        >>> # 将XML文件中的'PT'替换为'PT_new'，'AB'替换为'AB_new'
        >>> update_xml_categories('image.xml', ['PT', 'AB'], ['PT_new', 'AB_new'])

        >>> # 批量处理目录下所有XML文件
        >>> for xml_file in glob.glob('annotations/*.xml'):
        >>>     update_xml_categories(xml_file, ['old_class'], ['new_class'])
    """
    logger = set_logging("update_xml_categories", verbose=verbose)

    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"XML file not found: {xml_path}")

    # 解析 XML 文件
    tree = ET.parse(xml_path)
    updated_count = 0

    # 遍历 XML 文件中的所有 <name> 标签，修改对应的类别名
    for obj in tree.findall('object'):
        name = obj.find('name')
        if name is not None and name.text in source_categories:
            index = source_categories.index(name.text)
            logger.info(f"Updating category: '{source_categories[index]}' → '{target_categories[index]}'")
            name.text = target_categories[index]  # 修改类别名
            updated_count += 1

    # 如果有更新才写回文件
    if updated_count > 0:
        # 写回修改后的XML文件
        try:
            tree.write(xml_path, encoding='utf-8', xml_declaration=True)
        except Exception as e:
            raise IOError(f"Failed to write XML file: {e}")


def get_images_without_annotations(xml_path, verbose=False):
    """
    提取XML文件中无标注的图片（不含扩展名）

    此函数用于检测没有标注对象的XML文件，通常用于数据清洗和质量控制。

    Args:
        xml_path (str): XML标注文件的完整路径

    Returns:
        str or None: 如果没有标注对象，返回文件名（不含扩展名）；否则返回None

    Example:
        >>> # 获取单个XML文件的无标注状态
        >>> result = get_images_without_annotations('image.xml')
        >>> if result:
        >>>     print(f"Image without annotations: {result}")

        >>> # 批量检测目录下所有XML文件
        >>> empty_files = []
        >>> for xml_file in glob.glob('annotations/*.xml'):
        >>>     result = get_images_without_annotations(xml_file)
        >>>     if result:
        >>>         empty_files.append(result)
    """
    logger = set_logging("get_images_without_annotations", verbose=verbose)
    try:
        # 解析 XML 文件
        tree = ET.parse(xml_path)

        if len(tree.findall('object')) == 0:
            filename_without_extension = os.path.splitext(os.path.basename(xml_path))[0]
            return filename_without_extension
        return None
    except Exception as e:
        logger.error(f"Error processing {xml_path}: {str(e)}")
        return None


def get_defect_classes_and_nums(xml_dir, verbose=False):
    """
    从XML标注文件中提取所有缺陷类别及其出现次数统计

    此函数会遍历指定目录下的所有XML文件，统计每个缺陷类别的出现次数，
    返回一个包含类别和对应数量的字典。

    Args:
        xml_dir (str): 包含XML标注文件的目录路径

    Returns:
        Dict[str, int]: 类别名称到出现次数的映射字典

    Example:
        >>> # 统计目录下所有XML文件的缺陷类别
        >>> stats = get_defect_classes_and_nums('annotations/')
        >>> print("Defect statistics:")
        >>> for class_name, count in stats.items():
        >>>     print(f"  {class_name}: {count}")
    """
    logger = set_logging("get_images_without_annotations", verbose=verbose)

    classes_and_nums = {}
    from .basic import get_files
    xml_file_paths = get_files(xml_dir, '.xml')
    for xml_path in tqdm(xml_file_paths, desc="Defect category and quantity statistics"):
        if not os.path.exists(xml_path):
            logger.warning(f"Warning: File does not exist, skipping processing: {xml_path}")

        try:
            tree = ET.parse(xml_path)
            for obj in tree.findall('object'):
                class_name = obj.find('name').text
                if class_name not in classes_and_nums:
                    classes_and_nums[class_name] = 1  # 新类别初始化为1
                else:
                    classes_and_nums[class_name] += 1  # 已有类别计数加1
        except ET.ParseError as e:
            logger.warnin(f"Warning: XML parsing error, skipping file {xml_path}: {str(e)}")
            continue
        except Exception as e:
            logger.warning(f"Warning: An unknown error occurred while processing file {xml_path}: {str(e)}")
            continue
    return classes_and_nums


def get_images_with_specific_categories(xml_path, target_categories, verbose=False):
    """
    提取XML文件中仅包含指定类别的图片（不含扩展名）

    此函数用于筛选包含特定类别的图片文件，支持单个类别、列表或集合形式的输入。

    Args:
        xml_path (str): XML标注文件的完整路径
        target_categories (str|List[str]|Set[str]): 需要查找的目标类别，
                                                    可以是字符串、列表或集合

    Returns:
        str or None: 如果包含目标类别，返回文件名（不含扩展名）；否则返回None

    Example:
        >>> # 查找包含'person'类别的图片
        >>> result = get_images_with_specific_categories('image.xml', 'person')

        >>> # 查找包含'person'或'car'类别的图片
        >>> result = get_images_with_specific_categories('image.xml', ['person', 'car'])
    """
    logger = set_logging("get_images_without_annotations", verbose=verbose)
    try:
        if isinstance(target_categories, str):
            target_categories_set = {target_categories}
        else:
            target_categories_set = set(target_categories)
        # 解析 XML 文件
        tree = ET.parse(xml_path)

        existing_categories = {obj.findtext('name') for obj in tree.findall('object') if obj.find('name') is not None}
        if target_categories_set & existing_categories:
            filename_without_extension = os.path.splitext(os.path.basename(xml_path))[0]
            return filename_without_extension
        return None
    except Exception as e:
        logger.error(f"Error processing {xml_path}: {str(e)}")
        return None
