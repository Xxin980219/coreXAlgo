# coreXAlgo Documentation  

<div class="hero-section">
  <div class="hero-content">
    <h1>coreXAlgo</h1>
    <p class="subtitle">算法开发工具库</p>
    <p class="description">一个为算法工程师打造的综合性工具集合，提供高效、可靠的技术支持</p>
    <div class="version-badge">
      <span class="badge">v0.5.0</span>
    </div>
  </div>
</div>

<style>
  .hero-section {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem;
    border-radius: 12px;
    margin-bottom: 2rem;
    color: white;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }
  
  .hero-content {
    max-width: 800px;
    margin: 0 auto;
    text-align: center;
  }
  
  .hero-content h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
    font-weight: bold;
  }
  
  .subtitle {
    font-size: 1.2rem;
    margin-bottom: 1rem;
    opacity: 0.9;
  }
  
  .description {
    font-size: 1rem;
    margin-bottom: 1.5rem;
    opacity: 0.8;
  }
  
  .version-badge {
    display: inline-block;
    background: rgba(255, 255, 255, 0.2);
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.9rem;
  }
  
  .feature-card {
    border-radius: 8px;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
  }
  
  .feature-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
  }
  
  .feature-icon {
    font-size: 2rem;
    margin-bottom: 1rem;
  }
  
  .grid-container {
    gap: 1.5rem;
  }
  
  .info-section {
    background: #f8f9fa;
    padding: 1.5rem;
    border-radius: 8px;
    margin-bottom: 2rem;
  }
  
  .info-item {
    margin-bottom: 0.5rem;
  }
  
  .info-label {
    font-weight: 600;
    margin-right: 0.5rem;
  }
</style>

该算法开发工具库是一个根据本人自身算法工程师日常工作而构建的综合性工具集合。

本库整合了算法开发过程中常用的核心功能模块：计算机视觉处理技术、文件操作工具和基础实用函数。通过模块化的设计，为算法研发提供高效、可靠的技术支持，显著提升开发效率，减少重复性工作，确保代码质量和可维护性。

## 📋 项目概览

:::{grid}

:::{grid-item-card} 🎯 核心功能
:class-card: feature-card

- **计算机视觉**：图像处理、标注工具、目标检测
- **文件处理**：批量操作、格式转换、数据管理
- **基础工具**：日志管理、网络传输、数据库操作
- **数据可视化**：目标检测结果展示、标注可视化
:::

:::{grid-item-card} 🚀 技术特点
:class-card: feature-card

- **模块化设计**：清晰的代码结构，易于扩展
- **性能优化**：多线程支持，批量处理
- **错误处理**：完善的异常捕获机制
- **文档完善**：详细的使用示例和API文档
- **跨平台兼容**：支持Windows、Linux、macOS
:::

:::{grid-item-card} 💡 应用场景
:class-card: feature-card

- **目标检测**：数据集准备、标注转换、结果可视化
- **图像分割**：多边形处理、掩码操作、数据增强
- **工业缺陷检测**：图像裁剪、缺陷分类、统计分析
- **数据管道**：文件管理、批量处理、网络传输
:::

::::

## 📁 项目架构

:::{dropdown} {octicon}`checklist;1em`&nbsp; 目录结构
:animate: fade-in-slide-down
:open:

```
coreXAlgo/
├── __init__.py              # 主入口文件
├── version.py               # 版本管理
├── utils/                   # 基础工具模块
│   ├── basic.py            # 基础工具函数
│   ├── bbox_util.py        # 边界框处理工具
│   ├── constants.py        # 常量定义
│   ├── ftp_client.py       # FTP客户端
│   ├── sftp_client.py      # SFTP客户端
│   ├── mt_db_client.py     # 多线程数据库客户端
│   └── mt_file_downloader.py # 多线程文件下载器
├── adv_cv/                 # 高级计算机视觉模块
│   └── basic.py           # 图像处理功能
└── file_processing/         # 文件处理模块
    ├── basic.py           # 文件操作工具
    ├── archive.py         # 压缩解压管理
    ├── annotation_convert.py # 标注格式转换
    ├── data_preprocessing.py # 数据预处理
    ├── image_crop.py      # 图像裁剪处理
    └── voc_xml_deal.py   # VOC XML处理
```
:::

