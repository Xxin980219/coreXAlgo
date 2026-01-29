import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Union, Set
from tqdm import tqdm
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from ..utils.basic import set_logging


class VOCXMLProcessor:
    """
    VOC XML 标注文件处理器
    
    用于处理 VOC 格式的 XML 标注文件，提供以下功能：
    1. 更新 XML 文件中的类别名称
    2. 提取无标注的图片
    3. 统计缺陷类别及其出现次数
    4. 提取包含特定类别的图片
    5. 批量处理多个 XML 文件
    6. 多线程并行处理，提高效率
    7. 获取详细的标注统计信息
    
    Example:
        >>> # 1. 创建 VOC XML 处理器实例
        >>> from coreXAlgo.file_processing.voc_xml_deal import VOCXMLProcessor
        >>> processor = VOCXMLProcessor(verbose=True)
        >>> 
        >>> # 2. 更新 XML 文件中的类别名称
        >>> processor.update_categories(
        ...     'annotations/image.xml',
        ...     ['old_class1', 'old_class2'],
        ...     ['new_class1', 'new_class2']
        ... )
        
        >>> # 3. 提取无标注的图片
        >>> result = processor.get_images_without_annotations('annotations/image.xml')
        >>> if result:
        ...     print(f"Image without annotations: {result}")
        
        >>> # 4. 统计缺陷类别及其出现次数
        >>> stats = processor.get_defect_classes_and_nums('annotations/')
        >>> print("Defect statistics:")
        >>> for class_name, count in stats.items():
        ...     print(f"  {class_name}: {count}")
        
        >>> # 5. 提取包含特定类别的图片
        >>> # 单个类别
        >>> result = processor.get_images_with_specific_categories('annotations/image.xml', 'person')
        >>> # 多个类别
        >>> result = processor.get_images_with_specific_categories('annotations/image.xml', ['person', 'car'])
        
        >>> # 6. 批量处理目录中的所有 XML 文件
        >>> def process_func(xml_path):
        ...     return processor.get_images_without_annotations(xml_path)
        >>> 
        >>> empty_files = processor.batch_process('annotations/', process_func)
        >>> print(f"Empty files: {empty_files}")
        
        >>> # 7. 多线程批量处理
        >>> empty_files = processor.batch_process_with_threads('annotations/', process_func, max_workers=4)
        
        >>> # 8. 获取详细的标注统计信息
        >>> annotation_stats = processor.get_annotation_statistics('annotations/')
        >>> print(f"Total files: {annotation_stats['total_files']}")
        >>> print(f"Total objects: {annotation_stats['total_objects']}")
        >>> print(f"Average objects per file: {annotation_stats['avg_objects_per_file']}")
        >>> print("Class counts:")
        >>> for class_name, count in annotation_stats['class_counts'].items():
        ...     print(f"  {class_name}: {count}")
        >>> print(f"Empty files: {annotation_stats['empty_files']}")
    """
    
    def __init__(self, verbose: bool = False):
        """
        初始化 VOC XML 处理器
        
        Args:
            verbose: 是否启用详细日志
        """
        self.verbose = verbose
        self.logger = set_logging("VOCXMLProcessor", verbose=verbose)
    
    def update_categories(self, xml_path: str, source_categories: List[str], target_categories: List[str]) -> int:
        """
        更新 XML 文件中的类别名称
        
        Args:
            xml_path: XML 标注文件的完整路径
            source_categories: 需要被替换的原始类别名称列表
            target_categories: 替换后的目标类别名称列表
        
        Returns:
            int: 更新的类别数量
        
        Raises:
            FileNotFoundError: 当 XML 文件不存在时
            ValueError: 当源类别和目标类别列表长度不匹配时
        """
        xml_path_obj = Path(xml_path)
        if not xml_path_obj.exists():
            raise FileNotFoundError(f"XML file not found: {xml_path}")
        
        if len(source_categories) != len(target_categories):
            raise ValueError("Source and target categories must have the same length")
        
        # 解析 XML 文件
        tree = ET.parse(xml_path)
        updated_count = 0
        
        # 遍历 XML 文件中的所有 <name> 标签，修改对应的类别名
        for obj in tree.findall('object'):
            name = obj.find('name')
            if name is not None and name.text in source_categories:
                index = source_categories.index(name.text)
                self.logger.info(f"Updating category: '{source_categories[index]}' → '{target_categories[index]}'")
                name.text = target_categories[index]
                updated_count += 1
        
        # 如果有更新才写回文件
        if updated_count > 0:
            try:
                tree.write(xml_path, encoding='utf-8', xml_declaration=True)
            except Exception as e:
                raise IOError(f"Failed to write XML file: {e}")
        
        return updated_count
    
    def get_images_without_annotations(self, xml_path: str) -> Optional[str]:
        """
        提取无标注的图片
        
        Args:
            xml_path: XML 标注文件的完整路径
        
        Returns:
            Optional[str]: 如果没有标注对象，返回文件名（不含扩展名）；否则返回 None
        """
        try:
            xml_path_obj = Path(xml_path)
            if not xml_path_obj.exists():
                self.logger.warning(f"XML file not found: {xml_path}")
                return None
            
            # 解析 XML 文件
            tree = ET.parse(xml_path)
            
            if len(tree.findall('object')) == 0:
                return xml_path_obj.stem
            return None
        except Exception as e:
            self.logger.error(f"Error processing {xml_path}: {str(e)}")
            return None
    
    def get_defect_classes_and_nums(self, xml_dir: str) -> Dict[str, int]:
        """
        统计缺陷类别及其出现次数
        
        Args:
            xml_dir: 包含 XML 标注文件的目录路径
        
        Returns:
            Dict[str, int]: 类别名称到出现次数的映射字典
        """
        classes_and_nums = {}
        xml_dir_obj = Path(xml_dir)
        
        if not xml_dir_obj.exists():
            self.logger.warning(f"Directory not found: {xml_dir}")
            return classes_and_nums
        
        # 获取目录下所有 XML 文件
        xml_files = list(xml_dir_obj.glob('*.xml'))
        
        for xml_path in tqdm(xml_files, desc="Defect category and quantity statistics"):
            try:
                tree = ET.parse(xml_path)
                for obj in tree.findall('object'):
                    name_elem = obj.find('name')
                    if name_elem is not None and name_elem.text:
                        class_name = name_elem.text
                        if class_name not in classes_and_nums:
                            classes_and_nums[class_name] = 1
                        else:
                            classes_and_nums[class_name] += 1
            except ET.ParseError as e:
                self.logger.warning(f"XML parsing error, skipping file {xml_path}: {str(e)}")
                continue
            except Exception as e:
                self.logger.warning(f"Error processing file {xml_path}: {str(e)}")
                continue
        
        return classes_and_nums
    
    def get_images_with_specific_categories(self, xml_path: str, target_categories: Union[str, List[str], Set[str]]) -> Optional[str]:
        """
        提取包含特定类别的图片
        
        Args:
            xml_path: XML 标注文件的完整路径
            target_categories: 需要查找的目标类别
        
        Returns:
            Optional[str]: 如果包含目标类别，返回文件名（不含扩展名）；否则返回 None
        """
        try:
            xml_path_obj = Path(xml_path)
            if not xml_path_obj.exists():
                self.logger.warning(f"XML file not found: {xml_path}")
                return None
            
            # 标准化目标类别为集合
            if isinstance(target_categories, str):
                target_categories_set = {target_categories}
            else:
                target_categories_set = set(target_categories)
            
            # 解析 XML 文件
            tree = ET.parse(xml_path)
            
            existing_categories = {
                obj.findtext('name') for obj in tree.findall('object') 
                if obj.find('name') is not None
            }
            
            if target_categories_set & existing_categories:
                return xml_path_obj.stem
            return None
        except Exception as e:
            self.logger.error(f"Error processing {xml_path}: {str(e)}")
            return None
    
    def batch_process(self, xml_dir: str, process_func, *args, **kwargs) -> List:
        """
        批量处理目录中的 XML 文件
        
        Args:
            xml_dir: 包含 XML 标注文件的目录路径
            process_func: 处理单个 XML 文件的函数
            *args: 传递给处理函数的位置参数
            **kwargs: 传递给处理函数的关键字参数
        
        Returns:
            List: 处理结果列表
        """
        xml_dir_obj = Path(xml_dir)
        if not xml_dir_obj.exists():
            self.logger.warning(f"Directory not found: {xml_dir}")
            return []
        
        # 获取目录下所有 XML 文件
        xml_files = list(xml_dir_obj.glob('*.xml'))
        results = []
        
        for xml_file in tqdm(xml_files, desc="Batch processing XML files"):
            result = process_func(str(xml_file), *args, **kwargs)
            if result:
                results.append(result)
        
        return results
    
    def batch_process_with_threads(self, xml_dir: str, process_func, *args, max_workers: int = 4, **kwargs) -> List:
        """
        多线程批量处理目录中的 XML 文件
        
        Args:
            xml_dir: 包含 XML 标注文件的目录路径
            process_func: 处理单个 XML 文件的函数
            *args: 传递给处理函数的位置参数
            max_workers: 最大线程数
            **kwargs: 传递给处理函数的关键字参数
        
        Returns:
            List: 处理结果列表
        """
        xml_dir_obj = Path(xml_dir)
        if not xml_dir_obj.exists():
            self.logger.warning(f"Directory not found: {xml_dir}")
            return []
        
        # 获取目录下所有 XML 文件
        xml_files = list(xml_dir_obj.glob('*.xml'))
        results = []
        
        # 使用多线程处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for xml_file in xml_files:
                futures.append(executor.submit(process_func, str(xml_file), *args, **kwargs))
            
            # 收集结果
            for future in tqdm(futures, desc="Multi-thread processing XML files"):
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"Error in thread: {str(e)}")
        
        return results
    
    def get_annotation_statistics(self, xml_dir: str) -> Dict[str, Any]:
        """
        获取标注统计信息
        
        Args:
            xml_dir: 包含 XML 标注文件的目录路径
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        xml_dir_obj = Path(xml_dir)
        if not xml_dir_obj.exists():
            self.logger.warning(f"Directory not found: {xml_dir}")
            return {}
        
        # 获取目录下所有 XML 文件
        xml_files = list(xml_dir_obj.glob('*.xml'))
        total_files = len(xml_files)
        total_objects = 0
        class_counts = {}
        empty_files = []
        
        for xml_file in tqdm(xml_files, desc="Calculating annotation statistics"):
            try:
                tree = ET.parse(xml_file)
                objects = tree.findall('object')
                object_count = len(objects)
                total_objects += object_count
                
                if object_count == 0:
                    empty_files.append(xml_file.stem)
                else:
                    for obj in objects:
                        name_elem = obj.find('name')
                        if name_elem is not None and name_elem.text:
                            class_name = name_elem.text
                            class_counts[class_name] = class_counts.get(class_name, 0) + 1
            except Exception as e:
                self.logger.warning(f"Error processing {xml_file}: {str(e)}")
                continue
        
        return {
            'total_files': total_files,
            'total_objects': total_objects,
            'class_counts': class_counts,
            'empty_files': empty_files,
            'avg_objects_per_file': total_objects / total_files if total_files > 0 else 0
        }
