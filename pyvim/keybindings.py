"""Key bindings and input handling."""

import curses
import curses.ascii
from typing import Dict, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .editor import Editor


class KeyBindings:
    """Manages key bindings for different modes."""
    
    def __init__(self, editor: 'Editor'):
        self.editor = editor
        self.normal_bindings: Dict[int, Callable] = {}
        self.insert_bindings: Dict[int, Callable] = {}
        self.command_bindings: Dict[int, Callable] = {}
        
        self._init_normal_bindings()
        self._init_insert_bindings()
        
    def _init_normal_bindings(self):
        """Initialize normal mode key bindings."""
        # Movement
        self.normal_bindings[ord('h')] = lambda: self.editor.buffer.move_cursor(dx=-1)
        self.normal_bindings[ord('j')] = lambda: self.editor.buffer.move_cursor(dy=1)
        self.normal_bindings[ord('k')] = lambda: self.editor.buffer.move_cursor(dy=-1)
        self.normal_bindings[ord('l')] = lambda: self.editor.buffer.move_cursor(dx=1)
        
        # Arrow keys
        self.normal_bindings[curses.KEY_LEFT] = lambda: self.editor.buffer.move_cursor(dx=-1)
        self.normal_bindings[curses.KEY_DOWN] = lambda: self.editor.buffer.move_cursor(dy=1)
        self.normal_bindings[curses.KEY_UP] = lambda: self.editor.buffer.move_cursor(dy=-1)
        self.normal_bindings[curses.KEY_RIGHT] = lambda: self.editor.buffer.move_cursor(dx=1)
        
        # Mode changes
        self.normal_bindings[ord('i')] = lambda: self.editor.enter_insert_mode()
        self.normal_bindings[ord('a')] = lambda: self.editor.enter_insert_mode(append=True)
        self.normal_bindings[ord('o')] = lambda: self.editor.open_line_below()
        self.normal_bindings[ord('O')] = lambda: self.editor.open_line_above()
        self.normal_bindings[ord('A')] = lambda: self.editor.append_at_line_end()
        self.normal_bindings[ord('I')] = lambda: self.editor.insert_at_line_start()
        
        # Editing in normal mode
        self.normal_bindings[ord('x')] = lambda: self.editor.delete_char_under_cursor()
        self.normal_bindings[ord('X')] = lambda: self.editor.backspace_in_normal_mode()
        self.normal_bindings[curses.KEY_DC] = lambda: self.editor.delete_char_under_cursor()  # Delete key
        
        # Command mode
        self.normal_bindings[ord(':')] = lambda: self.editor.enter_command_mode()
        
        # Navigation
        self.normal_bindings[ord('0')] = lambda: self.editor.goto_line_start()
        self.normal_bindings[ord('$')] = lambda: self.editor.goto_line_end()
        self.normal_bindings[ord('g')] = self.editor.handle_g_command
        self.normal_bindings[ord('G')] = lambda: self.editor.goto_last_line()
        
        # Word navigation
        self.normal_bindings[ord('w')] = lambda: self.editor.next_word()
        self.normal_bindings[ord('b')] = lambda: self.editor.prev_word()
        
        # Line operations
        self.normal_bindings[ord('d')] = self.editor.handle_d_command
        self.normal_bindings[ord('y')] = self.editor.handle_y_command
        self.normal_bindings[ord('p')] = lambda: self.editor.paste_after()
        self.normal_bindings[ord('P')] = lambda: self.editor.paste_before()
        
    def _init_insert_bindings(self):
        """Initialize insert mode key bindings."""
        # Exit insert mode
        self.insert_bindings[27] = lambda: self.editor.exit_insert_mode()  # ESC
        self.insert_bindings[curses.ascii.ESC] = lambda: self.editor.exit_insert_mode()
        
        # Backspace handling - multiple key codes for compatibility
        self.insert_bindings[curses.KEY_BACKSPACE] = lambda: self.editor.handle_backspace()
        self.insert_bindings[127] = lambda: self.editor.handle_backspace()  # ASCII DEL (common backspace)
        self.insert_bindings[8] = lambda: self.editor.handle_backspace()    # ASCII BS (Ctrl+H)
        self.insert_bindings[curses.ascii.BS] = lambda: self.editor.handle_backspace()
        
        # Delete key
        self.insert_bindings[curses.KEY_DC] = lambda: self.editor.buffer.delete_forward()
        
        # Enter/Return
        self.insert_bindings[10] = lambda: self.editor.handle_enter()  # LF (Line Feed)
        self.insert_bindings[13] = lambda: self.editor.handle_enter()  # CR (Carriage Return)
        self.insert_bindings[curses.KEY_ENTER] = lambda: self.editor.handle_enter()
        
        # Tab
        self.insert_bindings[9] = lambda: self.editor.handle_tab()  # TAB
        self.insert_bindings[curses.ascii.TAB] = lambda: self.editor.handle_tab()
        
        # Arrow keys in insert mode
        self.insert_bindings[curses.KEY_LEFT] = lambda: self.editor.buffer.move_cursor(dx=-1)
        self.insert_bindings[curses.KEY_RIGHT] = lambda: self.editor.buffer.move_cursor(dx=1)
        self.insert_bindings[curses.KEY_UP] = lambda: self.editor.buffer.move_cursor(dy=-1)
        self.insert_bindings[curses.KEY_DOWN] = lambda: self.editor.buffer.move_cursor(dy=1)
        
        # Page navigation
        self.insert_bindings[curses.KEY_PPAGE] = lambda: self.editor.page_up()
        self.insert_bindings[curses.KEY_NPAGE] = lambda: self.editor.page_down()
        
        # Home/End keys
        self.insert_bindings[curses.KEY_HOME] = lambda: self.editor.goto_line_start()
        self.insert_bindings[curses.KEY_END] = lambda: self.editor.goto_line_end()
        
    def handle_key(self, key: int) -> bool:
        """Handle key press based on current mode."""
        from .modes import Mode
        
        mode = self.editor.mode_handler.get_mode()
        
        if mode == Mode.NORMAL:
            if key in self.normal_bindings:
                self.normal_bindings[key]()
                return True
                
        elif mode == Mode.INSERT:
            if key in self.insert_bindings:
                self.insert_bindings[key]()
                return True
            else:
                # Regular character input
                if 32 <= key <= 126:  # Printable ASCII
                    self.editor.buffer.insert_char(chr(key))
                    return True
                # Extended ASCII or Unicode
                elif key > 126 and key < 256:
                    try:
                        self.editor.buffer.insert_char(chr(key))
                        return True
                    except:
                        pass
                        
        return False