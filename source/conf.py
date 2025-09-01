#!/usr/bin/env python
import os
import sys

sys.path.insert(0, os.path.abspath(".."))
# print("当前工作目录:", os.getcwd())
# print("src绝对路径:", os.path.abspath('../coreXAIgo'))
# print("路径是否存在:", os.path.exists(os.path.abspath('../coreXAIgo')))


# fmt: off
__version__ = '0.1.0'
# fmt: on

# -- Project information -----------------------------------------------------

project = 'coreXAIgo'
copyright = '2025, Xiong xin'
author = 'Xiong xin'

version = __version__
release = __version__

# -- General configuration ---------------------------------------------
autodoc_mock_imports = ["pymysql"]  # 模拟导入，避免报错

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    # 支持 Google/NumPy 风格的文档字符串
    "sphinx.ext.napoleon",
    # myst 解析器
    "myst_parser",
    # 代码块复制按钮扩展
    "sphinx_copybutton",
    # tab 面板插件
    'sphinx_tabs.tabs',
    # 折叠警告（注释、警告等）的功能按钮
    "sphinx_togglebutton",
]

# 自动为所有模块生成文档
autosummary_generate = True

templates_path = ["_templates"]

source_suffix = ['.rst', '.md']

source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = "index"

language = 'zh_CN'

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

todo_include_todos = False

# -- Options for HTML output -------------------------------------------

# html_theme = "alabaster"
html_theme = "sphinx_rtd_theme"
# html_theme = "sphinx_typo3_theme"

tml_logo = "_static/logo.png"

html_static_path = ['_static']
# html_style = "custom.css"

html_theme_options = {}

# Output file base name for HTML help builder.
htmlhelp_basename = "coreXAIgo"
# 可选：修改 html_title 来控制浏览器标签页标题
html_title = 'coreXAIgo Documentation'

# -- Options for LaTeX output ------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',
    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',
    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',
    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto, manual, or own class]).
latex_documents = [
    (
        master_doc,
        "corexAIgo.tex",
        "corexAIgo Documentation",
        author,
        "manual",
    ),
]

# -- Options for manual page output ------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, "corexAIgo", "corexAIgo Documentation", [author], 1)]

# -- Options for Texinfo output ----------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        "corexAIgo",
        "corexAIgo Documentation",
        author,
        "corexAIgo",
        "One line description of project.",
        "Miscellaneous",
    ),
]


def setup(app):
    app.add_css_file('custom.css')
