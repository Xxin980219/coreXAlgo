# coreXAlgo Documentation

<div class="hero-section">
  <div class="hero-content">
    <div class="hero-badge">🚀 v0.5.2</div>
    <h1 class="hero-title">coreXAlgo</h1>
    <p class="hero-subtitle">算法开发工具库</p>
    <p class="hero-description">为算法工程师打造的综合性工具集合，提供高效、可靠的技术支持，显著提升开发效率</p>
    <div class="hero-buttons">
      <a href="#quick-start" class="btn btn-primary">开始使用</a>
      <a href="https://github.com/Xxin980219/coreXAlgo" class="btn btn-secondary" target="_blank">GitHub</a>
    </div>
  </div>
  <div class="hero-pattern"></div>
</div>

<style>
  /* Hero Section */
  .hero-section {
    position: relative;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
    padding: 4rem 2rem;
    border-radius: 16px;
    margin-bottom: 3rem;
    color: white;
    overflow: hidden;
    box-shadow: 0 20px 60px rgba(102, 126, 234, 0.3);
  }
  
  .hero-pattern {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-image: 
      radial-gradient(circle at 20% 50%, rgba(255,255,255,0.1) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(255,255,255,0.1) 0%, transparent 50%),
      radial-gradient(circle at 40% 20%, rgba(255,255,255,0.05) 0%, transparent 30%);
    pointer-events: none;
  }
  
  .hero-content {
    position: relative;
    z-index: 1;
    max-width: 800px;
    margin: 0 auto;
    text-align: center;
  }
  
  .hero-badge {
    display: inline-block;
    background: rgba(255, 255, 255, 0.2);
    backdrop-filter: blur(10px);
    padding: 0.4rem 1rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    margin-bottom: 1.5rem;
    border: 1px solid rgba(255, 255, 255, 0.3);
  }
  
  .hero-title {
    font-size: 3.5rem;
    margin-bottom: 0.5rem;
    font-weight: 800;
    background: linear-gradient(to right, #ffffff, #e0e7ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  }
  
  .hero-subtitle {
    font-size: 1.5rem;
    margin-bottom: 1rem;
    opacity: 0.95;
    font-weight: 500;
  }
  
  .hero-description {
    font-size: 1.1rem;
    margin-bottom: 2rem;
    opacity: 0.85;
    line-height: 1.6;
    max-width: 600px;
    margin-left: auto;
    margin-right: auto;
  }
  
  .hero-buttons {
    display: flex;
    gap: 1rem;
    justify-content: center;
    flex-wrap: wrap;
  }
  
  .btn {
    display: inline-flex;
    align-items: center;
    padding: 0.8rem 2rem;
    border-radius: 8px;
    font-weight: 600;
    text-decoration: none;
    transition: all 0.3s ease;
    font-size: 1rem;
  }
  
  .btn-primary {
    background: white;
    color: #667eea;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  }
  
  .btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
  }
  
  .btn-secondary {
    background: rgba(255, 255, 255, 0.1);
    color: white;
    border: 2px solid rgba(255, 255, 255, 0.3);
    backdrop-filter: blur(10px);
  }
  
  .btn-secondary:hover {
    background: rgba(255, 255, 255, 0.2);
    transform: translateY(-2px);
  }
  
  /* Feature Cards */
  .feature-card {
    border-radius: 12px;
    padding: 1.5rem;
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0;
    transition: all 0.3s ease;
    height: 100%;
  }
  
  .feature-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.1);
    border-color: #667eea;
  }
  
  .feature-icon {
    font-size: 2.5rem;
    margin-bottom: 1rem;
    display: block;
  }
  
  .feature-card h3 {
    color: #1e293b;
    font-size: 1.25rem;
    margin-bottom: 0.75rem;
    font-weight: 700;
  }
  
  .feature-card ul {
    margin: 0;
    padding-left: 1.2rem;
    color: #64748b;
  }
  
  .feature-card li {
    margin-bottom: 0.4rem;
    line-height: 1.5;
  }
  
  /* Sub Features Grid */
  .sub-features-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
  }
  
  .sub-feature-card {
    background: white;
    border-radius: 8px;
    padding: 1rem;
    border: 1px solid #e2e8f0;
    transition: all 0.3s ease;
  }
  
  .sub-feature-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
    border-color: #667eea;
  }
  
  .sub-feature-card h4 {
    color: #1e293b;
    font-size: 1rem;
    margin-bottom: 0.75rem;
    font-weight: 600;
  }
  
  .sub-feature-card ul {
    margin: 0;
    padding-left: 1.2rem;
    color: #64748b;
  }
  
  .sub-feature-card li {
    margin-bottom: 0.4rem;
    line-height: 1.5;
    font-size: 0.9rem;
  }
  
  /* Module Cards */
  .module-card {
    border-radius: 12px;
    padding: 2rem;
    background: white;
    border: 2px solid #e2e8f0;
    transition: all 0.3s ease;
    text-align: center;
    position: relative;
    overflow: hidden;
  }
  
  .module-link {
    text-decoration: none;
    color: inherit;
    display: block;
    height: 100%;
  }
  
  .module-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #667eea, #764ba2);
    transform: scaleX(0);
    transition: transform 0.3s ease;
  }
  
  .module-card:hover::before {
    transform: scaleX(1);
  }
  
  .module-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 15px 50px rgba(102, 126, 234, 0.15);
    border-color: #667eea;
  }
  
  .module-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
    display: block;
  }
  
  .module-card h3 {
    color: #1e293b;
    font-size: 1.3rem;
    margin-bottom: 0.75rem;
    font-weight: 700;
  }
  
  .module-card p {
    color: #64748b;
    margin: 0;
    line-height: 1.6;
  }
  
  /* Info Section */
  .info-section {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    padding: 2rem;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
  }
  
  .info-item {
    display: flex;
    align-items: center;
    margin-bottom: 1rem;
    padding: 0.75rem;
    background: white;
    border-radius: 8px;
    border-left: 4px solid #667eea;
  }
  
  .info-item:last-child {
    margin-bottom: 0;
  }
  
  .info-label {
    font-weight: 700;
    color: #1e293b;
    margin-right: 0.75rem;
    min-width: 120px;
  }
  
  .info-value {
    color: #64748b;
    font-weight: 500;
  }
  
  /* Quick Start Section */
  .quick-start-section {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    padding: 2.5rem;
    border-radius: 12px;
    color: white;
    margin: 2rem 0;
  }
  
  .quick-start-section h3 {
    color: white;
    margin-top: 0;
    margin-bottom: 1.5rem;
    font-size: 1.5rem;
  }
  
  .quick-start-section pre {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 1rem;
    overflow-x: auto;
  }
  
  .quick-start-section code {
    color: #a5b4fc;
    font-family: 'Consolas', 'Monaco', monospace;
  }
  
  /* Features Grid */
  .features-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.5rem;
    margin: 2rem 0;
  }
  
  .feature-item {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    padding: 1rem;
    background: #f8fafc;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
  }
  
  .feature-check {
    color: #10b981;
    font-size: 1.2rem;
    flex-shrink: 0;
  }
  
  .feature-text {
    color: #334155;
    font-weight: 500;
  }
  
  /* Changelog */
  .changelog-item {
    padding: 1.5rem;
    background: #f8fafc;
    border-radius: 8px;
    margin-bottom: 1rem;
    border-left: 4px solid #667eea;
  }
  
  .changelog-version {
    font-weight: 700;
    color: #1e293b;
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
  }
  
  .changelog-list {
    margin: 0;
    padding-left: 1.2rem;
    color: #64748b;
  }
  
  .changelog-list li {
    margin-bottom: 0.3rem;
  }
