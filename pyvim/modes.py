"""Editor modes implementation."""

from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .editor import Editor


class Mode(Enum):
    """Editor modes."""
    NORMAL = auto()
    INSERT = auto()
    VISUAL = auto()
    COMMAND = auto()
    REPLACE = auto()


class ModeHandler:
    """Handles mode transitions and mode-specific behavior."""
    
    def __init__(self, editor: 'Editor'):
        self.editor = editor
        self.current_mode = Mode.NORMAL
        self.previous_mode = Mode.NORMAL
        
    def set_mode(self, mode: Mode):
        """Change editor mode."""
        self.previous_mode = self.current_mode
        self.current_mode = mode
        self.editor.display.update_status_bar()
        
    def get_mode(self) -> Mode:
        """Get current mode."""
        return self.current_mode
        
    def is_insert_mode(self) -> bool:
        """Check if in insert mode."""
        return self.current_mode == Mode.INSERT
        
    def is_normal_mode(self) -> bool:
        """Check if in normal mode."""
        return self.current_mode == Mode.NORMAL
        
    def is_command_mode(self) -> bool:
        """Check if in command mode."""
        return self.current_mode == Mode.COMMAND
        
    def is_visual_mode(self) -> bool:
        """Check if in visual mode."""
        return self.current_mode == Mode.VISUAL