#!/usr/bin/env python3
"""
Transcript Logger
Saves transcription sessions to log files with timestamps
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class TranscriptLogger:
    """Manages saving transcripts to log files."""

    def __init__(self, log_dir: str = None):
        """
        Initialize transcript logger.

        Args:
            log_dir: Directory to save log files (default: ../log_output relative to this file)
        """
        if log_dir is None:
            log_dir = Path(__file__).parent.parent / "log_output"

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True, parents=True)

        self.current_session_file = None
        self.session_start_time = None

    def start_session(self) -> str:
        """
        Start a new logging session and create a new log file.

        Returns:
            Path to the created log file
        """
        self.session_start_time = datetime.now()
        timestamp = self.session_start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"transcript_{timestamp}.txt"
        self.current_session_file = self.log_dir / filename

        # Create file with header
        with open(self.current_session_file, 'w', encoding='utf-8') as f:
            f.write(f"Whispering Transcript Log\n")
            f.write(f"{'=' * 50}\n")
            f.write(f"Session started: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'=' * 50}\n\n")

        return str(self.current_session_file)

    def log_text(self, text: str, source: str = "transcription"):
        """
        Append text to the current session log.

        Args:
            text: Text to log
            source: Source of the text ('transcription', 'translation', 'ai_processed')
        """
        if not self.current_session_file:
            return

        if not text or not text.strip():
            return

        with open(self.current_session_file, 'a', encoding='utf-8') as f:
            # Add timestamp for each entry
            timestamp = datetime.now().strftime("%H:%M:%S")
            f.write(f"[{timestamp}] {text}")
            # Only add newline if text doesn't end with one
            if not text.endswith('\n'):
                f.write('\n')

    def end_session(self):
        """End the current logging session and add footer."""
        if not self.current_session_file:
            return

        end_time = datetime.now()
        duration = end_time - self.session_start_time

        with open(self.current_session_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'=' * 50}\n")
            f.write(f"Session ended: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duration: {duration}\n")
            f.write(f"{'=' * 50}\n")

        saved_file = self.current_session_file
        self.current_session_file = None
        self.session_start_time = None

        return str(saved_file)

    def get_current_file(self) -> Optional[str]:
        """Get the path of the current session file."""
        return str(self.current_session_file) if self.current_session_file else None

    def list_logs(self, limit: int = 10) -> list:
        """
        List recent log files.

        Args:
            limit: Maximum number of files to return

        Returns:
            List of tuples (filename, timestamp, size_bytes)
        """
        log_files = []

        for file_path in sorted(self.log_dir.glob("transcript_*.txt"), reverse=True):
            if limit and len(log_files) >= limit:
                break

            stat = file_path.stat()
            log_files.append((
                file_path.name,
                datetime.fromtimestamp(stat.st_mtime),
                stat.st_size
            ))

        return log_files

    def format_log_list(self, limit: int = 10) -> str:
        """
        Get a formatted string of recent log files.

        Args:
            limit: Maximum number of files to return

        Returns:
            Formatted string listing log files
        """
        logs = self.list_logs(limit)

        if not logs:
            return "No log files found."

        lines = ["Recent log files:", ""]
        for filename, timestamp, size in logs:
            size_kb = size / 1024
            lines.append(f"  {filename:30s} | {timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {size_kb:6.1f} KB")

        return "\n".join(lines)


# Convenience function
def create_logger(log_dir: str = None) -> TranscriptLogger:
    """
    Create a transcript logger instance.

    Args:
        log_dir: Directory to save log files (default: ../log_output relative to this file)

    Returns:
        TranscriptLogger instance
    """
    return TranscriptLogger(log_dir)


if __name__ == "__main__":
    """Test the logger."""
    print("Testing Transcript Logger...\n")

    logger = create_logger()
    print(f"Log directory: {logger.log_dir}\n")

    # Test session
    print("Starting test session...")
    log_file = logger.start_session()
    print(f"Created log file: {log_file}")

    logger.log_text("This is a test transcription.")
    logger.log_text("This is another line of text.")
    logger.log_text("And a final line with a paragraph break.\n\n")

    saved = logger.end_session()
    print(f"Session saved to: {saved}\n")

    # List logs
    print(logger.format_log_list())
