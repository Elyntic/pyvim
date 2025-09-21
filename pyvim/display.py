"""Display and UI handling."""

import curses
from typing import TYPE_CHECKING

from pyvim.modes import Mode

if TYPE_CHECKING:
    from .editor import Editor


class Display:
    """Handles terminal display and rendering."""
    
    def __init__(self, editor: 'Editor'):
        self.editor = editor
        self.screen = None
        self.height = 0
        self.width = 0
        
    def init_screen(self):
        """Initialize curses screen."""
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.screen.keypad(True)
        curses.curs_set(1)  # Show cursor
        
        # Get terminal dimensions
        self.height, self.width = self.screen.getmaxyx()
        
        # Initialize color pairs if supported
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()  # Use terminal's default colors
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Status bar
            curses.init_pair(2, curses.COLOR_YELLOW, -1)  # Line numbers
            curses.init_pair(3, curses.COLOR_GREEN, -1)  # Mode indicator
            curses.init_pair(4, curses.COLOR_RED, -1)    # Error messages
            curses.init_pair(5, curses.COLOR_CYAN, -1)   # Info messages
            
    def cleanup_screen(self):
        """Cleanup curses screen."""
        if self.screen:
            self.screen.keypad(False)
            curses.nocbreak()
            curses.echo()
            curses.endwin()
            
    def render(self):
        """Render the entire screen."""
        if not self.screen:
            return
            
        self.screen.clear()
        
        # Calculate visible area
        visible_height = self.height - 2  # Reserve for status bar and command line
        buffer = self.editor.buffer
        
        # Render text lines
        for y in range(visible_height):
            line_num = y + buffer.offset_y
            
            if line_num < len(buffer.lines):
                # Show line numbers if enabled
                if self.editor.config.show_line_numbers:
                    line_num_str = f"{line_num + 1:4} "
                    try:
                        self.screen.addstr(y, 0, line_num_str, curses.color_pair(2))
                    except curses.error:
                        pass
                    x_offset = len(line_num_str)
                else:
                    x_offset = 0
                    
                # Render line content
                line = buffer.lines[line_num]
                if buffer.offset_x < len(line):
                    visible_line = line[buffer.offset_x:buffer.offset_x + self.width - x_offset]
                    try:
                        self.screen.addstr(y, x_offset, visible_line)
                    except curses.error:
                        pass
            else:
                # Empty line indicator
                try:
                    self.screen.addstr(y, 0, "~", curses.color_pair(2))
                except curses.error:
                    pass
                
        # Render status bar
        self.update_status_bar()
        
        # Show message if any
        if self.editor.message:
            self.show_message(self.editor.message, temporary=False)
        
        # Position cursor
        cursor_screen_y = buffer.cursor_y - buffer.offset_y
        cursor_screen_x = buffer.cursor_x - buffer.offset_x
        
        if self.editor.config.show_line_numbers:
            cursor_screen_x += 5
            
        # Ensure cursor is within screen bounds
        if 0 <= cursor_screen_y < visible_height and 0 <= cursor_screen_x < self.width:
            try:
                self.screen.move(cursor_screen_y, cursor_screen_x)
            except curses.error:
                pass
            
        self.screen.refresh()
        
    def update_status_bar(self):
        """Update the status bar."""
        if not self.screen:
            return
            
        buffer = self.editor.buffer
        mode = self.editor.mode_handler.get_mode()
        
        # Mode indicator with color
        mode_colors = {
            Mode.NORMAL: (curses.color_pair(3), "NORMAL"),
            Mode.INSERT: (curses.color_pair(4), "INSERT"),
            Mode.VISUAL: (curses.color_pair(5), "VISUAL"),
            Mode.COMMAND: (curses.color_pair(1), "COMMAND"),
        }
        
        color, mode_text = mode_colors.get(mode, (curses.color_pair(1), mode.name))
        
        # Status bar content
        left_status = f" {mode_text} "
        if buffer.filename:
            middle_status = f" {buffer.filename}"
            if buffer.modified:
                middle_status += " [+]"
        else:
            middle_status = " [No Name]"
            if buffer.modified:
                middle_status += " [+]"
            
        # Line and column info
        total_lines = len(buffer.lines)
        line_percent = int((buffer.cursor_y + 1) * 100 / total_lines) if total_lines > 0 else 0
        right_status = f" {buffer.cursor_y + 1},{buffer.cursor_x + 1} | {line_percent}% "
        
        # Draw status bar
        status_y = self.height - 2
        try:
            # Clear status bar line
            self.screen.addstr(status_y, 0, " " * self.width, curses.color_pair(1))
            # Add status components
            self.screen.addstr(status_y, 0, left_status, color | curses.A_BOLD)
            self.screen.addstr(status_y, len(left_status), middle_status, curses.color_pair(1))
            self.screen.addstr(status_y, self.width - len(right_status), right_status, curses.color_pair(1))
        except curses.error:
            pass
        
    def show_command_line(self, prompt: str = ":"):
        """Show command line for user input."""
        command_y = self.height - 1
        try:
            self.screen.move(command_y, 0)
            self.screen.clrtoeol()
            self.screen.addstr(command_y, 0, prompt)
            self.screen.refresh()
            
            # Get user input with basic editing support
            curses.echo()
            command = self.screen.getstr(command_y, len(prompt), self.width - len(prompt) - 1).decode('utf-8')
            curses.noecho()
        except:
            command = ""
        
        return command
        
    def show_message(self, message: str, temporary: bool = True):
        """Display a message in the command line area."""
        message_y = self.height - 1
        try:
            self.screen.move(message_y, 0)
            self.screen.clrtoeol()
            
            # Truncate message if too long
            if len(message) > self.width - 1:
                message = message[:self.width - 4] + "..."
                
            self.screen.addstr(message_y, 0, message)
            
            if not temporary:
                self.screen.refresh()
        except curses.error:
            pass