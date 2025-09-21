"""Main editor class."""

import curses
import sys
import re
from typing import Optional, List

from .buffer import Buffer
from .display import Display
from .modes import Mode, ModeHandler
from .keybindings import KeyBindings
from .commands import CommandProcessor
from .config import Config, load_config


class Editor:
    """Main editor class that coordinates all components."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.buffer = None
        self.display = Display(self)
        self.mode_handler = ModeHandler(self)
        self.key_bindings = KeyBindings(self)
        self.command_processor = CommandProcessor(self)
        self.running = False
        self.last_command = None
        self.clipboard = []  # For copy/paste operations
        self.message = ""    # Status message
        
    def run(self, filename: Optional[str] = None):
        """Main editor loop."""
        self.buffer = Buffer(filename)
        
        try:
            self.display.init_screen()
            self.running = True
            
            # Show welcome message if new file
            if not filename:
                self.message = "PyVim v0.0.1a - Type :help for help"
            
            while self.running:
                self.adjust_viewport()
                self.display.render()
                self.handle_input()
                
        finally:
            self.display.cleanup_screen()
            
    def handle_input(self):
        """Handle user input."""
        key = self.display.screen.getch()
        
        # Clear message after any key press
        if self.message:
            self.message = ""
        
        # Let key bindings handle the key
        if not self.key_bindings.handle_key(key):
            # Key not handled by bindings
            pass
            
    def handle_backspace(self):
        """Handle backspace key in insert mode."""
        self.buffer.backspace()
        
    def backspace_in_normal_mode(self):
        """Handle X command - backspace in normal mode."""
        if self.buffer.cursor_x > 0:
            self.buffer.move_cursor(dx=-1)
            self.delete_char_under_cursor()
            
    def handle_tab(self):
        """Handle tab key in insert mode."""
        if self.config.use_spaces:
            # Insert spaces instead of tab
            for _ in range(self.config.tab_size):
                self.buffer.insert_char(' ')
        else:
            self.buffer.insert_char('\t')
            
    def enter_insert_mode(self, append: bool = False):
        """Enter insert mode."""
        if append and self.buffer.cursor_x < len(self.buffer.get_current_line()):
            self.buffer.move_cursor(dx=1)
        self.mode_handler.set_mode(Mode.INSERT)
        
    def append_at_line_end(self):
        """Move to end of line and enter insert mode."""
        self.goto_line_end()
        self.enter_insert_mode()
        
    def insert_at_line_start(self):
        """Move to start of line and enter insert mode."""
        self.goto_line_start()
        self.enter_insert_mode()
        
    def exit_insert_mode(self):
        """Exit insert mode and return to normal mode."""
        self.mode_handler.set_mode(Mode.NORMAL)
        # Move cursor back one position if not at start of line
        if self.buffer.cursor_x > 0:
            self.buffer.move_cursor(dx=-1)
            
    def enter_command_mode(self):
        """Enter command mode."""
        self.mode_handler.set_mode(Mode.COMMAND)
        command = self.display.show_command_line(":")
        
        if command:
            result = self.command_processor.execute(command)
            if result:
                self.message = result
                self.display.show_message(result)
                self.display.screen.getch()  # Wait for key press
                
        self.mode_handler.set_mode(Mode.NORMAL)
        
    def open_line_below(self):
        """Open new line below and enter insert mode."""
        # Move to end of current line first
        self.goto_line_end()
        self.handle_enter()
        self.mode_handler.set_mode(Mode.INSERT)
        
    def open_line_above(self):
        """Open new line above and enter insert mode."""
        self.goto_line_start()
        self.buffer.insert_line(below=False)
        self.enter_insert_mode()
        
    def delete_char_under_cursor(self):
        """Delete character under cursor (x command)."""
        self.buffer.delete_char_at_cursor()
            
    def handle_enter(self):
        """Handle enter key in insert mode."""
        line = self.buffer.get_current_line()
        # Split current line at cursor
        before = line[:self.buffer.cursor_x]
        after = line[self.buffer.cursor_x:]
        
        self.buffer.lines[self.buffer.cursor_y] = before
        self.buffer.lines.insert(self.buffer.cursor_y + 1, after)
        self.buffer.cursor_y += 1
        
        # Auto-indent: match indentation of previous line
        if self.config.auto_indent:
            indent_match = re.match(r'^(\s*)', before)
            if indent_match:
                indent = indent_match.group(1)
                self.buffer.lines[self.buffer.cursor_y] = indent + self.buffer.lines[self.buffer.cursor_y]
                self.buffer.cursor_x = len(indent)
            else:
                self.buffer.cursor_x = 0
        else:
            self.buffer.cursor_x = 0
            
        self.buffer.modified = True
        
    def goto_line_start(self):
        """Move cursor to start of line."""
        self.buffer.cursor_x = 0
        
    def goto_line_end(self):
        """Move cursor to end of line."""
        self.buffer.cursor_x = len(self.buffer.get_current_line())
        
    def goto_first_line(self):
        """Go to first line."""
        self.buffer.cursor_y = 0
        self.buffer.cursor_x = 0
        
    def goto_last_line(self):
        """Go to last line."""
        self.buffer.cursor_y = len(self.buffer.lines) - 1
        self.buffer.cursor_x = 0
        
    def next_word(self):
        """Move to next word."""
        line = self.buffer.get_current_line()
        x = self.buffer.cursor_x
        
        # Skip current word
        while x < len(line) and line[x].isalnum():
            x += 1
        # Skip spaces
        while x < len(line) and not line[x].isalnum():
            x += 1
            
        if x < len(line):
            self.buffer.cursor_x = x
        elif self.buffer.cursor_y < len(self.buffer.lines) - 1:
            self.buffer.cursor_y += 1
            self.buffer.cursor_x = 0
            
    def prev_word(self):
        """Move to previous word."""
        line = self.buffer.get_current_line()
        x = self.buffer.cursor_x
        
        if x > 0:
            x -= 1
            # Skip spaces
            while x > 0 and not line[x].isalnum():
                x -= 1
            # Skip to beginning of word
            while x > 0 and line[x-1].isalnum():
                x -= 1
            self.buffer.cursor_x = x
        elif self.buffer.cursor_y > 0:
            self.buffer.cursor_y -= 1
            self.goto_line_end()
            
    def page_up(self):
        """Scroll up one page."""
        page_size = self.display.height - 3
        self.buffer.move_cursor(dy=-page_size)
        
    def page_down(self):
        """Scroll down one page."""
        page_size = self.display.height - 3
        self.buffer.move_cursor(dy=page_size)
        
    def handle_g_command(self):
        """Handle 'g' command (gg for first line)."""
        key = self.display.screen.getch()
        if key == ord('g'):
            self.goto_first_line()
            
    def handle_d_command(self):
        """Handle 'd' command (dd for delete line)."""
        key = self.display.screen.getch()
        if key == ord('d'):
            # Copy line to clipboard before deleting
            self.clipboard = [self.buffer.get_current_line()]
            self.buffer.delete_line()
            self.message = "1 line deleted"
            
    def handle_y_command(self):
        """Handle 'y' command (yy for yank/copy line)."""
        key = self.display.screen.getch()
        if key == ord('y'):
            self.clipboard = [self.buffer.get_current_line()]
            self.message = "1 line yanked"
            
    def paste_after(self):
        """Paste clipboard content after current line."""
        if self.clipboard:
            for i, line in enumerate(self.clipboard):
                self.buffer.lines.insert(self.buffer.cursor_y + i + 1, line)
            self.buffer.cursor_y += 1
            self.buffer.cursor_x = 0
            self.buffer.modified = True
            self.message = f"{len(self.clipboard)} line(s) pasted"
            
    def paste_before(self):
        """Paste clipboard content before current line."""
        if self.clipboard:
            for i, line in enumerate(self.clipboard):
                self.buffer.lines.insert(self.buffer.cursor_y + i, line)
            self.buffer.cursor_x = 0
            self.buffer.modified = True
            self.message = f"{len(self.clipboard)} line(s) pasted"
            
    def adjust_viewport(self):
        """Adjust viewport to keep cursor visible."""
        if not self.display.screen:
            return
            
        visible_height = self.display.height - 2
        
        # Vertical adjustment
        if self.buffer.cursor_y < self.buffer.offset_y:
            self.buffer.offset_y = self.buffer.cursor_y
        elif self.buffer.cursor_y >= self.buffer.offset_y + visible_height:
            self.buffer.offset_y = self.buffer.cursor_y - visible_height + 1
            
        # Horizontal adjustment
        visible_width = self.display.width
        if self.config.show_line_numbers:
            visible_width -= 5
            
        if self.buffer.cursor_x < self.buffer.offset_x:
            self.buffer.offset_x = self.buffer.cursor_x
        elif self.buffer.cursor_x >= self.buffer.offset_x + visible_width:
            self.buffer.offset_x = self.buffer.cursor_x - visible_width + 1