</style>

该算法开发工具库是一个根据本人自身算法工程师日常工作而构建的综合性工具集合。

本库整合了算法开发过程中常用的核心功能模块：计算机视觉处理技术、文件操作工具和基础实用函数。通过模块化的设计，为算法研发提供高效、可靠的技术支持，显著提升开发效率，减少重复性工作，确保代码质量和可维护性。

## 📋 项目概览

<div class="features-grid">
  <div class="feature-card">
    <h3>🎯 核心功能</h3>
    <div class="sub-features-grid">
      <div class="sub-feature-card">
        <h4>计算机视觉</h4>
        <ul>
          <li>图像处理与变换</li>
          <li>标注工具与格式转换</li>
          <li>目标检测与可视化</li>
        </ul>
      </div>
      <div class="sub-feature-card">
        <h4>文件处理</h4>
        <ul>
          <li>批量文件操作</li>
          <li>格式转换与管理</li>
          <li>数据预处理管道</li>
        </ul>
      </div>
      <div class="sub-feature-card">
        <h4>基础工具</h4>
        <ul>
          <li>日志管理与配置</li>
          <li>网络传输协议</li>
          <li>数据库客户端</li>
        </ul>
      </div>
    </div>
  </div>

  <div class="feature-card">
    <h3>🚀 技术特点</h3>
    <div class="sub-features-grid">
      <div class="sub-feature-card">
        <h4>架构设计</h4>
        <ul>
          <li>模块化代码结构</li>
          <li>易于扩展和维护</li>
          <li>清晰的API设计</li>
        </ul>
      </div>
      <div class="sub-feature-card">
        <h4>性能优化</h4>
        <ul>
          <li>多线程并发支持</li>
          <li>批量处理能力</li>
          <li>内存效率优化</li>
        </ul>
      </div>
      <div class="sub-feature-card">
        <h4>质量保证</h4>
        <ul>
          <li>完善的异常处理</li>
          <li>详细的文档说明</li>
          <li>跨平台兼容性</li>
        </ul>
      </div>
    </div>
  </div>

  <div class="feature-card">
    <h3>💡 应用场景</h3>
    <div class="sub-features-grid">
      <div class="sub-feature-card">
        <h4>目标检测</h4>
        <ul>
          <li>数据集准备与标注</li>
          <li>格式转换与验证</li>
          <li>结果可视化分析</li>
        </ul>
      </div>
      <div class="sub-feature-card">
        <h4>图像分割</h4>
        <ul>
          <li>多边形处理</li>
          <li>掩码操作</li>
          <li>数据增强</li>
        </ul>
      </div>
      <div class="sub-feature-card">
        <h4>工业应用</h4>
        <ul>
          <li>缺陷检测流程</li>
          <li>图像裁剪分类</li>
          <li>统计分析报告</li>
        </ul>
      </div>
    </div>
  </div>
