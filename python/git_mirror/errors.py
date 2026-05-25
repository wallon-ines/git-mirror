"""Error handling for git-mirror.

Corresponds to: src/error.rs
"""


class GitMirrorError(Exception):
    """Base exception for git-mirror operations."""
    pass


class GenericError(GitMirrorError):
    """A generic error occurred during mirroring."""
    def __init__(self, message: str):
        self.message = message
        self.exit_code = 2
        super().__init__(f"Generic Mirror error: {message}")


class GitError(GitMirrorError):
    """Error during git command execution."""
    def __init__(self, message: str):
        self.message = message
        self.exit_code = 3
        super().__init__(f"Git command execution failed: {message}")


class MirrorExtractionError(GitMirrorError):
    """Error extracting mirror configuration."""
    def __init__(self, message: str):
        self.message = message
        self.exit_code = 4
        super().__init__(f"Mirror extraction failed: {message}")


class SyncError(GitMirrorError):
    """Error when syncing tasks fail."""
    def __init__(self, count: int):
        self.count = count
        self.exit_code = 1
        super().__init__(f"{count} sync tasks failed")


class GitCommandError(GitError):
    """Git command failed with an exit code."""
    def __init__(self, cmd: str, code: int, stderr: str):
        self.cmd = cmd
        self.code = code
        self.stderr = stderr
        super().__init__(f"Command {cmd} failed with exit code: {code}, Stderr: {stderr}")


class GitCommandTimeout(GitError):
    """Git command exceeded timeout."""
    def __init__(self, cmd: str, timeout: float):
        self.cmd = cmd
        self.timeout = timeout
        super().__init__(f"Command {cmd} timed out after {timeout}s")
