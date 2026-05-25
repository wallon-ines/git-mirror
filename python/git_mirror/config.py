"""Configuration and options for git-mirror.

Corresponds to: src/lib.rs MirrorOptions struct
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List


@dataclass
class MirrorOptions:
    """Configuration options for mirror operations."""
    
    mirror_dir: Path
    """Directory where local repository clones are stored."""
    
    dry_run: bool = False
    """Only print what would be done without actually running git commands."""
    
    metrics_file: Optional[Path] = None
    """Path to store Prometheus metrics."""
    
    junit_file: Optional[Path] = None
    """Path to store JUnit XML report."""
    
    worker_count: int = 1
    """Number of concurrent mirror jobs."""
    
    git_executable: str = "git"
    """Path to git executable to use."""
    
    refspec: Optional[List[str]] = None
    """Default refspec for pushing (can be overridden per project)."""
    
    remove_workrepo: bool = False
    """Remove local working repository after pushing."""
    
    fail_on_sync_error: bool = False
    """Exit with error code if any sync task fails."""
    
    mirror_lfs: bool = False
    """Mirror git LFS objects as well."""
    
    git_timeout: Optional[float] = None
    """Timeout in seconds for individual git operations."""