</div>

## 📁 项目架构

:::{dropdown} {octicon}`repo;1em`&nbsp; 目录结构
:animate: fade-in-slide-down
:open:

```
coreXAlgo/
├── 📄 __init__.py              # 主入口文件
├── 📄 version.py               # 版本管理
│
├── 📁 utils/                   # 基础工具模块
│   ├── 📄 basic.py            # 基础工具函数
│   ├── 📄 bbox_util.py        # 边界框处理工具
│   ├── 📄 constants.py        # 常量定义
│   ├── 📄 ftp_client.py       # FTP客户端
│   ├── 📄 sftp_client.py      # SFTP客户端
│   ├── 📄 mt_db_client.py     # 多线程数据库客户端
│   └── 📄 mt_file_transfer.py # 多线程文件传输器
│
├── 📁 adv_cv/                 # 高级计算机视觉模块
│   └── 📄 basic.py           # 图像处理功能
│
└── 📁 file_processing/         # 文件处理模块
    ├── 📄 basic.py           # 文件操作工具
    ├── 📄 archive.py         # 压缩解压管理
    ├── 📄 annotation_convert.py # 标注格式转换
    ├── 📄 data_preprocessing.py # 数据预处理
    ├── 📄 image_crop.py      # 图像裁剪处理
    └── 📄 voc_xml_deal.py   # VOC XML处理
```
:::

## 📊 版本信息

