"""
CLI styling utilities with graceful degradation

Provides colored output that automatically falls back to plain text
when the terminal doesn't support ANSI colors.
"""

import click
from typing import Optional


class Style:
    """Style constants for CLI output"""
    
    # Colors
    PRIMARY = 'cyan'
    SUCCESS = 'green'
    WARNING = 'yellow'
    ERROR = 'red'
    MUTED = 'bright_black'
    
    # Semantic styles
    COMMAND = 'cyan'
    OPTION = 'yellow'
    ARGUMENT = 'green'
    HEADER = 'bright_white'
    EXAMPLE = 'bright_black'


def styled(text: str, fg: Optional[str] = None, bold: bool = False) -> str:
    """
    Apply style to text with automatic fallback.
    
    Args:
        text: Text to style
        fg: Foreground color
        bold: Whether to make text bold
    
    Returns:
        Styled text (or plain text if colors not supported)
    """
    return click.style(text, fg=fg, bold=bold)


def header(text: str) -> str:
    """Style text as a header"""
    return styled(text, fg=Style.HEADER, bold=True)


def command(text: str) -> str:
    """Style text as a command"""
    return styled(text, fg=Style.COMMAND)


def success(text: str) -> str:
    """Style text as success"""
    return styled(text, fg=Style.SUCCESS)


def warning(text: str) -> str:
    """Style text as warning"""
    return styled(text, fg=Style.WARNING)


def error(text: str) -> str:
    """Style text as error"""
    return styled(text, fg=Style.ERROR)


def muted(text: str) -> str:
    """Style text as muted/secondary"""
    return styled(text, fg=Style.MUTED)


def example(text: str) -> str:
    """Style text as an example command"""
    return styled(text, fg=Style.EXAMPLE)


class HelpFormatter(click.HelpFormatter):
    """Custom help formatter with color support"""
    
    def write_usage(self, prog: str, args: str = '', prefix: Optional[str] = None) -> None:
        """Write styled usage line"""
        if prefix is None:
            prefix = 'Usage: '
        
        usage_prefix = styled(prefix, fg=Style.HEADER, bold=True)
        prog_styled = styled(prog, fg=Style.COMMAND)
        
        self.write(f'{usage_prefix}{prog_styled} {args}\n\n')
    
    def write_heading(self, heading: str) -> None:
        """Write styled heading"""
        self.write(f'{styled(heading, fg=Style.HEADER, bold=True)}:\n')
    
    def write_dl(self, rows, col_max: int = 30, col_spacing: int = 2) -> None:
        """Write a definition list with styled terms"""
        rows = list(rows)
        widths = [max(len(row[0]) for row in rows) if rows else 0]
        
        if widths[0] > col_max:
            widths[0] = col_max
        
        for first, second in rows:
            self.write(f'  {styled(first, fg=Style.COMMAND):{widths[0]}}')
            if second:
                self.write(' ' * col_spacing)
                self.write(second)
            self.write('\n')


class StyledGroup(click.Group):
    """Click Group with styled help output"""
    
    def format_help(self, ctx, formatter):
        """Format help with custom styling"""
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_commands(ctx, formatter)
    
    def format_commands(self, ctx, formatter):
        """Write styled commands section"""
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None or cmd.hidden:
                continue
            
            help_text = cmd.get_short_help_str(limit=formatter.width)
            commands.append((subcommand, help_text))
        
        if commands:
            with formatter.section(styled('Commands', fg=Style.HEADER, bold=True)):
                formatter.write_dl(commands)
    
    def make_context(self, info_name, args, parent=None, **extra):
        """Create context with custom formatter"""
        ctx = super().make_context(info_name, args, parent, **extra)
        ctx.formatter_class = HelpFormatter
        return ctx
