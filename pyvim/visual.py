"""Visual mode implementation."""

from enum import Enum, auto
from typing import Tuple, Optional, List
from dataclasses import dataclass


class VisualMode(Enum):
    """Types of visual selection."""
    CHARACTER = auto()
    LINE = auto()
    BLOCK = auto()


@dataclass
class Selection:
    """Represents a visual selection."""
    start_y: int
    start_x: int
    end_y: int
    end_x: int
    mode: VisualMode
    
    def normalize(self) -> 'Selection':
        """Normalize selection coordinates."""
        if self.start_y > self.end_y or (self.start_y == self.end_y and self.start_x > self.end_x):
            return Selection(
                self.end_y, self.end_x,
                self.start_y, self.start_x,
                self.mode
            )
        return self
        
    def contains(self, y: int, x: int) -> bool:
        """Check if position is within selection."""
        norm = self.normalize()
        
        if self.mode == VisualMode.LINE:
            return norm.start_y <= y <= norm.end_y
            
        elif self.mode == VisualMode.CHARACTER:
            if y < norm.start_y or y > norm.end_y:
                return False
            if y == norm.start_y and x < norm.start_x:
                return False
            if y == norm.end_y and x > norm.end_x:
                return False
            return True
            
        elif self.mode == VisualMode.BLOCK:
            if y < norm.start_y or y > norm.end_y:
                return False
            min_x = min(norm.start_x, norm.end_x)
            max_x = max(norm.start_x, norm.end_x)
            return min_x <= x <= max_x
            
        return False


class VisualModeHandler:
    """Handles visual mode operations."""
    
    def __init__(self, buffer):
        self.buffer = buffer
        self.selection: Optional[Selection] = None
        self.mode: Optional[VisualMode] = None
        
    def start_selection(self, mode: VisualMode):
        """Start visual selection."""
        self.mode = mode
        self.selection = Selection(
            self.buffer.cursor_y,
            self.buffer.cursor_x,
            self.buffer.cursor_y,
            self.buffer.cursor_x,
            mode
        )
        
    def update_selection(self):
        """Update selection end point to cursor position."""
        if self.selection:
            self.selection.end_y = self.buffer.cursor_y
            self.selection.end_x = self.buffer.cursor_x
            
    def clear_selection(self):
        """Clear visual selection."""
        self.selection = None
        self.mode = None
        
    def get_selected_text(self) -> str:
        """Get selected text."""
        if not self.selection:
            return ""
            
        norm = self.selection.normalize()
        lines = []
        
        if self.selection.mode == VisualMode.LINE:
            for y in range(norm.start_y, norm.end_y + 1):
                if y < len(self.buffer.lines):
                    lines.append(self.buffer.lines[y])
                    
        elif self.selection.mode == VisualMode.CHARACTER:
            if norm.start_y == norm.end_y:
                # Single line selection
                line = self.buffer.lines[norm.start_y]
                lines.append(line[norm.start_x:norm.end_x + 1])
            else:
                # Multi-line selection
                # First line
                lines.append(self.buffer.lines[norm.start_y][norm.start_x:])
                # Middle lines
                for y in range(norm.start_y + 1, norm.end_y):
                    lines.append(self.buffer.lines[y])
                # Last line
                lines.append(self.buffer.lines[norm.end_y][:norm.end_x + 1])
                
        elif self.selection.mode == VisualMode.BLOCK:
            min_x = min(norm.start_x, norm.end_x)
            max_x = max(norm.start_x, norm.end_x)
            
            for y in range(norm.start_y, norm.end_y + 1):
                if y < len(self.buffer.lines):
                    line = self.buffer.lines[y]
                    if min_x < len(line):
                        lines.append(line[min_x:min(max_x + 1, len(line))])
                    else:
                        lines.append("")
                        
        return '\n'.join(lines)
        
    def delete_selection(self):
        """Delete selected text."""
        if not self.selection:
            return
            
        norm = self.selection.normalize()
        
        if self.selection.mode == VisualMode.LINE:
            # Delete entire lines
            del self.buffer.lines[norm.start_y:norm.end_y + 1]
            if not self.buffer.lines:
                self.buffer.lines = [""]
            self.buffer.cursor_y = min(norm.start_y, len(self.buffer.lines) - 1)
            self.buffer.cursor_x = 0
            
        elif self.selection.mode == VisualMode.CHARACTER:
            if norm.start_y == norm.end_y:
                # Single line deletion
                line = self.buffer.lines[norm.start_y]
                self.buffer.lines[norm.start_y] = (
                    line[:norm.start_x] + line[norm.end_x + 1:]
                )
            else:
                # Multi-line deletion
                first_line = self.buffer.lines[norm.start_y][:norm.start_x]
                last_line = self.buffer.lines[norm.end_y][norm.end_x + 1:]
                self.buffer.lines[norm.start_y] = first_line + last_line
                del self.buffer.lines[norm.start_y + 1:norm.end_y + 1]
                
            self.buffer.cursor_y = norm.start_y
            self.buffer.cursor_x = norm.start_x
            
        elif self.selection.mode == VisualMode.BLOCK:
            min_x = min(norm.start_x, norm.end_x)
            max_x = max(norm.start_x, norm.end_x)
            
            for y in range(norm.start_y, norm.end_y + 1):
                if y < len(self.buffer.lines):
                    line = self.buffer.lines[y]
                    if min_x < len(line):
                        self.buffer.lines[y] = (
                            line[:min_x] + line[min(max_x + 1, len(line)):]
                        )
                        
            self.buffer.cursor_y = norm.start_y
            self.buffer.cursor_x = min_x
            
        self.buffer.modified = True
        self.clear_selection()
        
    def indent_selection(self, indent: bool = True):
        """Indent or unindent selected lines."""
        if not self.selection:
            return
            
        norm = self.selection.normalize()
        indent_str = "    "  # 4 spaces
        
        if self.selection.mode in [VisualMode.LINE, VisualMode.CHARACTER]:
            for y in range(norm.start_y, norm.end_y + 1):
                if y < len(self.buffer.lines):
                    if indent:
                        self.buffer.lines[y] = indent_str + self.buffer.lines[y]
                    else:
                        # Unindent
                        line = self.buffer.lines[y]
                        if line.startswith(indent_str):
                            self.buffer.lines[y] = line[len(indent_str):]
                        elif line.startswith("\t"):
                            self.buffer.lines[y] = line[1:]
                            
        self.buffer.modified = True