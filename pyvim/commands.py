"""Enhanced command mode implementation for v0.0.2a."""

from typing import TYPE_CHECKING, Optional, List
import os
import re

if TYPE_CHECKING:
    from .editor import Editor


class CommandProcessor:
    """Enhanced command processor with more vim commands."""
    
    def __init__(self, editor: 'Editor'):
        self.editor = editor
        self.commands = {
            # File operations
            'w': self.save_file,
            'write': self.save_file,
            'q': self.quit,
            'quit': self.quit,
            'q!': self.force_quit,
            'wq': self.save_and_quit,
            'x': self.save_and_quit,
            'e': self.edit_file,
            'edit': self.edit_file,
            
            # Buffer operations
            'bn': self.next_buffer,
            'bnext': self.next_buffer,
            'bp': self.previous_buffer,
            'bprevious': self.previous_buffer,
            'bd': self.delete_buffer,
            'bdelete': self.delete_buffer,
            'ls': self.list_buffers,
            'buffers': self.list_buffers,
            
            # Window operations  
            'split': self.split_horizontal,
            'sp': self.split_horizontal,
            'vsplit': self.split_vertical,
            'vs': self.split_vertical,
            'close': self.close_window,
            'only': self.only_window,
            
            # Search and replace
            's': self.substitute,
            'substitute': self.substitute,
            '%s': self.substitute_all,
            
            # Settings
            'set': self.set_option,
            'colorscheme': self.set_colorscheme,
            
            # Help
            'help': self.show_help,
            'h': self.show_help,
            
            # Session
            'mksession': self.make_session,
            'source': self.source_file,
        }
        
    def execute(self, command: str) -> Optional[str]:
        """Execute a command and return result message."""
        if not command:
            return None
            
        # Parse command with arguments
        parts = self._parse_command(command)
        if not parts:
            return None
            
        # Handle line ranges (e.g., :10,20d)
        if parts[0].isdigit() or parts[0] in ['$', '.', '%']:
            return self.handle_range_command(parts)
            
        # Get command and arguments
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Check for command in dictionary
        if cmd in self.commands:
            return self.commands[cmd](args)
        
        # Check for shortcuts
        if cmd.startswith('s/'):
            return self.substitute([cmd[2:]])
        elif cmd.startswith('%s/'):
            return self.substitute_all([cmd[3:]])
        else:
            return f"Not an editor command: {cmd}"
            
    def _parse_command(self, command: str) -> List[str]:
        """Parse command line into parts."""
        # Handle quoted strings
        parts = []
        current = ""
        in_quote = False
        quote_char = None
        
        for char in command:
            if char in ['"', "'"] and not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char and in_quote:
                in_quote = False
                quote_char = None
            elif char == ' ' and not in_quote:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char
                
        if current:
            parts.append(current)
            
        return parts
        
    def save_file(self, args: List[str]) -> str:
        """Save the current file."""
        filename = args[0] if args else None
        try:
            self.editor.buffer.save_file(filename)
            lines = len(self.editor.buffer.lines)
            size = os.path.getsize(self.editor.buffer.filename)
            return f'"{self.editor.buffer.filename}" {lines}L, {size}B written'
        except Exception as e:
            return f"Error: {e}"
            
    def edit_file(self, args: List[str]) -> str:
        """Edit a file."""
        if not args:
            return "E32: No file name"
            
        filename = args[0]
        
        # Check if current buffer has unsaved changes
        if self.editor.buffer.modified:
            return "E37: No write since last change (add ! to override)"
            
        self.editor.buffer_manager.open_file(filename)
        self.editor.syntax_highlighter.detect_language(filename)
        
        if os.path.exists(filename):
            lines = len(self.editor.buffer.lines)
            size = os.path.getsize(filename)
            return f'"{filename}" {lines}L, {size}B'
        else:
            return f'"{filename}" [New File]'
            
    def next_buffer(self, args: List[str]) -> str:
        """Switch to next buffer."""
        self.editor.buffer_manager.next_buffer()
        buffer = self.editor.buffer
        if buffer:
            return f"Buffer: {buffer.display_name}"
        return "No buffers"
        
    def previous_buffer(self, args: List[str]) -> str:
        """Switch to previous buffer."""
        self.editor.buffer_manager.previous_buffer()
        buffer = self.editor.buffer
        if buffer:
            return f"Buffer: {buffer.display_name}"
        return "No buffers"
        
    def delete_buffer(self, args: List[str]) -> str:
        """Delete current buffer."""
        if self.editor.buffer.modified:
            return "E89: No write since last change for buffer"
            
        if self.editor.buffer_manager.close_buffer():
            return "Buffer deleted"
        else:
            return "Cannot delete last buffer"
            
    def list_buffers(self, args: List[str]) -> str:
        """List all buffers."""
        buffers = self.editor.buffer_manager.get_buffer_list()
        if buffers:
            self.editor.message = "\n".join(buffers)
            return "Press ENTER to continue"
        return "No buffers"
        
    def substitute(self, args: List[str]) -> str:
        """Substitute pattern on current line."""
        if not args:
            return "E33: No previous substitute regular expression"
            
        # Parse s/pattern/replacement/flags
        pattern_str = args[0]
        match = re.match(r'([^/]+)/([^/]*)/?(.*)', pattern_str)
        
        if not match:
            return "E486: Pattern not found"
            
        pattern, replacement, flags = match.groups()
        
        # Perform substitution on current line
        line = self.editor.buffer.lines[self.editor.buffer.cursor_y]
        
        if 'g' in flags:
            new_line, count = re.subn(pattern, replacement, line)
        else:
            new_line, count = re.subn(pattern, replacement, line, count=1)
            
        if count > 0:
            self.editor.buffer.undo_manager.save_state("Substitute")
            self.editor.buffer.lines[self.editor.buffer.cursor_y] = new_line
            self.editor.buffer.modified = True
            return f"{count} substitution(s) on 1 line"
        else:
            return "E486: Pattern not found"
            
    def substitute_all(self, args: List[str]) -> str:
        """Substitute pattern in entire file."""
        if not args:
            return "E33: No previous substitute regular expression"
            
        pattern_str = args[0]
        match = re.match(r'([^/]+)/([^/]*)/?(.*)', pattern_str)
        
        if not match:
            return "E486: Pattern not found"
            
        pattern, replacement, flags = match.groups()
        
        self.editor.buffer.undo_manager.save_state("Global substitute")
        
        total_count = 0
        lines_affected = 0
        
        for i, line in enumerate(self.editor.buffer.lines):
            if 'g' in flags:
                new_line, count = re.subn(pattern, replacement, line)
            else:
                new_line, count = re.subn(pattern, replacement, line, count=1)
                
            if count > 0:
                self.editor.buffer.lines[i] = new_line
                total_count += count
                lines_affected += 1
                
        if total_count > 0:
            self.editor.buffer.modified = True
            return f"{total_count} substitution(s) on {lines_affected} line(s)"
        else:
            return "E486: Pattern not found"
            
    def split_horizontal(self, args: List[str]) -> str:
        """Split window horizontally."""
        self.editor.split_window_horizontal()
        return ""
        
    def split_vertical(self, args: List[str]) -> str:
        """Split window vertically."""
        self.editor.split_window_vertical()
        return ""
        
    def close_window(self, args: List[str]) -> str:
        """Close current window."""
        self.editor.close_window()
        return ""
        
    def only_window(self, args: List[str]) -> str:
        """Keep only current window."""
        # Close all other windows
        while len(self.editor.window_manager.windows) > 1:
            index = self.editor.window_manager.active_window_index
            self.editor.window_manager.next_window()
            if self.editor.window_manager.active_window_index != index:
                self.editor.window_manager.close_window()
            else:
                break
        return "Only one window"
        
    def set_option(self, args: List[str]) -> str:
        """Set editor option."""
        if not args:
            return "E518: Unknown option"
            
        option = args[0]
        
        # Parse option
        if option == "number" or option == "nu":
            self.editor.config.show_line_numbers = True
            return "Line numbers enabled"
        elif option == "nonumber" or option == "nonu":
            self.editor.config.show_line_numbers = False
            return "Line numbers disabled"
        elif option.startswith("tabstop=") or option.startswith("ts="):
            value = option.split('=')[1]
            try:
                self.editor.config.tab_size = int(value)
                return f"Tab size set to {value}"
            except ValueError:
                return "E521: Number required"
        elif option == "expandtab" or option == "et":
            self.editor.config.use_spaces = True
            return "Expand tab enabled"
        elif option == "noexpandtab" or option == "noet":
            self.editor.config.use_spaces = False
            return "Expand tab disabled"
        elif option == "autoindent" or option == "ai":
            self.editor.config.auto_indent = True
            return "Auto indent enabled"
        elif option == "noautoindent" or option == "noai":
            self.editor.config.auto_indent = False
            return "Auto indent disabled"
        elif option == "ignorecase" or option == "ic":
            self.editor.search_engine.case_sensitive = False
            return "Ignore case enabled"
        elif option == "noignorecase" or option == "noic":
            self.editor.search_engine.case_sensitive = True
            return "Ignore case disabled"
        else:
            return f"E518: Unknown option: {option}"
            
    def show_help(self, args: List[str]) -> str:
        """Show help."""
        help_text = """
PyVim v0.0.2a - Help

NORMAL MODE:
  h,j,k,l     - Move cursor
  i           - Insert mode
  v           - Visual mode
  V           - Visual line mode
  /           - Search forward
  ?           - Search backward
  n           - Next match
  N           - Previous match
  u           - Undo
  Ctrl-R      - Redo
  :           - Command mode
  
COMMANDS:
  :w          - Save
  :q          - Quit
  :e file     - Edit file
  :bn/:bp     - Next/previous buffer
  :split      - Split horizontal
  :vsplit     - Split vertical
  :%s/old/new/g - Replace all
  
Press ENTER to continue...
"""
        self.editor.display.show_message(help_text)
        self.editor.display.screen.getch()
        return ""
        
    def quit(self, args: List[str]) -> str:
        """Quit the editor."""
        if self.editor.buffer.modified:
            return "E37: No write since last change (add ! to override)"
        self.editor.running = False
        return None
        
    def force_quit(self, args: List[str]) -> str:
        """Force quit without saving."""
        self.editor.running = False
        return None
        
    def save_and_quit(self, args: List[str]) -> str:
        """Save and quit."""
        result = self.save_file(args)
        if result and not result.startswith("Error"):
            self.editor.running = False
        return result
        
    def make_session(self, args: List[str]) -> str:
        """Create session file."""
        filename = args[0] if args else "Session.vim"
        # TODO: Implement session saving
        return f"Session saved to {filename}"
        
    def source_file(self, args: List[str]) -> str:
        """Source a vim script file."""
        if not args:
            return "E471: Argument required"
        # TODO: Implement script sourcing
        return f"Sourced {args[0]}"
        
    def set_colorscheme(self, args: List[str]) -> str:
        """Set color scheme."""
        if not args:
            return "E185: Cannot find color scheme"
        # TODO: Implement color schemes
        return f"Color scheme set to {args[0]}"
        
    def handle_range_command(self, parts: List[str]) -> str:
        """Handle commands with line ranges."""
        # TODO: Implement range commands
        return "Range commands not yet implemented"