:::{dropdown} {octicon}`info;1em`&nbsp; 版本详情
:animate: fade-in-slide-down
:open:

<div class="info-section">
  <div class="info-item">
    <span class="info-label">📦 当前版本</span>
    <span class="info-value">0.5.2</span>
  </div>
  <div class="info-item">
    <span class="info-label">🐍 Python 兼容</span>
    <span class="info-value">≥ 3.8</span>
  </div>
  <div class="info-item">
    <span class="info-label">📅 更新日期</span>
    <span class="info-value">2026-03-19</span>
  </div>
  <div class="info-item">
    <span class="info-label">👤 作者</span>
    <span class="info-value">Xxin_BOE</span>
  </div>
  <div class="info-item">
    <span class="info-label">🎯 主要领域</span>
    <span class="info-value">计算机视觉、数据处理</span>
  </div>
</div>
:::

## 📚 模块文档

<div class="features-grid">
  <div class="module-card">
    <a href="adv_cv/index.html" class="module-link">
      <span class="module-icon">🖼️</span>
      <h3>计算机视觉</h3>
      <p>Adv_cv Module</p>
      <p>常用的计算机视觉技术和处理方法，以及对 OpenCV 函数的改进版本</p>
    </a>
  </div>

  <div class="module-card">
    <a href="file_processing/index.html" class="module-link">
      <span class="module-icon">📂</span>
      <h3>文件处理</h3>
      <p>File_processing Module</p>
      <p>常用的文件处理功能函数，特别是针对标注数据和图像处理的自定义工具</p>
    </a>
  </div>

  <div class="module-card">
    <a href="utils/index.html" class="module-link">
      <span class="module-icon">🛠️</span>
      <h3>基础工具</h3>
      <p>Utils Module</p>
      <p>常用的基础工具函数和类，包括网络传输、数据库操作、日志管理等</p>
    </a>
  </div>
</div>

## 🔧 快速开始 {#quick-start}

<div class="quick-start-section">

### 安装

```bash
# 克隆仓库
git clone https://github.com/Xxin980219/coreXAlgo.git

# 进入目录
cd coreXAlgo

# 安装依赖
pip install -r requirements.txt

# 安装库
pip install -e .
```

### 基本使用示例

```python
from coreXAlgo.utils import set_all_seed, colorstr
from coreXAlgo.file_processing import get_files, clean_unmatched_files

# 设置随机种子确保可复现
set_all_seed(42)

# 输出彩色日志
print(colorstr('green', 'bold', '✅ 核心功能初始化完成'))

# 查找文件
image_files = get_files('./images', ['.jpg', '.png'])
print(f"📸 找到 {len(image_files)} 个图片文件")

# 清理不匹配的文件
clean_unmatched_files(
    folder_path='./dataset',
    label_ext='.txt',
    dry_run=True
)
```

</div>

## 🎯 主要特性

<div class="features-grid">
  <div class="feature-item">
    <span class="feature-check">✅</span>
    <span class="feature-text">完善的文档与详细的使用示例</span>
  </div>
  <div class="feature-item">
    <span class="feature-check">✅</span>
    <span class="feature-text">全面的类型注解提高代码可读性</span>
  </div>
  <div class="feature-item">
    <span class="feature-check">✅</span>
    <span class="feature-text">完善的异常处理机制</span>
  </div>
  <div class="feature-item">
    <span class="feature-check">✅</span>
    <span class="feature-text">多线程支持批量处理性能优化</span>
  </div>
  <div class="feature-item">
    <span class="feature-check">✅</span>
    <span class="feature-text">跨平台兼容 Windows/Linux/macOS</span>
  </div>
  <div class="feature-item">
    <span class="feature-check">✅</span>
    <span class="feature-text">模块化设计易于扩展维护</span>
  </div>
  <div class="feature-item">
    <span class="feature-check">✅</span>
    <span class="feature-text">生产级代码质量测试覆盖完善</span>
  </div>
  <div class="feature-item">
    <span class="feature-check">✅</span>
    <span class="feature-text">活跃的社区支持与持续更新</span>
  </div>
