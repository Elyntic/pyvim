"""Utility functions for PyVim."""

import os
import re
from typing import List, Tuple, Optional


def expand_tabs(text: str, tab_size: int = 4) -> str:
    """Expand tabs to spaces."""
    return text.replace('\t', ' ' * tab_size)


def get_word_at_cursor(line: str, cursor_x: int) -> Tuple[str, int, int]:
    """Get word at cursor position."""
    if cursor_x >= len(line):
        return "", cursor_x, cursor_x
        
    # Find word boundaries
    word_pattern = re.compile(r'\w+')
    
    for match in word_pattern.finditer(line):
        start, end = match.span()
        if start <= cursor_x < end:
            return match.group(), start, end
            
    return "", cursor_x, cursor_x


def find_matching_bracket(lines: List[str], cursor_y: int, cursor_x: int) -> Optional[Tuple[int, int]]:
    """Find matching bracket for bracket at cursor position."""
    if cursor_y >= len(lines) or cursor_x >= len(lines[cursor_y]):
        return None
        
    char = lines[cursor_y][cursor_x]
    
    brackets = {
        '(': (')', 1),
        ')': ('(', -1),
        '[': (']', 1),
        ']': ('[', -1),
        '{': ('}', 1),
        '}': ('{', -1),
    }
    
    if char not in brackets:
        return None
        
    match_char, direction = brackets[char]
    count = 1
    y, x = cursor_y, cursor_x
    
    while True:
        x += direction
        
        # Move to next/previous line if needed
        if direction > 0 and x >= len(lines[y]):
            y += 1
            if y >= len(lines):
                break
            x = 0
        elif direction < 0 and x < 0:
            y -= 1
            if y < 0:
                break
            x = len(lines[y]) - 1
            
        current_char = lines[y][x] if x < len(lines[y]) else ''
        
        if current_char == char:
            count += 1
        elif current_char == match_char:
            count -= 1
            if count == 0:
                return (y, x)
                
    return None


def create_backup(filename: str) -> bool:
    """Create backup of file."""
    if not os.path.exists(filename):
        return False
        
    backup_name = filename + "~"
    
    try:
        with open(filename, 'rb') as src:
            with open(backup_name, 'wb') as dst:
                dst.write(src.read())
        return True
    except Exception:
        return False


def get_file_info(filename: str) -> dict:
    """Get file information."""
    info = {
        'exists': os.path.exists(filename),
        'size': 0,
        'lines': 0,
        'readable': False,
        'writable': False,
    }
    
    if info['exists']:
        info['size'] = os.path.getsize(filename)
        info['readable'] = os.access(filename, os.R_OK)
        info['writable'] = os.access(filename, os.W_OK)
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                info['lines'] = sum(1 for _ in f)
        except:
            pass
            
    return info