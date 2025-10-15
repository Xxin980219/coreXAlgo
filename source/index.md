# coreXAlgo Documentation  

该算法开发工具库是一个根据本人自身算法工程师日常工作而构建的综合性工具集合。

本库整合了算法开发过程中常用的核心功能模块：计算机视觉处理技术、文件操作工具和基础实用函数。通过模块化的设计，为算法研发提供高效、可靠的技术支持，显著提升开发效率，减少重复性工作，确保代码质量和可维护性。

> 项目根目录/  
> ├── adv_cv/ # 计算机视觉技术改进模块  
> ├── file_processing/ # 文件处理功能模块  
> └── utils/ # 基础工具函数模块

```{toctree}
:caption: "contents"
:hidden:
:maxdepth: 1

adv_cv <adv_cv/index>
file_processing <file_processing/index>
utils <utils/index>
```

## 1. adv_cv 模块 - 计算机视觉技术

adv_cv 模块集成了算法开发中常用的计算机视觉技术和处理方法,以及对CV库部分常用函数的改进版

### 主要功能

- 基础函数: [basic.py](adv_cv/basic)
- 滤波处理（基于Tensor）
- 图像增强

## 2. file_processing 模块 - 文件处理

file_processing 模块为算法开发中常用的文件处理功能函数，特别是针对标注数据和图像处理的自定义工具函数。

### 主要功能

- 基础函数: [basic.py](file_processing/basic)
- 标注文件转换: [annotation_convert.py](file_processing/annotation_convert)
    - LabelMe ↔ VOC ↔ YOLO 标注格式互转
- 图像裁剪: [image_crop.py](file_processing/image_crop)
- xml文件处理: [voc_xml_deal.py](file_processing/voc_xml_deal)

## 3. utils 模块 - 基础工具函数

utils 模块包含算法开发中常用的基础工具函数和类，旨在提高开发效率，减少重复代码编写。

### 主要功能

- 基础函数: [basic.py](utils/basic)
- bbox框处理和可视化: [bbox_util.py](utils/bbox_util)
- FTP客户端下载和上传: [ftp_client.py](utils/ftp_client)
- 多线程并行下载ftp文件夹的所有文件: [mt_ftp_downloader.py](utils/mt_ftp_downloader)
- 轻量级多数据库查询客户端: [mt_db_client.py](utils/mt_db_client)