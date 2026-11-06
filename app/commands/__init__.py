"""Command-file input layer for the PS-061 pharmacy backend."""

from app.commands.command_processor import CommandProcessor, build_default_handlers

__all__ = ["CommandProcessor", "build_default_handlers"]
