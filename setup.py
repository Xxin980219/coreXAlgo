import re

from setuptools import setup, find_packages
import os


# 自动读取版本号
def get_version():
    # 尝试从 version.py 读取版本号
    version_path = os.path.join("coreXAlgo", "version.py")
    with open(version_path, "r", encoding="utf-8") as f:
        version_match = re.search(r"^__version__\s*=\s*['\"]([^'\"]*)['\"]", f.read(), re.M)
        if version_match:
            return version_match.group(1)

    # 如果找不到，使用默认版本
    return "0.1.0"

get_version()

def read_requirements():
    """读取requirements.txt"""
    with open('requirements.txt') as f:
        return [line.strip() for line in f if line.strip()]


setup(
    name="coreXAlgo",
    version=get_version(),
    packages=find_packages(),  # 自动发现所有包
    include_package_data=True,  # 包含非代码文件

    # 重要：包含模型权重和其他资源文件
    package_data={},

    install_requires=[],
    # # YOLO的依赖项（根据requirements.txt调整）
    # install_requires=read_requirements(),

    # 元数据
    author="Xiong Xin",
    author_email="",
    description="coreXAlgo - CoreX Algorithm Library.",
    license="AGPL-3.0",
    python_requires=">=3.7",  # Python版本要求
)