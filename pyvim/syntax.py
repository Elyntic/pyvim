"""Basic syntax highlighting."""

import re
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


class TokenType(Enum):
    """Token types for syntax highlighting."""
    KEYWORD = auto()
    STRING = auto()
    COMMENT = auto()
    NUMBER = auto()
    FUNCTION = auto()
    CLASS = auto()
    OPERATOR = auto()
    IDENTIFIER = auto()
    NORMAL = auto()


@dataclass
class Token:
    """Represents a syntax token."""
    type: TokenType
    start: int
    end: int
    text: str


class SyntaxHighlighter:
    """Basic syntax highlighter for multiple languages."""
    
    LANGUAGES = {
        '.py': 'python',
        '.js': 'javascript',
        '.html': 'html',
        '.css': 'css',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.sh': 'bash',
        '.yml': 'yaml',
        '.yaml': 'yaml',
        '.json': 'json',
    }
    
    def __init__(self):
        self.language = None
        self.tokens_cache: Dict[int, List[Token]] = {}
        
    def detect_language(self, filename: str) -> Optional[str]:
        """Detect language from filename."""
        if not filename:
            return None
            
        for ext, lang in self.LANGUAGES.items():
            if filename.endswith(ext):
                self.language = lang
                return lang
                
        # Check shebang
        return None
        
    def tokenize_line(self, line: str, line_num: int) -> List[Token]:
        """Tokenize a single line."""
        if line_num in self.tokens_cache:
            return self.tokens_cache[line_num]
            
        tokens = []
        
        if self.language == 'python':
            tokens = self._tokenize_python(line)
        elif self.language == 'javascript':
            tokens = self._tokenize_javascript(line)
        elif self.language == 'html':
            tokens = self._tokenize_html(line)
        else:
            # Default tokenization
            tokens = [Token(TokenType.NORMAL, 0, len(line), line)]
            
        self.tokens_cache[line_num] = tokens
        return tokens
        
    def _tokenize_python(self, line: str) -> List[Token]:
        """Tokenize Python code."""
        tokens = []
        
        # Python keywords
        keywords = {
            'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue',
            'def', 'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
            'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'None',
            'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'True', 'try',
            'while', 'with', 'yield'
        }
        
        patterns = [
            (r'#.*$', TokenType.COMMENT),
            (r'""".*?"""', TokenType.STRING),
            (r"'''.*?'''", TokenType.STRING),
            (r'"[^"\```*(\\.[^"\```*)*"', TokenType.STRING),
            (r"'[^'\```*(\\.[^'\```*)*'", TokenType.STRING),
            (r'\b\d+\.?\d*([eE][+-]?\d+)?\b', TokenType.NUMBER),
            (r'\bdef\s+(\w+)', TokenType.FUNCTION),
            (r'\bclass\s+(\w+)', TokenType.CLASS),
            (r'\b(' + '|'.join(keywords) + r')\b', TokenType.KEYWORD),
            (r'[+\-*/%=<>!&|^~]+', TokenType.OPERATOR),
        ]
        
        return self._apply_patterns(line, patterns)
        
    def _tokenize_javascript(self, line: str) -> List[Token]:
        """Tokenize JavaScript code."""
        keywords = {
            'async', 'await', 'break', 'case', 'catch', 'class', 'const', 'continue',
            'debugger', 'default', 'delete', 'do', 'else', 'export', 'extends',
            'finally', 'for', 'function', 'if', 'import', 'in', 'instanceof', 'let',
            'new', 'return', 'super', 'switch', 'this', 'throw', 'try', 'typeof',
            'var', 'void', 'while', 'with', 'yield'
        }
        
        patterns = [
            (r'//.*$', TokenType.COMMENT),
            (r'/\*.*?\*/', TokenType.COMMENT),
            (r'"[^"\```*(\\.[^"\```*)*"', TokenType.STRING),
            (r"'[^'\```*(\\.[^'\```*)*'", TokenType.STRING),
            (r'`[^`]*`', TokenType.STRING),
            (r'\b\d+\.?\d*([eE][+-]?\d+)?\b', TokenType.NUMBER),
            (r'\bfunction\s+(\w+)', TokenType.FUNCTION),
            (r'\bclass\s+(\w+)', TokenType.CLASS),
            (r'\b(' + '|'.join(keywords) + r')\b', TokenType.KEYWORD),
            (r'[+\-*/%=<>!&|^~]+', TokenType.OPERATOR),
        ]
        
        return self._apply_patterns(line, patterns)
        
    def _tokenize_html(self, line: str) -> List[Token]:
        """Tokenize HTML code."""
        patterns = [
            (r'<!--.*?-->', TokenType.COMMENT),
            (r'</?[a-zA-Z][^>]*>', TokenType.KEYWORD),
            (r'"[^"]*"', TokenType.STRING),
            (r"'[^']*'", TokenType.STRING),
        ]
        
        return self._apply_patterns(line, patterns)
        
    def _apply_patterns(self, line: str, patterns: List[Tuple[str, TokenType]]) -> List[Token]:
        """Apply regex patterns to tokenize line."""
        tokens = []
        covered = set()
        
        for pattern, token_type in patterns:
            for match in re.finditer(pattern, line):
                start, end = match.span()
                
                # Check if this range is already covered
                if not any(start <= i < end for i in covered):
                    tokens.append(Token(token_type, start, end, match.group()))
                    covered.update(range(start, end))
                    
        # Fill gaps with normal tokens
        tokens.sort(key=lambda t: t.start)
        result = []
        pos = 0
        
        for token in tokens:
            if pos < token.start:
                result.append(Token(TokenType.NORMAL, pos, token.start, line[pos:token.start]))
            result.append(token)
            pos = token.end
            
        if pos < len(line):
            result.append(Token(TokenType.NORMAL, pos, len(line), line[pos:]))
            
        return result
        
    def clear_cache(self):
        """Clear the tokens cache."""
        self.tokens_cache.clear()