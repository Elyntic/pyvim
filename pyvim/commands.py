"""Command mode implementation."""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .editor import Editor


class CommandProcessor:
    """Processes command mode commands."""
    
    def __init__(self, editor: 'Editor'):
        self.editor = editor
        self.commands = {
            'w': self.save_file,
            'write': self.save_file,
            'q': self.quit,
            'quit': self.quit,
            'q!': self.force_quit,
            'wq': self.save_and_quit,
            'x': self.save_and_quit,
        }
        
    def execute(self, command: str) -> Optional[str]:
        """Execute a command and return result message."""
        if not command:
            return None
            
        # Parse command and arguments
        parts = command.split()
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Check for line number
        if cmd.isdigit():
            self.editor.buffer.goto_line(int(cmd))
            return None
            
        # Execute command
        if cmd in self.commands:
            return self.commands[cmd](args)
        else:
            return f"Unknown command: {cmd}"
            
    def save_file(self, args=None) -> str:
        """Save the current file."""
        filename = args[0] if args else None
        try:
            self.editor.buffer.save_file(filename)
            return f"Saved: {self.editor.buffer.filename}"
        except Exception as e:
            return str(e)
            
    def quit(self, args=None) -> str:
        """Quit the editor."""
        if self.editor.buffer.modified:
            return "No write since last change (add ! to override)"
        self.editor.running = False
        return None
        
    def force_quit(self, args=None) -> str:
        """Force quit without saving."""
        self.editor.running = False
        return None
        
    def save_and_quit(self, args=None) -> str:
        """Save and quit."""
        result = self.save_file(args)
        if result and not result.startswith("Error"):
            self.editor.running = False
        return result