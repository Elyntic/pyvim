"""Buffer management for the editor."""

import os
from typing import List, Optional


class Buffer:
    """Represents a text buffer."""
    
    def __init__(self, filename: Optional[str] = None):
        self.filename = filename
        self.lines: List[str] = [""]
        self.modified = False
        self.cursor_x = 0
        self.cursor_y = 0
        self.offset_y = 0  # Vertical scroll offset
        self.offset_x = 0  # Horizontal scroll offset
        
        if filename and os.path.exists(filename):
            self.load_file()
            
    def load_file(self):
        """Load file content into buffer."""
        if not self.filename:
            return
            
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                content = f.read()
                self.lines = content.split('\n') if content else [""]
            self.modified = False
        except Exception as e:
            self.lines = [f"Error loading file: {e}"]
            
    def save_file(self, filename: Optional[str] = None):
        """Save buffer content to file."""
        if filename:
            self.filename = filename
            
        if not self.filename:
            raise ValueError("No filename specified")
            
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.lines))
            self.modified = False
            return True
        except Exception as e:
            raise Exception(f"Error saving file: {e}")
            
    def insert_char(self, char: str):
        """Insert character at cursor position."""
        line = self.lines[self.cursor_y]
        self.lines[self.cursor_y] = (
            line[:self.cursor_x] + char + line[self.cursor_x:]
        )
        self.cursor_x += 1
        self.modified = True
        
    def delete_char(self):
        """Delete character before cursor (backspace behavior)."""
        if self.cursor_x > 0:
            # Delete character before cursor in current line
            line = self.lines[self.cursor_y]
            self.lines[self.cursor_y] = (
                line[:self.cursor_x - 1] + line[self.cursor_x:]
            )
            self.cursor_x -= 1
            self.modified = True
        elif self.cursor_y > 0:
            # At beginning of line, join with previous line
            self.cursor_x = len(self.lines[self.cursor_y - 1])
            self.lines[self.cursor_y - 1] += self.lines[self.cursor_y]
            del self.lines[self.cursor_y]
            self.cursor_y -= 1
            self.modified = True
            
    def delete_char_at_cursor(self):
        """Delete character at cursor position (delete key behavior)."""
        line = self.lines[self.cursor_y]
        
        if self.cursor_x < len(line):
            # Delete character at cursor
            self.lines[self.cursor_y] = (
                line[:self.cursor_x] + line[self.cursor_x + 1:]
            )
            self.modified = True
        elif self.cursor_y < len(self.lines) - 1:
            # At end of line, join with next line
            self.lines[self.cursor_y] += self.lines[self.cursor_y + 1]
            del self.lines[self.cursor_y + 1]
            self.modified = True
            
    def backspace(self):
        """Handle backspace key - delete character before cursor."""
        self.delete_char()
        
    def delete_forward(self):
        """Handle delete key - delete character at cursor."""
        self.delete_char_at_cursor()
        
    def insert_line(self, below: bool = True):
        """Insert new line above or below current line."""
        if below:
            self.lines.insert(self.cursor_y + 1, "")
            self.cursor_y += 1
        else:
            self.lines.insert(self.cursor_y, "")
        self.cursor_x = 0
        self.modified = True
        
    def delete_line(self):
        """Delete current line."""
        if len(self.lines) > 1:
            del self.lines[self.cursor_y]
            if self.cursor_y >= len(self.lines):
                self.cursor_y = len(self.lines) - 1
            self.cursor_x = 0
            self.modified = True
        else:
            self.lines[0] = ""
            self.cursor_x = 0
            self.modified = True
            
    def get_line(self, line_num: int) -> str:
        """Get line at specified line number."""
        if 0 <= line_num < len(self.lines):
            return self.lines[line_num]
        return ""
        
    def get_current_line(self) -> str:
        """Get current line."""
        return self.get_line(self.cursor_y)
        
    def move_cursor(self, dx: int = 0, dy: int = 0):
        """Move cursor by specified offset."""
        # Vertical movement
        self.cursor_y = max(0, min(self.cursor_y + dy, len(self.lines) - 1))
        
        # Horizontal movement
        line_length = len(self.lines[self.cursor_y])
        self.cursor_x = max(0, min(self.cursor_x + dx, line_length))
        
    def goto_line(self, line_num: int):
        """Go to specified line number."""
        self.cursor_y = max(0, min(line_num - 1, len(self.lines) - 1))
        self.cursor_x = 0