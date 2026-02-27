# Utils Module

<div class="module-header">
  <div class="module-content">
    <h1>Utils Module</h1>
    <p class="module-description">基础工具模块</p>
    <p class="module-detail">包含算法开发中常用的基础工具函数和类，旨在提高开发效率，减少重复代码编写</p>
  </div>
</div>

<style>
  .module-header {
    background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    padding: 1.5rem;
    border-radius: 8px;
    margin-bottom: 1.5rem;
    color: white;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }
  
  .module-content {
    max-width: 800px;
    margin: 0 auto;
  }
  
  .module-content h1 {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    font-weight: bold;
  }
  
  .module-description {
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
    opacity: 0.9;
  }
  
  .module-detail {
    font-size: 0.9rem;
    opacity: 0.8;
  }
  
  .component-card {
    border-radius: 8px;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    border: 1px solid #e9ecef;
  }
  
  .component-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
  }
  
  .component-icon {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
  }
</style>

## 📋 模块概览

**Utils** 模块提供了一系列基础工具函数和类，为算法开发提供通用的技术支持。该模块包含了从文件操作、网络传输到数据库访问等多种功能，旨在简化开发流程，提高代码复用率。

## 🚀 核心功能

- **基础工具**：日志管理、随机种子设置、颜色输出
- **边界框处理**：边界框转换、合并、可视化
- **网络传输**：FTP/SFTP 客户端、多线程下载
- **数据库操作**：多数据库查询客户端
- **文件处理**：JSON/YAML/ pickle 读写
- **并发处理**：线程池、并行任务

## 📁 组件列表

::::{grid} 2 2 2 3
:gutter: 2
:padding: 1

:::{grid-item-card} {octicon}`codescan` Basic
:link: basic
:link-type: doc
:class-card: component-card

**基础函数**

提供日志管理、随机种子设置、颜色输出、文件读写等基础工具函数。
:::

:::{grid-item-card} {octicon}`diamond` Bbox_util
:link: bbox_util
:link-type: doc
:class-card: component-card

**边界框处理**

提供边界框转换、合并、多边形处理和目标检测可视化功能。
:::

:::{grid-item-card} {octicon}`cloud` Ftp_client
:link: ftp_client
:link-type: doc
:class-card: component-card

**FTP客户端**

提供 FTP 协议的文件上传和下载功能，支持断点续传和进度显示。
:::

:::{grid-item-card} {octicon}`cache` Mt_db_client
:link: mt_db_client
:link-type: doc
:class-card: component-card

**多数据库客户端**

轻量级多数据库查询客户端，支持 MySQL、PostgreSQL、SQLite 等多种数据库。
:::

:::{grid-item-card} {octicon}`download` Mt_file_downloader
:link: mt_file_downloader
:link-type: doc
:class-card: component-card

**多线程文件下载器**

多线程并行下载 FTP/SFTP 文件夹的所有文件，支持断点续传和进度显示。
:::

:::{grid-item-card} {octicon}`cloud` Sftp_client
:link: sftp_client
:link-type: doc
:class-card: component-card

**SFTP客户端**

提供 SFTP 协议的文件上传和下载功能，优化了连接稳定性和传输效率。
:::

::::

## 🔧 使用示例

```python
from coreXAlgo.utils import set_all_seed, colorstr, thread_pool

# 设置随机种子
set_all_seed(42)

# 输出彩色日志
print(colorstr('green', 'bold', '核心功能初始化完成'))

# 多线程处理
def process_file(file_path):
    # 处理文件
    pass

file_list = ['file1.txt', 'file2.txt', 'file3.txt']
failed = thread_pool(process_file, file_list, workers=4)
```

## 🎯 应用场景

- **开发辅助**：日志管理、颜色输出、随机种子设置
- **数据处理**：边界框处理、多边形转换、可视化
- **网络传输**：文件上传下载、批量传输、断点续传
- **数据库操作**：多数据库查询、数据导出、表结构操作
- **并发处理**：多线程任务、批量处理、性能优化

## 📚 相关资源

- [Python 官方文档](https://docs.python.org/3/)
- [FTP 协议详解](https://tools.ietf.org/html/rfc959)
- [SFTP 协议详解](https://tools.ietf.org/html/draft-ietf-secsh-filexfer-02)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)

```{toctree}
:caption: utils
:hidden:

basic
bbox_util
ftp_client
mt_db_client
mt_file_downloader
sftp_client
```
