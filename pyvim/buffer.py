"""Enhanced buffer management for the editor."""

import os
import re
from typing import List, Optional, Tuple
from .undo import UndoManager


class Buffer:
    """Represents a text buffer with undo support."""
    
    def __init__(self, filename: Optional[str] = None):
        self.filename = filename
        self.display_name = filename
        self.lines: List[str] = [""]
        self.modified = False
        self.cursor_x = 0
        self.cursor_y = 0
        self.offset_y = 0  # Vertical scroll offset
        self.offset_x = 0  # Horizontal scroll offset
        self.undo_manager = UndoManager(self)
        self.marks = {}  # Mark positions
        self.jump_list = []  # Jump history
        self.jump_index = -1
        self.last_search = None
        self.file_encoding = 'utf-8'
        self.line_ending = '\n'  # \n for Unix, \r\n for Windows
        
        if filename and os.path.exists(filename):
            self.load_file()
            
    def load_file(self):
        """Load file content into buffer with encoding detection."""
        if not self.filename:
            return
            
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(self.filename, 'r', encoding=encoding) as f:
                    content = f.read()
                    
                # Detect line ending
                if '\r\n' in content:
                    self.line_ending = '\r\n'
                elif '\r' in content:
                    self.line_ending = '\r'
                else:
                    self.line_ending = '\n'
                    
                self.lines = content.split(self.line_ending) if content else [""]
                self.file_encoding = encoding
                self.modified = False
                self.undo_manager.load_persistent_undo(self.filename)
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                self.lines = [f"Error loading file: {e}"]
                break
                
    def save_file(self, filename: Optional[str] = None):
        """Save buffer content to file."""
        if filename:
            self.filename = filename
            self.display_name = filename
            
        if not self.filename:
            raise ValueError("No filename specified")
            
        # Create backup
        if os.path.exists(self.filename):
            backup_name = self.filename + "~"
            try:
                with open(self.filename, 'rb') as src:
                    with open(backup_name, 'wb') as dst:
                        dst.write(src.read())
            except:
                pass
                
        try:
            content = self.line_ending.join(self.lines)
            with open(self.filename, 'w', encoding=self.file_encoding) as f:
                f.write(content)
            self.modified = False
            self.undo_manager.mark_save_point()
            self.undo_manager.save_persistent_undo(self.filename)
            return True
        except Exception as e:
            raise Exception(f"Error saving file: {e}")
            
    def insert_char(self, char: str):
        """Insert character at cursor position."""
        self.undo_manager.save_state("Insert character")
        line = self.lines[self.cursor_y]
        self.lines[self.cursor_y] = (
            line[:self.cursor_x] + char + line[self.cursor_x:]
        )
        self.cursor_x += 1
        self.modified = True
        
    def delete_char(self):
        """Delete character before cursor (backspace behavior)."""
        self.undo_manager.save_state("Delete character")
        if self.cursor_x > 0:
            line = self.lines[self.cursor_y]
            self.lines[self.cursor_y] = (
                line[:self.cursor_x - 1] + line[self.cursor_x:]
            )
            self.cursor_x -= 1
            self.modified = True
        elif self.cursor_y > 0:
            # Join with previous line
            self.cursor_x = len(self.lines[self.cursor_y - 1])
            self.lines[self.cursor_y - 1] += self.lines[self.cursor_y]
            del self.lines[self.cursor_y]
            self.cursor_y -= 1
            self.modified = True
            
    def delete_char_at_cursor(self):
        """Delete character at cursor position."""
        self.undo_manager.save_state("Delete at cursor")
        line = self.lines[self.cursor_y]
        
        if self.cursor_x < len(line):
            self.lines[self.cursor_y] = (
                line[:self.cursor_x] + line[self.cursor_x + 1:]
            )
            self.modified = True
        elif self.cursor_y < len(self.lines) - 1:
            # Join with next line
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
        self.undo_manager.save_state("Insert line")
        if below:
            self.lines.insert(self.cursor_y + 1, "")
            self.cursor_y += 1
        else:
            self.lines.insert(self.cursor_y, "")
        self.cursor_x = 0
        self.modified = True
        
    def delete_line(self):
        """Delete current line."""
        self.undo_manager.save_state("Delete line")
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
            
    def move_cursor(self, dx: int = 0, dy: int = 0):
        """Move cursor by specified offset."""
        # Vertical movement
        new_y = self.cursor_y + dy
        self.cursor_y = max(0, min(new_y, len(self.lines) - 1))
        
        # Horizontal movement
        line_length = len(self.lines[self.cursor_y])
        new_x = self.cursor_x + dx
        self.cursor_x = max(0, min(new_x, line_length))
        
    def move_cursor_to(self, x: int, y: int):
        """Move cursor to absolute position."""
        self.cursor_y = max(0, min(y, len(self.lines) - 1))
        line_length = len(self.lines[self.cursor_y])
        self.cursor_x = max(0, min(x, line_length))
        
    def get_line(self, line_num: int) -> str:
        """Get line at specified line number."""
        if 0 <= line_num < len(self.lines):
            return self.lines[line_num]
        return ""
        
    def get_current_line(self) -> str:
        """Get current line."""
        return self.get_line(self.cursor_y)
        
    def goto_line(self, line_num: int):
        """Go to specified line number (1-indexed)."""
        self.add_jump_position()
        self.cursor_y = max(0, min(line_num - 1, len(self.lines) - 1))
        self.cursor_x = 0
        
    def set_mark(self, mark: str):
        """Set a mark at current position."""
        self.marks[mark] = (self.cursor_y, self.cursor_x)
        
    def goto_mark(self, mark: str) -> bool:
        """Go to a previously set mark."""
        if mark in self.marks:
            self.add_jump_position()
            self.cursor_y, self.cursor_x = self.marks[mark]
            self.validate_cursor()
            return True
        return False
        
    def add_jump_position(self):
        """Add current position to jump list."""
        pos = (self.cursor_y, self.cursor_x)
        
        # Remove any forward jumps
        if self.jump_index < len(self.jump_list) - 1:
            self.jump_list = self.jump_list[:self.jump_index + 1]
            
        # Add new position if it's different from the last one
        if not self.jump_list or self.jump_list[-1] != pos:
            self.jump_list.append(pos)
            if len(self.jump_list) > 100:  # Limit jump list size
                self.jump_list.pop(0)
            self.jump_index = len(self.jump_list) - 1
            
    def jump_backward(self) -> bool:
        """Jump to previous position in jump list."""
        if self.jump_index > 0:
            self.jump_index -= 1
            self.cursor_y, self.cursor_x = self.jump_list[self.jump_index]
            self.validate_cursor()
            return True
        return False
        
    def jump_forward(self) -> bool:
        """Jump to next position in jump list."""
        if self.jump_index < len(self.jump_list) - 1:
            self.jump_index += 1
            self.cursor_y, self.cursor_x = self.jump_list[self.jump_index]
            self.validate_cursor()
            return True
        return False
        
    def validate_cursor(self):
        """Ensure cursor is within valid bounds."""
        # Ensure we have at least one line
        if not self.lines:
            self.lines = [""]
            
        # Validate vertical position
        self.cursor_y = max(0, min(self.cursor_y, len(self.lines) - 1))
        
        # Validate horizontal position
        line_length = len(self.lines[self.cursor_y])
        self.cursor_x = max(0, min(self.cursor_x, line_length))
        
    def get_word_at_cursor(self) -> str:
        """Get the word under the cursor."""
        line = self.lines[self.cursor_y]
        if self.cursor_x >= len(line):
            return ""
            
        # Find word boundaries
        start = self.cursor_x
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == '_'):
            start -= 1
            
        end = self.cursor_x
        while end < len(line) and (line[end].isalnum() or line[end] == '_'):
            end += 1
            
        return line[start:end]
        
    def find_word_start(self, x: int, y: int) -> int:
        """Find the start of a word at given position."""
        if y >= len(self.lines):
            return x
            
        line = self.lines[y]
        while x > 0 and (line[x - 1].isalnum() or line[x - 1] == '_'):
            x -= 1
        return x
        
    def find_word_end(self, x: int, y: int) -> int:
        """Find the end of a word at given position."""
        if y >= len(self.lines):
            return x
            
        line = self.lines[y]
        while x < len(line) and (line[x].isalnum() or line[x] == '_'):
            x += 1
        return x
        
    def get_visible_lines(self, start: int, count: int) -> List[str]:
        """Get visible lines for display."""
        end = min(start + count, len(self.lines))
        return self.lines[start:end]
        
    def get_line_count(self) -> int:
        """Get total number of lines."""
        return len(self.lines)
        
    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self.lines) == 1 and self.lines[0] == ""
        
    def get_content(self) -> str:
        """Get entire buffer content as string."""
        return self.line_ending.join(self.lines)
        
    def set_content(self, content: str):
        """Set buffer content from string."""
        self.undo_manager.save_state("Set content")
        
        # Detect line ending
        if '\r\n' in content:
            self.line_ending = '\r\n'
        elif '\r' in content:
            self.line_ending = '\r'
        else:
            self.line_ending = '\n'
            
        self.lines = content.split(self.line_ending) if content else [""]
        self.cursor_x = 0
        self.cursor_y = 0
        self.modified = True
        self.validate_cursor()
        
    def replace_line(self, line_num: int, new_line: str):
        """Replace a specific line."""
        if 0 <= line_num < len(self.lines):
            self.undo_manager.save_state("Replace line")
            self.lines[line_num] = new_line
            self.modified = True
            
    def insert_text_at_cursor(self, text: str):
        """Insert text at current cursor position."""
        self.undo_manager.save_state("Insert text")
        
        lines = text.split('\n')
        current_line = self.get_current_line()
        
        if len(lines) == 1:
            # Single line insert
            self.lines[self.cursor_y] = (
                current_line[:self.cursor_x] + text + current_line[self.cursor_x:]
            )
            self.cursor_x += len(text)
        else:
            # Multi-line insert
            before = current_line[:self.cursor_x]
            after = current_line[self.cursor_x:]
            
            # First line
            self.lines[self.cursor_y] = before + lines[0]
            
            # Middle lines
            for i, line in enumerate(lines[1:-1], 1):
                self.lines.insert(self.cursor_y + i, line)
                
            # Last line
            last_line_index = self.cursor_y + len(lines) - 1
            self.lines.insert(last_line_index, lines[-1] + after)
            
            self.cursor_y = last_line_index
            self.cursor_x = len(lines[-1])
            
        self.modified = True
        
    def delete_range(self, start_y: int, start_x: int, end_y: int, end_x: int):
        """Delete text in a range."""
        self.undo_manager.save_state("Delete range")
        
        if start_y == end_y:
            # Single line deletion
            line = self.lines[start_y]
            self.lines[start_y] = line[:start_x] + line[end_x:]
        else:
            # Multi-line deletion
            first_line = self.lines[start_y][:start_x]
            last_line = self.lines[end_y][end_x:]
            
            # Combine first and last line
            self.lines[start_y] = first_line + last_line
            
            # Delete intermediate lines
            for _ in range(end_y - start_y):
                del self.lines[start_y + 1]
                
        self.cursor_y = start_y
        self.cursor_x = start_x
        self.modified = True
        self.validate_cursor()
        
    def get_text_range(self, start_y: int, start_x: int, end_y: int, end_x: int) -> str:
        """Get text in a range."""
        if start_y == end_y:
            # Single line
            return self.lines[start_y][start_x:end_x]
        else:
            # Multi-line
            result = []
            result.append(self.lines[start_y][start_x:])
            
            for y in range(start_y + 1, end_y):
                result.append(self.lines[y])
                
            result.append(self.lines[end_y][:end_x])
            
            return '\n'.join(result)