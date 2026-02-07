import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Union, Set, Any
from tqdm import tqdm
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from ..utils.basic import set_logging
from .basic import get_files


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
            xml_path: XML 标注文件的完整路径或包含 XML 文件的目录路径
            source_categories: 需要被替换的原始类别名称列表
            target_categories: 替换后的目标类别名称列表
        
        Returns:
            int: 更新的类别总数
        
        Raises:
            FileNotFoundError: 当 XML 文件不存在时
            ValueError: 当源类别和目标类别列表长度不匹配时
        
        Example:
            >>> # 更新单个文件中的类别
            >>> updated = processor.update_categories(
            ...     'annotations/image.xml',
            ...     ['old_class1', 'old_class2'],
            ...     ['new_class1', 'new_class2']
            ... )
            >>> print(f"Updated {updated} categories in the file")
            >>>
            >>> # 更新目录中所有文件的类别
            >>> updated = processor.update_categories(
            ...     'annotations/',
            ...     ['old_class1', 'old_class2'],
            ...     ['new_class1', 'new_class2']
            ... )
            >>> print(f"Updated {updated} categories in the directory")
        """
        if len(source_categories) != len(target_categories):
            raise ValueError("Source and target categories must have the same length")
        
        xml_path_obj = Path(xml_path)
        if not xml_path_obj.exists():
            raise FileNotFoundError(f"Path not found: {xml_path}")
        
        # 检查是否为目录
        if xml_path_obj.is_dir():
            # 获取目录下所有 XML 文件（包括子目录）
            xml_files = get_files(xml_path, '.xml')
            total_updated = 0
            
            for file_path in tqdm(xml_files, desc="Updating categories in XML files"):
                try:
                    updated = self._update_single_file_categories(file_path, source_categories, target_categories)
                    total_updated += updated
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {str(e)}")
                    continue
            
            return total_updated
        else:
            # 处理单个文件
            return self._update_single_file_categories(xml_path, source_categories, target_categories)
    
    def _update_single_file_categories(self, xml_path: str, source_categories: List[str], target_categories: List[str]) -> int:
        """
        更新单个 XML 文件中的类别名称
        
        Args:
            xml_path: XML 标注文件的完整路径
            source_categories: 需要被替换的原始类别名称列表
            target_categories: 替换后的目标类别名称列表
        
        Returns:
            int: 更新的类别数量
        """
        # 解析 XML 文件
        tree = ET.parse(xml_path)
        updated_count = 0
        
        # 遍历 XML 文件中的所有 <object> 标签，修改对应的类别名
        for obj in tree.findall('object'):
            name = obj.find('name')
            if name is not None and name.text in source_categories:
                index = source_categories.index(name.text)
                self.logger.info(f"Updating category in {xml_path}: '{source_categories[index]}' → '{target_categories[index]}'")
                name.text = target_categories[index]
                updated_count += 1
        
        # 如果有更新才写回文件
        if updated_count > 0:
            try:
                tree.write(xml_path, encoding='utf-8', xml_declaration=True)
            except Exception as e:
                raise IOError(f"Failed to write XML file: {e}")
        
        return updated_count
    
    def get_images_without_annotations(self, xml_path: str) -> Union[Optional[str], List[str]]:
        """
        提取无标注的图片
        
        Args:
            xml_path: XML 标注文件的完整路径或包含 XML 文件的目录路径
        
        Returns:
            Union[Optional[str], List[str]]:
                - 如果输入是单个文件：如果没有标注对象，返回文件名（不含扩展名）；否则返回 None
                - 如果输入是目录：返回所有无标注的图片名称列表（不含扩展名）
        
        Example:
            >>> # 处理单个文件
            >>> result = processor.get_images_without_annotations('annotations/image.xml')
            >>> if result:
            ...     print(f"Image without annotations: {result}")
            ... else:
            ...     print("Image has annotations")
            >>>
            >>> # 处理目录
            >>> empty_images = processor.get_images_without_annotations('annotations/')
            >>> print(f"Found {len(empty_images)} images without annotations")
            >>> for image in empty_images:
            ...     print(f"  - {image}")
        """
        try:
            xml_path_obj = Path(xml_path)
            if not xml_path_obj.exists():
                self.logger.warning(f"Path not found: {xml_path}")
                return None if xml_path_obj.is_file() else []
            
            # 检查是否为目录
            if xml_path_obj.is_dir():
                # 获取目录下所有 XML 文件（包括子目录）
                xml_files = get_files(xml_path, '.xml')
                result_list = []
                
                for file_path in tqdm(xml_files, desc="Processing XML files"):
                    try:
                        # 解析 XML 文件
                        tree = ET.parse(file_path)
                        
                        if len(tree.findall('object')) == 0:
                            result_list.append(Path(file_path).stem)
                    except Exception as e:
                        self.logger.error(f"Error processing {file_path}: {str(e)}")
                        continue
                
                return result_list
            else:
                # 处理单个文件
                # 解析 XML 文件
                tree = ET.parse(xml_path)
                
                if len(tree.findall('object')) == 0:
                    return xml_path_obj.stem
                return None
        except Exception as e:
            self.logger.error(f"Error processing {xml_path}: {str(e)}")
            return None if Path(xml_path).is_file() else []
    
    def get_defect_classes_and_nums(self, xml_dir: str) -> Dict[str, int]:
        """
        统计缺陷类别及其出现次数
        
        Args:
            xml_dir: 包含 XML 标注文件的目录路径
        
        Returns:
            Dict[str, int]: 类别名称到出现次数的映射字典
        
        Example:
            >>> # 统计目录中所有缺陷类别及其出现次数
            >>> stats = processor.get_defect_classes_and_nums('annotations/')
            >>> print("Defect statistics:")
            >>> for class_name, count in stats.items():
            ...     print(f"  {class_name}: {count}")
            >>>
            >>> # 按照出现次数排序
            >>> sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
            >>> print("\\n Defect statistics (sorted by count):")
            >>> for class_name, count in sorted_stats:
            ...     print(f"  {class_name}: {count}")
        """
        classes_and_nums = {}
        xml_dir_obj = Path(xml_dir)
        
        if not xml_dir_obj.exists():
            self.logger.warning(f"Directory not found: {xml_dir}")
            return classes_and_nums
        
        # 使用 get_files 函数获取目录下所有 XML 文件（支持递归搜索）
        xml_files = get_files(xml_dir, '.xml')
        
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
    
    def get_images_with_specific_categories(self, xml_path: str, target_categories: Union[str, List[str], Set[str]]) -> Union[Optional[str], List[str]]:
        """
        提取包含特定类别的图片
        
        Args:
            xml_path: XML 标注文件的完整路径或包含 XML 文件的目录路径
            target_categories: 需要查找的目标类别
        
        Returns:
            Union[Optional[str], List[str]]:
                - 如果输入是单个文件：如果包含目标类别，返回文件名（不含扩展名）；否则返回 None
                - 如果输入是目录：返回包含目标类别的所有图片名称列表（不含扩展名）
        
        Example:
            >>> # 处理单个文件 - 单个类别
            >>> result = processor.get_images_with_specific_categories('annotations/image.xml', 'person')
            >>> if result:
            ...     print(f"Image contains 'person' category: {result}")
            ... else:
            ...     print("Image does not contain 'person' category")
            >>>
            >>> # 处理单个文件 - 多个类别
            >>> result = processor.get_images_with_specific_categories('annotations/image.xml', ['person', 'car'])
            >>> if result:
            ...     print(f"Image contains at least one target category: {result}")
            ... else:
            ...     print("Image does not contain any target category")
            >>>
            >>> # 处理目录
            >>> images_with_person = processor.get_images_with_specific_categories('annotations/', 'person')
            >>> print(f"Found {len(images_with_person)} images with 'person' category")
            >>> for image in images_with_person:
            ...     print(f"  - {image}")
        """
        try:
            xml_path_obj = Path(xml_path)
            if not xml_path_obj.exists():
                self.logger.warning(f"Path not found: {xml_path}")
                return None if xml_path_obj.is_file() else []
            
            # 标准化目标类别为集合
            if isinstance(target_categories, str):
                target_categories_set = {target_categories}
            else:
                target_categories_set = set(target_categories)
            
            # 检查是否为目录
            if xml_path_obj.is_dir():
                # 获取目录下所有 XML 文件（包括子目录）
                xml_files = get_files(xml_path, '.xml')
                result_list = []
                
                for file_path in tqdm(xml_files, desc="Processing XML files"):
                    try:
                        # 解析 XML 文件
                        tree = ET.parse(file_path)
                        
                        existing_categories = {
                            obj.findtext('name') for obj in tree.findall('object') 
                            if obj.find('name') is not None
                        }
                        
                        if target_categories_set & existing_categories:
                            result_list.append(Path(file_path).stem)
                    except Exception as e:
                        self.logger.error(f"Error processing {file_path}: {str(e)}")
                        continue
                
                return result_list
            else:
                # 处理单个文件
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
            return None if Path(xml_path).is_file() else []
    
    def get_all_categories_and_images(self, xml_path: str) -> Optional[Dict[str, List[str]]]:
            """
            解析XML文件，返回该文件中包含的所有类别和对应的图片名

            Args:
                xml_path: XML标注文件的完整路径

            Returns:
                Optional[Dict[str, List[str]]]:
                    - 字典格式: {图片名: [类别1, 类别2, ...]}
                    - 如果解析失败或文件不存在，返回None

            Example:
                >>> # 解析单个XML文件
                >>> result = processor.get_all_categories_and_images('annotations/image.xml')
                >>> if result:
                ...     for image_name, categories in result.items():
                ...         print(f"Image: {image_name}, Categories: {categories}")
                ... else:
                ...     print("No valid data found in XML file")
            """
            try:
                xml_path_obj = Path(xml_path)
                if not xml_path_obj.exists():
                    self.logger.warning(f"XML file not found: {xml_path}")
                    return None

                # 解析XML文件
                tree = ET.parse(xml_path)
                root = tree.getroot()

                # 获取图片名（从filename标签）
                filename_elem = root.find('filename')
                if filename_elem is None or filename_elem.text is None:
                    self.logger.warning(f"No filename found in XML: {xml_path}")
                    return None

                image_name = filename_elem.text.strip()
                if not image_name:
                    self.logger.warning(f"Empty filename in XML: {xml_path}")
                    return None

                # 去除文件扩展名
                image_name = Path(image_name).stem

                # 查找所有的object标签
                objects = root.findall('object')
                if not objects:
                    self.logger.debug(f"No objects found in XML: {xml_path}")
                    return {image_name: []}  # 返回图片名和空类别列表

                # 收集所有不重复的类别
                categories = set()
                for obj in objects:
                    name_elem = obj.find('name')
                    if name_elem is not None and name_elem.text:
                        category = name_elem.text.strip()
                        if category:  # 确保类别名不为空
                            categories.add(category)

                return {image_name: list(categories)}

            except ET.ParseError as e:
                self.logger.error(f"XML parsing error in {xml_path}: {str(e)}")
                return None
            except Exception as e:
                self.logger.error(f"Error processing XML file {xml_path}: {str(e)}")
                return None

    def get_all_categories_and_images_batch(self, xml_dir: str) -> Dict[str, Dict[str, List[str]]]:
        """
        批量解析目录中的所有XML文件，返回所有文件的类别和图片信息

        Args:
            xml_dir: 包含XML标注文件的目录路径

        Returns:
            Dict[str, Dict[str, List[str]]]:
                - 字典格式: {XML文件路径: {图片名: [类别1, 类别2, ...]}}

        Example:
            >>> # 批量解析目录中的所有XML文件
            >>> all_data = processor.get_all_categories_and_images_batch('annotations/')
            >>> for xml_path, image_data in all_data.items():
            ...     for image_name, categories in image_data.items():
            ...         print(f"File: {Path(xml_path).name}, Image: {image_name}, Categories: {len(categories)}")
        """
        xml_dir_obj = Path(xml_dir)
        if not xml_dir_obj.exists():
            self.logger.warning(f"Directory not found: {xml_dir}")
            return {}

        # 获取目录下所有XML文件
        xml_files = get_files(xml_dir, '.xml')
        all_data = {}

        for xml_file in tqdm(xml_files, desc="Batch parsing XML files"):
            result = self.get_all_categories_and_images(xml_file)
            if result:
                all_data[xml_file] = result

        return all_data

    def get_images_by_category(self, xml_dir: str) -> Dict[str, List[str]]:
        """
        获取按类别分组的图片列表

        Args:
            xml_dir: 包含XML标注文件的目录路径

        Returns:
            Dict[str, List[str]]: 字典格式: {类别名: [图片名1, 图片名2, ...]}

        Example:
            >>> # 获取按类别分组的图片
            >>> category_images = processor.get_images_by_category('annotations/')
            >>> for category, images in category_images.items():
            ...     print(f"Category: {category}, Image count: {len(images)}")
            ...     for image in images[:3]:  # 显示前3个图片
            ...         print(f"  - {image}")
        """
        batch_data = self.get_all_categories_and_images_batch(xml_dir)
        category_images = {}

        for xml_path, image_data in batch_data.items():
            for image_name, categories in image_data.items():
                for category in categories:
                    if category not in category_images:
                        category_images[category] = []
                    category_images[category].append(image_name)

        return category_images

    def get_category_statistics(self, xml_dir: str) -> Dict[str, Dict[str, int]]:
        """
        获取详细的类别统计信息

        Args:
            xml_dir: 包含XML标注文件的目录路径

        Returns:
            Dict[str, Dict[str, int]]: 统计信息字典

        Example:
            >>> # 获取类别统计信息
            >>> stats = processor.get_category_statistics('annotations/')
            >>> print(f"Total categories: {stats['total_categories']}")
            >>> print(f"Total images: {stats['total_images']}")
            >>> print("\nCategory distribution:")
            >>> for category, count in stats['category_counts'].items():
            ...     print(f"  {category}: {count} images")
        """
        category_images = self.get_images_by_category(xml_dir)
        all_images = set()

        for images in category_images.values():
            all_images.update(images)

        # 计算每个类别的图片数量
        category_counts = {category: len(images) for category, images in category_images.items()}

        return {
            'total_categories': len(category_images),
            'total_images': len(all_images),
            'category_counts': category_counts,
            'category_images': category_images
        }



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
        
        Example:
            >>> # 定义处理函数
            >>> def process_func(xml_path):
            ...     return processor.get_images_without_annotations(xml_path)
            >>>
            >>> # 批量处理目录中的所有 XML 文件
            >>> empty_files = processor.batch_process('annotations/', process_func)
            >>> print(f"Found {len(empty_files)} images without annotations")
            >>>
            >>> # 使用带参数的处理函数
            >>> def process_with_category(xml_path, category):
            ...     return processor.get_images_with_specific_categories(xml_path, category)
            >>>
            >>> # 批量处理并传递参数
            >>> person_images = processor.batch_process('annotations/', process_with_category, 'person')
            >>> print(f"Found {len(person_images)} images with 'person' category")
        """
        xml_dir_obj = Path(xml_dir)
        if not xml_dir_obj.exists():
            self.logger.warning(f"Directory not found: {xml_dir}")
            return []
        
        # 获取目录下所有 XML 文件（包括子目录）
        xml_files = get_files(xml_dir, '.xml')
        results = []
        
        for xml_file in tqdm(xml_files, desc="Batch processing XML files"):
            result = process_func(xml_file, *args, **kwargs)
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
        
        Example:
            >>> # 定义处理函数
            >>> def process_func(xml_path):
            ...     return processor.get_images_without_annotations(xml_path)
            >>>
            >>> # 多线程批量处理目录中的所有 XML 文件
            >>> empty_files = processor.batch_process_with_threads('annotations/', process_func, max_workers=4)
            >>> print(f"Found {len(empty_files)} images without annotations")
            >>>
            >>> # 使用带参数的处理函数
            >>> def process_with_category(xml_path, category):
            ...     return processor.get_images_with_specific_categories(xml_path, category)
            >>>
            >>> # 多线程批量处理并传递参数
            >>> person_images = processor.batch_process_with_threads('annotations/', process_with_category, 'person', max_workers=8)
            >>> print(f"Found {len(person_images)} images with 'person' category")
        """
        xml_dir_obj = Path(xml_dir)
        if not xml_dir_obj.exists():
            self.logger.warning(f"Directory not found: {xml_dir}")
            return []
        
        # 获取目录下所有 XML 文件（包括子目录）
        xml_files = get_files(xml_dir, '.xml')
        results = []
        
        # 使用多线程处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for xml_file in xml_files:
                futures.append(executor.submit(process_func, xml_file, *args, **kwargs))
            
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
        
        Example:
            >>> # 获取标注统计信息
            >>> stats = processor.get_annotation_statistics('annotations/')
            >>> print(f"Total files: {stats['total_files']}")
            >>> print(f"Total objects: {stats['total_objects']}")
            >>> print(f"Average objects per file: {stats['avg_objects_per_file']:.2f}")
            >>> print("\\nClass counts:")
            >>> for class_name, count in stats['class_counts'].items():
            ...     print(f"  {class_name}: {count}")
            >>> print(f"\\nEmpty files: {len(stats['empty_files'])}")
            >>> for file in stats['empty_files']:
            ...     print(f"  - {file}")
        """
        xml_dir_obj = Path(xml_dir)
        if not xml_dir_obj.exists():
            self.logger.warning(f"Directory not found: {xml_dir}")
            return {}
        
        # 获取目录下所有 XML 文件（包括子目录）
        xml_files = get_files(xml_dir, '.xml')
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
                    empty_files.append(Path(xml_file).stem)
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
