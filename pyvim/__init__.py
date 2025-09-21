"""
PyVim - A lightweight Vim-like text editor in Python
Version: 0.0.2a
"""

__version__ = "0.0.2a"
__author__ = "Your Name"

from .editor import Editor
from .buffer import Buffer
from .modes import Mode
from .window import Window

__all__ = ["Editor", "Buffer", "Mode", "Window", "__version__"]