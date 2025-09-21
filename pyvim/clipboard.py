"""Clipboard management with system integration."""

import os
import sys
from typing import List, Optional, Tuple

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


class Register:
    """Represents a vim register."""
    
    def __init__(self, name: str):
        self.name = name
        self.content: List[str] = []
        self.is_line_mode = False
        
    def set(self, content: List[str], line_mode: bool = False):
        """Set register content."""
        self.content = content.copy()
        self.is_line_mode = line_mode
        
    def get(self) -> List[str]:
        """Get register content."""
        return self.content.copy()
        
    def clear(self):
        """Clear register content."""
        self.content = []
        self.is_line_mode = False


class ClipboardManager:
    """Manages clipboard and registers."""
    
    def __init__(self):
        self.registers = {
            '"': Register('"'),  # Default register
            '0': Register('0'),  # Yank register
            '1': Register('1'),  # Delete registers
            '2': Register('2'),
            '3': Register('3'),
            '4': Register('4'),
            '5': Register('5'),
            '6': Register('6'),
            '7': Register('7'),
            '8': Register('8'),
            '9': Register('9'),
            '-': Register('-'),  # Small delete register
            'a': Register('a'),  # Named registers a-z
            'b': Register('b'),
            'c': Register('c'),
            # ... add more as needed
            '+': Register('+'),  # System clipboard
            '*': Register('*'),  # Primary selection (X11)
            '/': Register('/'),  # Last search pattern
            ':': Register(':'),  # Last command
            '.': Register('.'),  # Last inserted text
            '%': Register('%'),  # Current filename
            '#': Register('#'),  # Alternate filename
        }
        
        self.recording_register = None
        self.recording_commands = []
        
    def yank(self, lines: List[str], register: str = '"', line_mode: bool = False):
        """Yank (copy) lines to register."""
        if register not in self.registers:
            register = '"'
            
        self.registers[register].set(lines, line_mode)
        
        # Also set to yank register
        if register != '0':
            self.registers['0'].set(lines, line_mode)
            
        # Copy to system clipboard if using + register
        if register == '+' and HAS_PYPERCLIP:
            try:
                pyperclip.copy('\n'.join(lines))
            except:
                pass
                
    def delete(self, lines: List[str], register: str = '"', line_mode: bool = False):
        """Delete lines and save to register."""
        if register not in self.registers:
            register = '"'
            
        # Rotate numbered registers
        for i in range(9, 1, -1):
            if str(i-1) in self.registers and str(i) in self.registers:
                self.registers[str(i)].content = self.registers[str(i-1)].content
                self.registers[str(i)].is_line_mode = self.registers[str(i-1)].is_line_mode
                
        # Set register 1
        self.registers['1'].set(lines, line_mode)
        
        # Set specified register
        self.registers[register].set(lines, line_mode)
        
    def put(self, register: str = '"') -> Optional[Tuple[List[str], bool]]:
        """Get content from register for pasting."""
        if register == '+' and HAS_PYPERCLIP:
            # Get from system clipboard
            try:
                content = pyperclip.paste()
                if content:
                    lines = content.split('\n')
                    return (lines, '\n' in content)
            except:
                pass
                
        if register in self.registers:
            reg = self.registers[register]
            if reg.content:
                return (reg.get(), reg.is_line_mode)
                
        return None
        
    def start_recording(self, register: str):
        """Start recording macro to register."""
        if register in self.registers:
            self.recording_register = register
            self.recording_commands = []
            
    def stop_recording(self):
        """Stop recording macro."""
        if self.recording_register:
            self.registers[self.recording_register].set(
                self.recording_commands,
                line_mode=False
            )
            self.recording_register = None
            self.recording_commands = []
            
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self.recording_register is not None
        
    def record_command(self, command: str):
        """Record a command during macro recording."""
        if self.is_recording():
            self.recording_commands.append(command)
            
    def play_macro(self, register: str) -> List[str]:
        """Play back a recorded macro."""
        if register in self.registers:
            return self.registers[register].get()
        return []