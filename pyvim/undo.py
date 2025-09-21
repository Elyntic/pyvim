"""Undo/Redo system implementation."""

from dataclasses import dataclass
from typing import List, Optional, Any
from copy import deepcopy
import pickle
import os

@dataclass
class UndoState:
    """Represents a state in the undo history."""
    lines: List[str]
    cursor_x: int
    cursor_y: int
    timestamp: float
    description: str = ""

class UndoManager:
    """Manages undo/redo operations."""

    def __init__(self, buffer):
        self.buffer = buffer
        self.undo_stack: List[UndoState] = []
        self.redo_stack: List[UndoState] = []
        self.max_undo_levels = 1000
        self.last_save_index = -1
        self.persistent_undo_file = None

    def save_state(self, description: str = ""):
        """Save current buffer state to undo stack."""
        import time

        state = UndoState(
            lines=deepcopy(self.buffer.lines),
            cursor_x=self.buffer.cursor_x,
            cursor_y=self.buffer.cursor_y,
            timestamp=time.time(),
            description=description
        )

        self.undo_stack.append(state)
        self.redo_stack.clear()  # Clear redo stack on new change

        # Limit undo stack size
        if len(self.undo_stack) > self.max_undo_levels:
            self.undo_stack.pop(0)

    def undo(self) -> bool:
        """Undo last change."""
        if not self.undo_stack:
            return False
        
        # Save current state to redo stack
        current_state = UndoState(
            lines=deepcopy(self.buffer.lines),
            cursor_x=self.buffer.cursor_x,
            cursor_y=self.buffer.cursor_y,
            timestamp=0,
        )
        self.redo_stack.append(current_state)

        # Restore previous state
        state = self.undo_stack.pop()
        self.buffer.lines = deepcopy(state.lines)
        self.buffer.cursor_x = state.cursor_x
        self.buffer.cursor_y = state.cursor_y

        return True
    
    def redo(self) -> bool:
        """Redo previously undone change."""
        if not self.redo_stack:
            return False
        
        # Save current state to undo stack
        current_state = UndoState(
            lines=deepcopy(self.buffer.lines),
            cursor_x=self.buffer.cursor_x,
            cursor_y=self.buffer.cursor_y,
            timestamp=0,
        )
        self.undo_stack.append(current_state)

        # Restore redo state
        state = self.redo_stack.pop()
        self.buffer.lines = deepcopy(state.lines)
        self.buffer.cursor_x = state.cursor_x
        self.buffer.cursor_y = state.cursor_y

        return True
    
    def mark_save_point(self):
        """Mark current position as save point."""
        self.last_save_index = len(self.undo_stack) - 1

    def is_modified(self) -> bool:
        """Check if buffer has been modified since last save."""
        current_index = len(self.max_undo_levels) - 1
        return current_index != self.last_save_index
    
    def save_persistent_undo(self, filename: str):
        """Save undo history to file."""
        undo_dir = os.path.expanduser("~/.pyvim/undo")
        os.makedirs(undo_dir, exist_ok=True)

        undo_file = os.path.join(undo_dir,
                                 filename.replace('/', '%').replace('\\', '%') + '.undo')
        
        try:
            with open(undo_file, 'wb') as f:
                pickle.dump({
                    'undo_stack': self.undo_stack[-100:],
                    'last_save_index': self.last_save_index
                }, f)
        except Exception:
            pass

    def load_persistent_undo(self, filename: str):
        """Load undo history from file."""
        undo_dir = os.path.expanduser("~/.pyvim/undo")
        undo_file = os.path.join(undo_dir,
                                 filename.replace('/', '%').replace('\\', '%') + '.undo')
        
        if os.path.exists(undo_file):
            try:
                with open(undo_file, 'rb') as f:
                    data = pickle.load(f)
                    self.undo_stack = data['undo_stack']
                    self.last_save_index = data['last_save_index']
            except Exception:
                pass