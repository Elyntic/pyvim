"""Configuration settings for PyVim."""

import os
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Config:
    """Editor configuration."""
    
    # Display settings
    show_line_numbers: bool = True
    tab_size: int = 4
    use_spaces: bool = True
    
    # Colors (curses color pairs)
    color_scheme: str = "default"
    
    # Editor behavior
    auto_indent: bool = True
    highlight_current_line: bool = True
    show_status_bar: bool = True
    show_mode_indicator: bool = True
    
    # File settings
    backup_files: bool = True
    auto_save: bool = False
    auto_save_interval: int = 300  # seconds
    
    # Key repeat settings
    key_repeat_initial_delay: float = 0.5
    key_repeat_interval: float = 0.03


# Default configuration instance
default_config = Config()


def load_config(config_path: str = None) -> Config:
    """Load configuration from file."""
    if config_path is None:
        config_path = os.path.expanduser("~/.pyvimrc")
    
    config = Config()
    
    if os.path.exists(config_path):
        # TODO: Implement config file parsing
        pass
    
    return config