"""Window management for split views."""

from enum import Enum, auto
from typing import List, Optional, Tuple
from dataclasses import dataclass


class SplitType(Enum):
    """Window split types."""
    HORIZONTAL = auto()
    VERTICAL = auto()


@dataclass
class WindowLayout:
    """Represents a window's layout."""
    x: int
    y: int
    width: int
    height: int
    

class Window:
    """Represents a window in the editor."""
    
    def __init__(self, buffer, layout: WindowLayout):
        self.buffer = buffer
        self.layout = layout
        self.cursor_x = 0
        self.cursor_y = 0
        self.offset_x = 0
        self.offset_y = 0
        
    def resize(self, width: int, height: int):
        """Resize the window."""
        self.layout.width = width
        self.layout.height = height
        
    def is_cursor_visible(self) -> bool:
        """Check if cursor is within visible area."""
        if self.cursor_y < self.offset_y or self.cursor_y >= self.offset_y + self.layout.height:
            return False
        if self.cursor_x < self.offset_x or self.cursor_x >= self.offset_x + self.layout.width:
            return False
        return True
        
    def adjust_viewport(self):
        """Adjust viewport to keep cursor visible."""
        # Vertical adjustment
        if self.cursor_y < self.offset_y:
            self.offset_y = self.cursor_y
        elif self.cursor_y >= self.offset_y + self.layout.height - 1:
            self.offset_y = self.cursor_y - self.layout.height + 2
            
        # Horizontal adjustment
        if self.cursor_x < self.offset_x:
            self.offset_x = self.cursor_x
        elif self.cursor_x >= self.offset_x + self.layout.width - 1:
            self.offset_x = self.cursor_x - self.layout.width + 2


class WindowManager:
    """Manages multiple windows and splits."""
    
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.windows: List[Window] = []
        self.active_window_index = 0
        
    def add_window(self, window: Window):
        """Add a new window."""
        self.windows.append(window)
        
    def get_active_window(self) -> Optional[Window]:
        """Get the currently active window."""
        if 0 <= self.active_window_index < len(self.windows):
            return self.windows[self.active_window_index]
        return None
        
    def split_window(self, split_type: SplitType) -> Window:
        """Split the current window."""
        if not self.windows:
            return None
            
        current = self.get_active_window()
        if not current:
            return None
            
        if split_type == SplitType.HORIZONTAL:
            # Split horizontally (top/bottom)
            new_height = current.layout.height // 2
            current.layout.height = new_height
            
            new_window = Window(
                current.buffer,
                WindowLayout(
                    x=current.layout.x,
                    y=current.layout.y + new_height,
                    width=current.layout.width,
                    height=self.screen_height - current.layout.y - new_height
                )
            )
        else:
            # Split vertically (left/right)
            new_width = current.layout.width // 2
            current.layout.width = new_width
            
            new_window = Window(
                current.buffer,
                WindowLayout(
                    x=current.layout.x + new_width,
                    y=current.layout.y,
                    width=self.screen_width - current.layout.x - new_width,
                    height=current.layout.height
                )
            )
            
        self.windows.insert(self.active_window_index + 1, new_window)
        return new_window
        
    def close_window(self) -> bool:
        """Close the current window."""
        if len(self.windows) <= 1:
            return False
            
        del self.windows[self.active_window_index]
        if self.active_window_index >= len(self.windows):
            self.active_window_index = len(self.windows) - 1
            
        # Redistribute space
        self._redistribute_space()
        return True
        
    def next_window(self):
        """Switch to next window."""
        if self.windows:
            self.active_window_index = (self.active_window_index + 1) % len(self.windows)
            
    def previous_window(self):
        """Switch to previous window."""
        if self.windows:
            self.active_window_index = (self.active_window_index - 1) % len(self.windows)
            
    def _redistribute_space(self):
        """Redistribute space among windows after closing."""
        if not self.windows:
            return
            
        # Simple equal distribution for now
        height_per_window = self.screen_height // len(self.windows)
        y_offset = 0
        
        for window in self.windows:
            window.layout.x = 0
            window.layout.y = y_offset
            window.layout.width = self.screen_width
            window.layout.height = height_per_window
            y_offset += height_per_window
            
        # Give remaining space to last window
        if self.windows:
            self.windows[-1].layout.height += self.screen_height % len(self.windows)