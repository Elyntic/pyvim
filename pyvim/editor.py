"""Enhanced main editor class with v0.0.2a features."""

import curses
import sys
import os
import re
from typing import Optional, List, Tuple

from .buffer import Buffer
from .buffer_manager import BufferManager
from .display import Display
from .modes import Mode, ModeHandler
from .keybindings import KeyBindings
from .commands import CommandProcessor
from .config import Config, load_config
from .search import SearchEngine
from .visual import VisualModeHandler, VisualMode
from .syntax import SyntaxHighlighter
from .clipboard import ClipboardManager
from .window import Window, WindowManager, WindowLayout


class Editor:
    """Main editor class with enhanced features for v0.0.2a."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.buffer_manager = BufferManager()
        self.display = Display(self)
        self.mode_handler = ModeHandler(self)
        self.key_bindings = KeyBindings(self)
        self.command_processor = CommandProcessor(self)
        self.clipboard_manager = ClipboardManager()
        self.running = False
        self.message = ""
        self.last_command = None
        
        # v0.0.2a features
        self.search_engine = None
        self.visual_handler = None
        self.syntax_highlighter = SyntaxHighlighter()
        self.window_manager = None
        
        # Command history
        self.command_history = []
        self.command_history_index = -1
        
        # Macros
        self.macro_register = None
        self.macro_commands = []
        
        # For handling multi-key commands
        self.pending_command = None
        
    @property
    def buffer(self):
        """Get current buffer."""
        return self.buffer_manager.get_current_buffer()
        
    def run(self, filename: Optional[str] = None):
        """Main editor loop."""
        # Initialize buffer
        if filename:
            self.buffer_manager.open_file(filename)
            self.syntax_highlighter.detect_language(filename)
        else:
            self.buffer_manager.create_buffer()
            
        # Initialize components that need buffer
        self.search_engine = SearchEngine(self.buffer)
        self.visual_handler = VisualModeHandler(self.buffer)
        
        try:
            self.display.init_screen()
            
            # Initialize window manager
            self.window_manager = WindowManager(
                self.display.width,
                self.display.height
            )
            
            # Create initial window
            window = Window(
                self.buffer,
                WindowLayout(0, 0, self.display.width, self.display.height - 2)
            )
            self.window_manager.add_window(window)
            
            self.running = True
            
            # Show welcome message
            if not filename:
                self.message = "PyVim v0.0.2a - :help for help | :q to quit"
            else:
                file_info = self._get_file_info(filename)
                self.message = f'"{filename}" {file_info}'
                
            while self.running:
                self.adjust_viewport()
                self.display.render()
                self.handle_input()
                
        finally:
            self.display.cleanup_screen()
            
    def handle_input(self):
        """Handle user input."""
        key = self.display.screen.getch()
        
        # Record macro command if recording
        if self.clipboard_manager.is_recording():
            self.clipboard_manager.record_command(chr(key) if 0 < key < 127 else str(key))
            
        # Clear message on input
        if self.message and key != -1:
            self.message = ""
            
        # Handle visual mode
        if self.mode_handler.is_visual_mode():
            self.handle_visual_input(key)
        else:
            # Let key bindings handle the key
            if not self.key_bindings.handle_key(key):
                pass
                
    def handle_visual_input(self, key: int):
        """Handle input in visual mode."""
        # Movement updates selection
        if key in [ord('h'), ord('j'), ord('k'), ord('l'), 
                   curses.KEY_LEFT, curses.KEY_DOWN, curses.KEY_UP, curses.KEY_RIGHT]:
            self.key_bindings.handle_key(key)
            self.visual_handler.update_selection()
            
        # Operations on selection
        elif key == ord('d'):  # Delete selection
            text = self.visual_handler.get_selected_text()
            self.clipboard_manager.delete(text.split('\n'), line_mode=self.visual_handler.mode == VisualMode.LINE)
            self.visual_handler.delete_selection()
            self.exit_visual_mode()
            
        elif key == ord('y'):  # Yank selection
            text = self.visual_handler.get_selected_text()
            self.clipboard_manager.yank(text.split('\n'), line_mode=self.visual_handler.mode == VisualMode.LINE)
            self.exit_visual_mode()
            self.message = f"{len(text.split(chr(10)))} lines yanked"
            
        elif key == ord('>'):  # Indent
            self.visual_handler.indent_selection(True)
            self.exit_visual_mode()
            
        elif key == ord('<'):  # Unindent
            self.visual_handler.indent_selection(False)
            self.exit_visual_mode()
            
        elif key == 27:  # ESC - exit visual mode
            self.exit_visual_mode()
            
    # ============= Basic Movement and Editing =============
    
    def enter_insert_mode(self, append: bool = False):
        """Enter insert mode."""
        if append and self.buffer.cursor_x < len(self.buffer.get_current_line()):
            self.buffer.move_cursor(dx=1)
        self.mode_handler.set_mode(Mode.INSERT)
        
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
        
    def append_at_line_end(self):
        """Move to end of line and enter insert mode (A command)."""
        self.goto_line_end()
        self.enter_insert_mode()
        
    def insert_at_line_start(self):
        """Move to start of line and enter insert mode (I command)."""
        # Skip leading whitespace
        line = self.buffer.get_current_line()
        first_non_space = 0
        for i, char in enumerate(line):
            if not char.isspace():
                first_non_space = i
                break
        self.buffer.cursor_x = first_non_space
        self.enter_insert_mode()
        
    # ============= Character Operations =============
    
    def delete_char_under_cursor(self):
        """Delete character under cursor (x command)."""
        self.buffer.delete_char_at_cursor()
        
    def backspace_in_normal_mode(self):
        """Handle X command - backspace in normal mode."""
        if self.buffer.cursor_x > 0:
            self.buffer.move_cursor(dx=-1)
            self.delete_char_under_cursor()
            
    def handle_backspace(self):
        """Handle backspace key in insert mode."""
        self.buffer.backspace()
        
    def handle_tab(self):
        """Handle tab key in insert mode."""
        if self.config.use_spaces:
            # Insert spaces instead of tab
            for _ in range(self.config.tab_size):
                self.buffer.insert_char(' ')
        else:
            self.buffer.insert_char('\t')
            
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
        
    # ============= Navigation =============
    
    def goto_line_start(self):
        """Move cursor to start of line (0 command)."""
        self.buffer.cursor_x = 0
        
    def goto_line_end(self):
        """Move cursor to end of line ($ command)."""
        self.buffer.cursor_x = len(self.buffer.get_current_line())
        
    def goto_first_line(self):
        """Go to first line (gg command)."""
        self.buffer.cursor_y = 0
        self.buffer.cursor_x = 0
        
    def goto_last_line(self):
        """Go to last line (G command)."""
        self.buffer.cursor_y = len(self.buffer.lines) - 1
        self.buffer.cursor_x = 0
        
    def next_word(self):
        """Move to next word (w command)."""
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
        """Move to previous word (b command)."""
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
        """Scroll up one page (Ctrl-B)."""
        page_size = self.display.height - 3
        self.buffer.move_cursor(dy=-page_size)
        
    def page_down(self):
        """Scroll down one page (Ctrl-F)."""
        page_size = self.display.height - 3
        self.buffer.move_cursor(dy=page_size)
        
    # ============= Multi-key Commands =============
    
    def handle_g_command(self):
        """Handle 'g' command (gg for first line)."""
        key = self.display.screen.getch()
        if key == ord('g'):
            self.goto_first_line()
            self.message = "First line"
        elif key == ord('0'):
            # g0 - go to first character of screen line
            self.buffer.cursor_x = self.buffer.offset_x
        elif key == ord('$'):
            # g$ - go to last character of screen line
            max_x = self.buffer.offset_x + self.display.width - 1
            line_length = len(self.buffer.get_current_line())
            self.buffer.cursor_x = min(max_x, line_length)
            
    def handle_d_command(self):
        """Handle 'd' command (dd for delete line, dw for delete word, etc.)."""
        key = self.display.screen.getch()
        
        if key == ord('d'):
            # dd - delete line
            self.buffer.undo_manager.save_state("Delete line")
            line = self.buffer.get_current_line()
            self.clipboard_manager.delete([line], '"', line_mode=True)
            self.buffer.delete_line()
            self.message = "1 line deleted"
            
        elif key == ord('w'):
            # dw - delete word
            self.buffer.undo_manager.save_state("Delete word")
            start_x = self.buffer.cursor_x
            self.next_word()
            end_x = self.buffer.cursor_x
            
            line = self.buffer.get_current_line()
            deleted = line[start_x:end_x]
            self.buffer.lines[self.buffer.cursor_y] = line[:start_x] + line[end_x:]
            self.buffer.cursor_x = start_x
            self.buffer.modified = True
            self.clipboard_manager.delete([deleted], '"')
            self.message = "Word deleted"
            
        elif key == ord('0'):
            # d0 - delete to beginning of line
            self.buffer.undo_manager.save_state("Delete to line start")
            line = self.buffer.get_current_line()
            deleted = line[:self.buffer.cursor_x]
            self.buffer.lines[self.buffer.cursor_y] = line[self.buffer.cursor_x:]
            self.buffer.cursor_x = 0
            self.buffer.modified = True
            self.clipboard_manager.delete([deleted], '"')
            
        elif key == ord('$'):
            # d$ - delete to end of line
            self.buffer.undo_manager.save_state("Delete to line end")
            line = self.buffer.get_current_line()
            deleted = line[self.buffer.cursor_x:]
            self.buffer.lines[self.buffer.cursor_y] = line[:self.buffer.cursor_x]
            if self.buffer.cursor_x > 0:
                self.buffer.cursor_x -= 1
            self.buffer.modified = True
            self.clipboard_manager.delete([deleted], '"')
            
    def handle_y_command(self):
        """Handle 'y' command (yy for yank line, yw for yank word, etc.)."""
        key = self.display.screen.getch()
        
        if key == ord('y'):
            # yy - yank line
            line = self.buffer.get_current_line()
            self.clipboard_manager.yank([line], '"', line_mode=True)
            self.message = "1 line yanked"
            
        elif key == ord('w'):
            # yw - yank word
            start_x = self.buffer.cursor_x
            old_y = self.buffer.cursor_y
            self.next_word()
            end_x = self.buffer.cursor_x
            
            if self.buffer.cursor_y == old_y:
                line = self.buffer.get_current_line()
                yanked = line[start_x:end_x]
                self.clipboard_manager.yank([yanked], '"')
                self.buffer.cursor_x = start_x  # Return cursor to original position
                self.message = "Word yanked"
            else:
                # Word spans multiple lines
                self.buffer.cursor_y = old_y
                self.buffer.cursor_x = start_x
                
        elif key == ord('0'):
            # y0 - yank to beginning of line
            line = self.buffer.get_current_line()
            yanked = line[:self.buffer.cursor_x]
            self.clipboard_manager.yank([yanked], '"')
            self.message = "Yanked to line start"
            
        elif key == ord('$'):
            # y$ - yank to end of line
            line = self.buffer.get_current_line()
            yanked = line[self.buffer.cursor_x:]
            self.clipboard_manager.yank([yanked], '"')
            self.message = "Yanked to line end"
            
    # ============= Paste Operations =============
    
    def paste_after(self):
        """Paste clipboard content after cursor (p command)."""
        result = self.clipboard_manager.put('"')
        if result:
            lines, line_mode = result
            self.buffer.undo_manager.save_state("Paste")
            
            if line_mode:
                # Paste lines after current line
                for i, line in enumerate(lines):
                    self.buffer.lines.insert(self.buffer.cursor_y + i + 1, line)
                self.buffer.cursor_y += 1
                self.buffer.cursor_x = 0
            else:
                # Paste at cursor position
                current_line = self.buffer.get_current_line()
                text = ''.join(lines)
                self.buffer.lines[self.buffer.cursor_y] = (
                    current_line[:self.buffer.cursor_x + 1] + 
                    text + 
                    current_line[self.buffer.cursor_x + 1:]
                )
                self.buffer.cursor_x += len(text)
                
            self.buffer.modified = True
            self.message = f"{len(lines)} line(s) pasted"
        else:
            self.message = "Nothing to paste"
            
    def paste_before(self):
        """Paste clipboard content before cursor (P command)."""
        result = self.clipboard_manager.put('"')
        if result:
            lines, line_mode = result
            self.buffer.undo_manager.save_state("Paste before")
            
            if line_mode:
                # Paste lines before current line
                for i, line in enumerate(lines):
                    self.buffer.lines.insert(self.buffer.cursor_y + i, line)
                self.buffer.cursor_x = 0
            else:
                # Paste before cursor position
                current_line = self.buffer.get_current_line()
                text = ''.join(lines)
                self.buffer.lines[self.buffer.cursor_y] = (
                    current_line[:self.buffer.cursor_x] + 
                    text + 
                    current_line[self.buffer.cursor_x:]
                )
                
            self.buffer.modified = True
            self.message = f"{len(lines)} line(s) pasted"
        else:
            self.message = "Nothing to paste"
            
    # ============= Visual Mode =============
    
    def enter_visual_mode(self, mode: VisualMode = VisualMode.CHARACTER):
        """Enter visual mode."""
        self.mode_handler.set_mode(Mode.VISUAL)
        self.visual_handler.start_selection(mode)
        
    def exit_visual_mode(self):
        """Exit visual mode."""
        self.visual_handler.clear_selection()
        self.mode_handler.set_mode(Mode.NORMAL)
        
    # ============= Search Operations =============
    
    def search_forward(self):
        """Start forward search (/ command)."""
        self.mode_handler.set_mode(Mode.COMMAND)
        pattern = self.display.show_command_line("/")
        
        if pattern:
            result = self.search_engine.search(pattern, "forward")
            if result:
                self.buffer.add_jump_position()
                self.buffer.cursor_y, self.buffer.cursor_x = result
                self.message = f"/{pattern}"
            else:
                self.message = f"Pattern not found: {pattern}"
                
        self.mode_handler.set_mode(Mode.NORMAL)
        
    def search_backward(self):
        """Start backward search (? command)."""
        self.mode_handler.set_mode(Mode.COMMAND)
        pattern = self.display.show_command_line("?")
        
        if pattern:
            result = self.search_engine.search(pattern, "backward")
            if result:
                self.buffer.add_jump_position()
                self.buffer.cursor_y, self.buffer.cursor_x = result
                self.message = f"?{pattern}"
            else:
                self.message = f"Pattern not found: {pattern}"
                
        self.mode_handler.set_mode(Mode.NORMAL)
        
    def find_next(self):
        """Find next occurrence (n command)."""
        result = self.search_engine.find_next()
        if result:
            self.buffer.add_jump_position()
            self.buffer.cursor_y, self.buffer.cursor_x = result
            matches = len(self.search_engine.matches)
            current = self.search_engine.current_match_index + 1
            self.message = f"[{current}/{matches}]"
        else:
            self.message = "No matches found"
            
    def find_previous(self):
        """Find previous occurrence (N command)."""
        result = self.search_engine.find_previous()
        if result:
            self.buffer.add_jump_position()
            self.buffer.cursor_y, self.buffer.cursor_x = result
            matches = len(self.search_engine.matches)
            current = self.search_engine.current_match_index + 1
            self.message = f"[{current}/{matches}]"
        else:
            self.message = "No matches found"
            
    # ============= Undo/Redo =============
    
    def undo(self):
        """Undo last change (u command)."""
        if self.buffer.undo_manager.undo():
            self.message = "Undo"
        else:
            self.message = "Already at oldest change"
            
    def redo(self):
        """Redo previously undone change (Ctrl-R)."""
        if self.buffer.undo_manager.redo():
            self.message = "Redo"
        else:
            self.message = "Already at newest change"
            
    # ============= Marks and Jumps =============
    
    def set_mark(self):
        """Set a mark at current position (m command)."""
        key = self.display.screen.getch()
        if key > 0:
            mark = chr(key)
            self.buffer.set_mark(mark)
            self.message = f"Mark {mark} set"
            
    def goto_mark(self):
        """Go to a mark (' command)."""
        key = self.display.screen.getch()
        if key > 0:
            mark = chr(key)
            if self.buffer.goto_mark(mark):
                self.message = f"Jumped to mark {mark}"
            else:
                self.message = f"Mark {mark} not set"
                
    def jump_backward(self):
        """Jump backward in jump list (Ctrl-O)."""
        if self.buffer.jump_backward():
            self.message = "Jumped backward"
        else:
            self.message = "No previous jump"
            
    def jump_forward(self):
        """Jump forward in jump list (Ctrl-I)."""
        if self.buffer.jump_forward():
            self.message = "Jumped forward"
        else:
            self.message = "No next jump"
            
    # ============= Macros =============
    
    def start_recording_macro(self):
        """Start recording a macro (q command)."""
        key = self.display.screen.getch()
        if key > 0 and chr(key).isalpha():
            register = chr(key).lower()
            self.clipboard_manager.start_recording(register)
            self.message = f"Recording @{register}"
            
    def stop_recording_macro(self):
        """Stop recording macro."""
        if self.clipboard_manager.is_recording():
            register = self.clipboard_manager.recording_register
            self.clipboard_manager.stop_recording()
            self.message = f"Recorded macro @{register}"
            
    def play_macro(self):
        """Play a recorded macro (@ command)."""
        key = self.display.screen.getch()
        if key > 0 and chr(key).isalpha():
            register = chr(key).lower()
            commands = self.clipboard_manager.play_macro(register)
            
            # Execute macro commands
            for cmd in commands:
                if cmd.isdigit():
                    self.key_bindings.handle_key(int(cmd))
                else:
                    self.key_bindings.handle_key(ord(cmd))
                    
            self.message = f"Executed macro @{register}"
            
    # ============= Window Management =============
    
    def split_window_horizontal(self):
        """Split window horizontally (:split command)."""
        from .window import SplitType
        new_window = self.window_manager.split_window(SplitType.HORIZONTAL)
        if new_window:
            self.message = "Window split horizontally"
        else:
            self.message = "Cannot split window"
            
    def split_window_vertical(self):
        """Split window vertically (:vsplit command)."""
        from .window import SplitType
        new_window = self.window_manager.split_window(SplitType.VERTICAL)
        if new_window:
            self.message = "Window split vertically"
        else:
            self.message = "Cannot split window"
            
    def next_window(self):
        """Switch to next window (Ctrl-W w)."""
        self.window_manager.next_window()
        self.message = f"Window {self.window_manager.active_window_index + 1}"
        
    def close_window(self):
        """Close current window (:close command)."""
        if self.window_manager.close_window():
            self.message = "Window closed"
        else:
            self.message = "Cannot close last window"
            
    # ============= Utility Methods =============
    
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
            
    def _get_file_info(self, filename: str) -> str:
        """Get file information string."""
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            lines = len(self.buffer.lines)
            return f"{lines}L, {size}B"
        else:
            return "[New File]"