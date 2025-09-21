"""Search and replace functionality."""

import re
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class SearchMatch:
    """Represents a search match."""
    line: int
    start: int
    end: int
    text: str


class SearchEngine:
    """Handles search and replace operations."""
    
    def __init__(self, buffer):
        self.buffer = buffer
        self.last_search: Optional[str] = None
        self.last_direction: str = "forward"
        self.search_history: List[str] = []
        self.replace_history: List[Tuple[str, str]] = []
        self.matches: List[SearchMatch] = []
        self.current_match_index: int = -1
        self.case_sensitive: bool = False
        self.use_regex: bool = False
        self.whole_word: bool = False
        
    def search(self, pattern: str, direction: str = "forward", 
               from_cursor: bool = True) -> Optional[Tuple[int, int]]:
        """Search for pattern in buffer."""
        if not pattern:
            pattern = self.last_search
            
        if not pattern:
            return None
            
        self.last_search = pattern
        self.last_direction = direction
        
        # Add to search history
        if pattern not in self.search_history:
            self.search_history.append(pattern)
            if len(self.search_history) > 50:
                self.search_history.pop(0)
                
        # Build regex pattern
        if self.use_regex:
            try:
                regex = re.compile(pattern, 
                                   re.IGNORECASE if not self.case_sensitive else 0)
            except re.error:
                return None
        else:
            escaped = re.escape(pattern)
            if self.whole_word:
                escaped = r'\b' + escaped + r'\b'
            regex = re.compile(escaped,
                               re.IGNORECASE if not self.case_sensitive else 0)
            
        # Find all matches
        self.matches.clear()
        for line_num, line in enumerate(self.buffer.lines):
            for match in regex.finditer(line):
                self.matches.append(SearchMatch(
                    line=line_num,
                    start=match.start(),
                    end=match.end(),
                    text=match.group()
                ))
                
        if not self.matches:
            return None
            
        # Find closest match to cursor
        if from_cursor:
            cursor_y, cursor_x = self.buffer.cursor_y, self.buffer.cursor_x
            
            if direction == "forward":
                for i, match in enumerate(self.matches):
                    if (match.line > cursor_y or 
                        (match.line == cursor_y and match.start > cursor_x)):
                        self.current_match_index = i
                        break
                else:
                    # Wrap around
                    self.current_match_index = 0
            else:  # backward
                for i in range(len(self.matches) - 1, -1, -1):
                    match = self.matches[i]
                    if (match.line < cursor_y or
                        (match.line == cursor_y and match.start < cursor_x)):
                        self.current_match_index = i
                        break
                else:
                    # Wrap around
                    self.current_match_index = len(self.matches) - 1
        else:
            self.current_match_index = 0 if direction == "forward" else len(self.matches) - 1
            
        if self.current_match_index >= 0:
            match = self.matches[self.current_match_index]
            return (match.line, match.start)
            
        return None
        
    def find_next(self) -> Optional[Tuple[int, int]]:
        """Find next occurrence."""
        if not self.matches:
            return self.search(self.last_search, "forward")
            
        self.current_match_index = (self.current_match_index + 1) % len(self.matches)
        match = self.matches[self.current_match_index]
        return (match.line, match.start)
        
    def find_previous(self) -> Optional[Tuple[int, int]]:
        """Find previous occurrence."""
        if not self.matches:
            return self.search(self.last_search, "backward")
            
        self.current_match_index = (self.current_match_index - 1) % len(self.matches)
        match = self.matches[self.current_match_index]
        return (match.line, match.start)
        
    def replace(self, pattern: str, replacement: str, 
                flags: str = "") -> int:
        """Replace pattern with replacement."""
        count = 0
        
        # Parse flags
        global_replace = 'g' in flags
        confirm = 'c' in flags
        case_insensitive = 'i' in flags
        
        # Build regex
        regex_flags = 0
        if case_insensitive or not self.case_sensitive:
            regex_flags |= re.IGNORECASE
            
        try:
            regex = re.compile(pattern, regex_flags)
        except re.error:
            return 0
            
        # Perform replacement
        for i, line in enumerate(self.buffer.lines):
            if global_replace:
                new_line, n = regex.subn(replacement, line)
                if n > 0:
                    self.buffer.lines[i] = new_line
                    count += n
            else:
                match = regex.search(line)
                if match:
                    new_line = regex.sub(replacement, line, count=1)
                    self.buffer.lines[i] = new_line
                    count += 1
                    
        if count > 0:
            self.buffer.modified = True
            
        # Add to replace history
        self.replace_history.append((pattern, replacement))
        if len(self.replace_history) > 20:
            self.replace_history.pop(0)
            
        return count
        
    def highlight_matches(self) -> List[SearchMatch]:
        """Get all matches for highlighting."""
        return self.matches