</div>

## 📝 版本更新日志

<div class="changelog-item">
  <div class="changelog-version">📌 版本 0.5.2 (2026-03-19)</div>
  <ul class="changelog-list">
    <li>优化了 utils/ftp_client.py 和 utils/sftp_client.py，添加了多线程支持</li>
    <li>实现了线程安全的连接池管理</li>
    <li>添加了 _process_upload_batch 和 _process_single_upload 方法用于并行上传</li>
    <li>添加了 _process_download_batch 和 _process_single_download 方法用于并行下载</li>
    <li>修复了 max_workers 参数未使用的问题</li>
    <li>修复了 utils/mt_file_transfer.py 中的返回值处理问题</li>
    <li>确保 parallel_download_by_instances 正确返回成功下载数量</li>
    <li>统一了FTP和SFTP客户端的返回值处理格式</li>
    <li>增强了线程安全机制，添加了 threading.RLock() 线程安全锁</li>
    <li>优化了文件传输性能，支持批量处理文件传输</li>
  </ul>
</div>

<div class="changelog-item">
  <div class="changelog-version">📌 版本 0.5.1 (2026-03-03)</div>
  <ul class="changelog-list">
    <li>更新了 file_processing/image_crop.py，添加了新参数：separate_images_xml 和 generate_ok_xml</li>
    <li>改进了 image_crop.py 的目录结构管理</li>
    <li>增强了 image_crop.py 的错误处理和日志记录</li>
    <li>更新了 image_crop.py 的 _process_image 方法以返回正确的错误值</li>
    <li>为 image_crop.py 添加了 tqdm 安全检查以处理 stdout None 的情况</li>
    <li>重新排列了 image_crop.py 中 __init__ 方法的参数，将 verbose 移到最后</li>
    <li>隐藏了 annotation_convert.py 中的某些异常类和类型定义，使其不在文档中显示</li>
  </ul>
</div>

<div class="changelog-item">
  <div class="changelog-version">📌 版本 0.5.0 (2026-02-27)</div>
  <ul class="changelog-list">
    <li>为 file_processing/basic.py 中的函数添加了详细的文档字符串和使用示例</li>
    <li>优化了 randomly_select_files 函数的代码结构</li>
  </ul>
</div>

<div class="changelog-item">
  <div class="changelog-version">📌 版本 0.4.9 (2026-02-26)</div>
  <ul class="changelog-list">
    <li>修复了 sftp_client.py 中下载成功数量统计错误的问题</li>
    <li>优化了 sftp_client.py 的异常处理逻辑</li>
    <li>为 mt_file_downloader.py 添加了缺失的 logging 模块导入</li>
    <li>改进了 sftp_client.py 的连接池管理</li>
  </ul>
</div>

<div class="changelog-item">
  <div class="changelog-version">📌 版本 0.4.8 (2026-02-25)</div>
  <ul class="changelog-list">
    <li>重构了文件处理模块，提升了性能</li>
    <li>优化了工具模块，包括 bbox_util.py、ftp_client.py 和 sftp_client.py</li>
    <li>新增了 mt_file_downloader.py 模块</li>
    <li>改进了数据库客户端的查询性能和错误处理</li>
  </ul>
</div>

<div class="changelog-item">
  <div class="changelog-version">📌 版本 0.4.7 (2026-02-24)</div>
  <ul class="changelog-list">
    <li>修复了 SQLAlchemy 版本兼容性问题</li>
    <li>优化了 FTP/SFTP 客户端的错误处理</li>
    <li>改进了目标检测可视化的性能</li>
  </ul>
</div>

<div class="changelog-item">
  <div class="changelog-version">📌 版本 0.4.6 (2026-02-23)</div>
  <ul class="changelog-list">
    <li>初始版本发布</li>
    <li>包含核心工具模块、高级计算机视觉模块和文件处理模块</li>
  </ul>
</div>

```{toctree}
:caption: 模块文档
:hidden:

adv_cv/index
file_processing/index
utils/index
```
