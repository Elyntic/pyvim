"""Buffer management for multiple files."""

from typing import List, Optional, Dict
from .buffer import Buffer


class BufferManager:
    """Manages multiple buffers."""
    
    def __init__(self):
        self.buffers: List[Buffer] = []
        self.current_index = -1
        self.buffer_history: List[int] = []
        self.unnamed_counter = 0
        
    def create_buffer(self, filename: Optional[str] = None) -> Buffer:
        """Create a new buffer."""
        buffer = Buffer(filename)
        
        if not filename:
            self.unnamed_counter += 1
            buffer.display_name = f"[No Name {self.unnamed_counter}]"
        else:
            buffer.display_name = filename
            
        self.buffers.append(buffer)
        self.current_index = len(self.buffers) - 1
        self.buffer_history.append(self.current_index)
        
        return buffer
        
    def open_file(self, filename: str) -> Buffer:
        """Open a file in a new buffer or switch to existing."""
        # Check if file is already open
        for i, buffer in enumerate(self.buffers):
            if buffer.filename == filename:
                self.switch_to_buffer(i)
                return buffer
                
        # Create new buffer for file
        return self.create_buffer(filename)
        
    def get_current_buffer(self) -> Optional[Buffer]:
        """Get the current buffer."""
        if 0 <= self.current_index < len(self.buffers):
            return self.buffers[self.current_index]
        return None
        
    def switch_to_buffer(self, index: int):
        """Switch to buffer by index."""
        if 0 <= index < len(self.buffers):
            self.current_index = index
            self.buffer_history.append(index)
            
            # Limit history size
            if len(self.buffer_history) > 100:
                self.buffer_history.pop(0)
                
    def next_buffer(self):
        """Switch to next buffer."""
        if self.buffers:
            self.current_index = (self.current_index + 1) % len(self.buffers)
            self.buffer_history.append(self.current_index)
            
    def previous_buffer(self):
        """Switch to previous buffer."""
        if self.buffers:
            self.current_index = (self.current_index - 1) % len(self.buffers)
            self.buffer_history.append(self.current_index)
            
    def close_buffer(self, index: Optional[int] = None) -> bool:
        """Close a buffer."""
        if index is None:
            index = self.current_index
            
        if not (0 <= index < len(self.buffers)):
            return False
            
        buffer = self.buffers[index]
        
        # Check if buffer is modified
        if buffer.modified:
            # Would need confirmation dialog here
            pass
            
        # Remove buffer
        del self.buffers[index]
        
        # Adjust current index
        if self.buffers:
            if self.current_index >= len(self.buffers):
                self.current_index = len(self.buffers) - 1
        else:
            self.current_index = -1
            
        return True
        
    def get_buffer_list(self) -> List[str]:
        """Get list of buffer names."""
        names = []
        for i, buffer in enumerate(self.buffers):
            modified = '+' if buffer.modified else ' '
            current = '>' if i == self.current_index else ' '
            name = buffer.display_name or buffer.filename or "[No Name]"
            names.append(f"{current} {i+1} {name} {modified}")
        return names
        
    def alternate_buffer(self):
        """Switch to alternate (previous) buffer."""
        if len(self.buffer_history) >= 2:
            # Get previous buffer from history
            prev_index = self.buffer_history[-2]
            if 0 <= prev_index < len(self.buffers):
                self.switch_to_buffer(prev_index)