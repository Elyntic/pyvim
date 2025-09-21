#!/usr/bin/env python3
"""Main entry point for PyVim editor."""

import sys
import argparse
from .editor import Editor


def main():
    """Main function to run the editor."""
    parser = argparse.ArgumentParser(description="PyVim - A Vim-like text editor")
    parser.add_argument("filename", nargs="?", help="File to edit")
    parser.add_argument("--version", action="version", version="PyVim v0.0.1a")
    
    args = parser.parse_args()
    
    try:
        editor = Editor()
        editor.run(args.filename)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()