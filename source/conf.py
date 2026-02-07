#!/usr/bin/env python
"""
Sphinx configuration file for coreXAlgo project.

This file configures the Sphinx documentation builder for the coreXAlgo project.
It sets up project information, extensions, build options, and output settings.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Define paths
project_root = Path(__file__).parent.parent

# Insert paths to sys.path
sys.path.insert(0, str(project_root.resolve()))

# -- Project information -----------------------------------------------------
project = 'coreXAlgo'
copyright = '2026, Xiong xin'
author = 'Xiong xin'

# Version information
try:
    from coreXAlgo import __version__
    version = __version__
    release = __version__
except ImportError:
    version = 'latest'
    release = 'latest'

# -- General configuration ---------------------------------------------

# Mock imports to avoid dependency issues during documentation build
autodoc_mock_imports = [
    "pymysql", 
    "torch", 
    "cv2", 
    "numpy", 
    "tqdm", 
    "pandas", 
    "paramiko", 
    "matplotlib",
    "sqlalchemy",
    "concurrent.futures",
    "ftplib",
    "lxml",
]
# Sphinx extensions
extensions = [
    # Core extensions
    "sphinx.ext.autodoc",          # Automatic documentation generation
    "sphinx.ext.mathjax",          # Math equation support
    "sphinx.ext.napoleon",         # Google-style docstring support
    "sphinx.ext.intersphinx",      # Cross-referencing other documentation
    "sphinx.ext.autosectionlabel",  # Automatic section labels for cross-referencing
    "sphinx.ext.viewcode",          # Add links to source code
    "sphinx.ext.todo",              # Todo item support
    
    # Third-party extensions
    "sphinx_design",                # Modern UI components
    "myst_parser",                  # Markdown support
    "nbsphinx",                     # Jupyter notebook support
    "sphinx_autodoc_typehints",     # Type hint support
    "sphinx_copybutton",            # Copy code button
]

# MyST (Markedly Structured Text) configuration
myst_enable_extensions = [
    "colon_fence",    # Support for ::: fences
    "linkify",        # Automatic link detection
    "substitution",   # Variable substitution
    "tasklist",       # Task list support
    "deflist",        # Definition list support
    "fieldlist",      # Field list support
    "amsmath",        # AMS math support
    "dollarmath",     # Dollar-delimited math
]

# Enable eval-rst in MyST
myst_enable_eval_rst = True

# Jupyter notebook handling
nbsphinx_allow_errors = True
nbsphinx_execute = "auto"  # Execute notebooks during build
nbsphinx_timeout = 300  # Timeout in seconds
nbsphinx_kernel_name = "python3"  # Kernel to use for execution

# Templates and patterns
templates_path = ["_templates"]
exclude_patterns: List[str] = [
    "_build",
    "**.ipynb_checkpoints",
    "**/.pytest_cache",
    "**/.git",
    "**/.github",
    "**/.venv",
    "**/*.egg-info",
    "**/build",
    "**/dist",
    "examples/notebooks/**",
    "**/__pycache__",
]

# Automatic exclusion of prompts from code copies
# https://sphinx-copybutton.readthedocs.io/en/latest/use.html#automatic-exclusion-of-prompts-from-the-copies
copybutton_exclude = ".linenos, .gp, .go"
copybutton_prompt_text = ">>> "  # Default Python prompt
copybutton_prompt_is_regexp = True  # Treat prompt as regex

# Enable section anchors for cross-referencing
autosectionlabel_prefix_document = True

# Todo extension configuration
todo_include_todos = True  # Include todos in documentation

# Autodoc configuration
autodoc_default_options = {
    "members": True,            # Include all members
    "undoc-members": True,      # Include undocumented members
    "private-members": False,    # Exclude private members
    "special-members": True,     # Include special members
    "inherited-members": True,   # Include inherited members
    "show-inheritance": True,    # Show inheritance hierarchy
    "ignore-module-all": False,  # Don't ignore __all__
}

# Type hints configuration
autodoc_typehints = "description"  # Include type hints in descriptions
autodoc_typehints_format = "short"  # Use short type names

# -- Options for HTML output ------------------------------------------

html_theme = "sphinx_book_theme"
html_logo = "_static/images/logos/coreXAlgo-icon.png"
html_favicon = "_static/images/logos/coreXAlgo-favicon.png"
html_static_path = ["_static"]

# HTML theme options
html_theme_options: Dict[str, Any] = {
    "logo": {
        "text": "coreXAlgo",
    },
    "repository_url": "https://github.com/Xxin980219/coreXAlgo",  # Repository URL
    "repository_branch": "main",  # Default branch
    "use_repository_button": True,  # Show repository button
    "use_issues_button": True,      # Show issues button
    "use_download_button": True,    # Show download button
    "path_to_docs": "source",       # Path to documentation source
    "use_edit_page_button": True,    # Show edit page button
    "show_navbar_depth": 2,          # Show navbar depth
    "navbar_align": "left",          # Navbar alignment
    "navbar_center": [],             # Center navbar items
    "navbar_end": ["navbar-icon-links"],  # End navbar items
    "footer_start": [],              # Start footer items
    "footer_end": ["copyright"],     # End footer items
    "show_prev_next": True,          # Show previous/next buttons
    "show_toc_level": 2,             # Show TOC level
    "home_page_in_toc": True,        # Include home page in TOC
    "extra_navbar": "",              # Extra navbar content
    "extra_footer": "",              # Extra footer content
}

# HTML context
templates_context = {
    "github_user": "yourusername",
    "github_repo": "coreXAlgo",
    "github_version": "main",
    "doc_path": "source",
}

# External documentation references
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "torch": ("https://pytorch.org/docs/stable", None),
    "lightning": ("https://lightning.ai/docs/pytorch/stable/", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "pandas": ("https://pandas.pydata.org/docs/stable", None),
    "matplotlib": ("https://matplotlib.org/stable", None),
}

# Intersphinx cache timeout (in days)
intersphinx_timeout = 10

# -- Options for LaTeX output ------------------------------------------
latex_elements = {
    "papersize": "a4paper",
    "pointsize": "10pt",
    "preamble": "",
}

# LaTeX document class
latex_documents = [
    ("index", "coreXAlgo.tex", "coreXAlgo Documentation",
     "Xiong xin", "manual"),
]

# -- Options for manual page output ------------------------------------------
man_pages = [
    ("index", "corexalgo", "coreXAlgo Documentation",
     ["Xiong xin"], 1)
]

# -- Options for Texinfo output ------------------------------------------
texinfo_documents = [
    ("index", "coreXAlgo", "coreXAlgo Documentation",
     "Xiong xin", "coreXAlgo", "One line description of project.",
     "Miscellaneous"),
]

# -- Options for Epub output ------------------------------------------
epub_title = "coreXAlgo"
epub_author = "Xiong xin"
epub_publisher = "Xiong xin"
epub_copyright = "2026, Xiong xin"
epub_exclude_files = ["search.html"]

# -- Performance optimizations ------------------------------------------

# Cache settings
# Increase cache size for faster builds
# This is especially useful for large documentation projects
builders_cache_limit = 5  # Number of builder caches to keep

# Parallel processing
try:
    import multiprocessing
    # Use half of available CPUs for parallel builds
    parallel = min(multiprocessing.cpu_count() // 2, 4)
    if parallel > 1:
        print(f"Using {parallel} parallel processes for documentation build")
except ImportError:
    parallel = 1

# -- Security settings ------------------------------------------

# Prevent execution of arbitrary code in notebooks
# This is a security measure to avoid malicious code execution
nbsphinx_allow_errors = True  # Still allow errors but be cautious

# -- Final checks ------------------------------------------

# Verify required directories exist
required_dirs = [
    Path(__file__).parent / "_templates",
    Path(__file__).parent / "_static" / "images" / "logos",
]

for dir_path in required_dirs:
    if not dir_path.exists():
        print(f"Warning: Directory {dir_path} does not exist. Creating it...")
        dir_path.mkdir(parents=True, exist_ok=True)