## 📊 版本信息

:::{dropdown} {octicon}`info;1em`&nbsp; 版本详情
:animate: fade-in-slide-down
:open:

<div class="info-section">
  <div class="info-item">
    <span class="info-label">当前版本:</span> 0.5.0
  </div>
  <div class="info-item">
    <span class="info-label">Python 兼容性:</span> ≥ 3.8
  </div>
  <div class="info-item">
    <span class="info-label">更新日期:</span> 2026-02-27
  </div>
  <div class="info-item">
    <span class="info-label">作者:</span> Xxin_BOE
  </div>
  <div class="info-item">
    <span class="info-label">主要领域:</span> 计算机视觉、数据处理
  </div>
</div>
:::

## 📚 模块文档

::::{grid}

:::{grid-item-card} {octicon}`rocket` Adv_cv Module
:link: adv_cv/index
:link-type: doc
:class-card: feature-card

常用的计算机视觉技术和处理方法,以及对OpenCV函数的改进版
:::

:::{grid-item-card} {octicon}`file` File_processing Module
:link: file_processing/index
:link-type: doc
:class-card: feature-card

常用的文件处理功能函数，特别是针对标注数据和图像处理的自定义工具函数
:::

:::{grid-item-card} {octicon}`hubot` Utils Module
:link: utils/index
:link-type: doc
:class-card: feature-card

常用的基础工具函数和类，包括网络传输、数据库操作、日志管理等
:::

::::

## 🔧 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/coreXAlgo.git

# 安装依赖
pip install -r requirements.txt

# 安装库
pip install -e .
```

### 基本使用

```python
from coreXAlgo.utils import set_all_seed, colorstr
from coreXAlgo.file_processing import get_files, clean_unmatched_files

# 设置随机种子
set_all_seed(42)

# 输出彩色日志
print(colorstr('green', 'bold', '核心功能初始化完成'))

# 查找文件
image_files = get_files('./images', ['.jpg', '.png'])
print(f"找到 {len(image_files)} 个图片文件")

# 清理不匹配的文件
clean_unmatched_files(
    folder_path='./dataset',
    label_ext='.txt',
    dry_run=True
)
```

## 🎯 主要特性

- **完善的文档**：详细的API文档和使用示例
- **类型提示**：全面的类型注解，提高代码可读性
- **错误处理**：完善的异常处理机制
- **性能优化**：多线程支持，批量处理
- **跨平台兼容**：支持Windows、Linux、macOS
- **模块化设计**：清晰的代码结构，易于扩展
- **生产级质量**：代码规范，测试覆盖完善

## 📝 版本更新日志

### 版本 0.5.0
- 为 `file_processing/basic.py` 中的函数添加了详细的文档字符串和使用示例
- 优化了 `randomly_select_files` 函数的代码结构
- 改进了 `clean_unmatched_files` 函数的文档
- 更新了项目文档和分析报告

### 版本 0.4.9
- 修复了 `sftp_client.py` 中下载成功数量统计错误的问题
- 优化了 `sftp_client.py` 的异常处理逻辑
- 为 `mt_file_downloader.py` 添加了缺失的 `logging` 模块导入
- 改进了 `sftp_client.py` 的连接池管理

### 版本 0.4.8
- 重构了文件处理模块，提升了性能
- 优化了工具模块，包括 bbox_util.py、ftp_client.py 和 sftp_client.py
- 新增了 mt_file_downloader.py 模块
- 改进了数据库客户端的查询性能和错误处理

### 版本 0.4.7
- 修复了 SQLAlchemy 版本兼容性问题
- 优化了 FTP/SFTP 客户端的错误处理
- 改进了目标检测可视化的性能

### 版本 0.4.6
- 初始版本发布
- 包含核心工具模块、高级计算机视觉模块和文件处理模块

```{toctree}
:caption: Modules
:hidden:

adv_cv/index
file_processing/index
utils/index
```