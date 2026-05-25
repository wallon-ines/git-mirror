"""Git command wrapper for executing git operations.

Corresponds to: src/git.rs
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional, List

from .errors import GitCommandError, GitCommandTimeout, GitError

logger = logging.getLogger(__name__)


class GitWrapper:
    """Wrapper around git command execution."""
    
    def __init__(
        self,
        executable: str = "git",
        lfs_enabled: bool = False,
        timeout: Optional[float] = None,
    ):
        """Initialize the git wrapper.
        
        Args:
            executable: Path to git executable to use.
            lfs_enabled: Whether git LFS is enabled.
            timeout: Timeout in seconds for git operations.
        """
        self.executable = executable
        self.lfs_enabled = lfs_enabled
        self.timeout = timeout
    
    def _run_cmd(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
    ) -> None:
        """Execute a command and handle errors.
        
        Args:
            cmd: Command and arguments to execute.
            cwd: Working directory for the command.
            
        Raises:
            GitCommandError: If command fails.
            GitCommandTimeout: If command times out.
        """
        cmd_str = " ".join(str(c) for c in cmd)
        logger.debug(f"Running: {cmd_str}")
        
        env = {**subprocess.os.environ, "GIT_TERMINAL_PROMPT": "0"}
        
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )
            
            if result.stdout and result.stdout.strip():
                logger.debug(f"Stdout: {result.stdout}")
            if result.stderr and result.stderr.strip():
                logger.debug(f"Stderr: {result.stderr}")
            
            if result.returncode != 0:
                raise GitCommandError(cmd_str, result.returncode, result.stderr)
                
        except subprocess.TimeoutExpired:
            raise GitCommandTimeout(cmd_str, self.timeout or 0)
    
    def git_version(self) -> None:
        """Check git version and availability."""
        cmd = [self.executable, "--version"]
        self._run_cmd(cmd)
    
    def git_lfs_version(self) -> None:
        """Check git-lfs version and availability."""
        cmd = [self.executable, "lfs", "version"]
        self._run_cmd(cmd)
    
    def git_clone_mirror(self, origin: str, repo_dir: Path, lfs: bool) -> None:
        """Clone a repository as a mirror.
        
        Args:
            origin: URL of the repository to clone from.
            repo_dir: Directory where to store the clone.
            lfs: Whether to fetch LFS objects.
        """
        logger.info(f"Local Checkout for {origin}")
        
        cmd = [self.executable, "clone", "--mirror", origin, str(repo_dir)]
        self._run_cmd(cmd)
        
        if self.lfs_enabled and lfs:
            self._git_lfs_fetch(repo_dir)
    
    def git_update_mirror(self, origin: str, repo_dir: Path, lfs: bool) -> None:
        """Update an existing mirror repository.
        
        Args:
            origin: URL of the repository to update from.
            repo_dir: Directory of the existing clone.
            lfs: Whether to fetch LFS objects.
        """
        logger.info(f"Local Update for {origin}")
        
        cmd = [self.executable, "remote", "set-url", "origin", origin]
        self._run_cmd(cmd, cwd=repo_dir)
        
        cmd = [self.executable, "remote", "update", "--prune"]
        self._run_cmd(cmd, cwd=repo_dir)
        
        if self.lfs_enabled and lfs:
            self._git_lfs_fetch(repo_dir)
    
    def git_push_mirror(
        self,
        destination: str,
        repo_dir: Path,
        refspec: Optional[List[str]],
        lfs: bool,
    ) -> None:
        """Push a mirror repository to destination.
        
        Args:
            destination: Destination URL to push to.
            repo_dir: Directory of the repository to push.
            refspec: Optional list of refspecs to push.
            lfs: Whether to push LFS objects.
        """
        logger.info(f"Push to destination {destination}")
        
        if self.lfs_enabled and lfs:
            cmd = [self.executable, "lfs", "install"]
            self._run_cmd(cmd, cwd=repo_dir)
        
        cmd = [
            self.executable, "-c", f"lfs.url={destination}",
            "push", "-f"
        ]
        
        if refspec:
            cmd.append(destination)
            cmd.extend(refspec)
        else:
            cmd.extend(["--mirror", destination])
        
        self._run_cmd(cmd, cwd=repo_dir)
    
    def _git_lfs_fetch(self, repo_dir: Path) -> None:
        """Fetch LFS objects in a repository."""
        cmd = [self.executable, "lfs", "fetch"]
        self._run_cmd(cmd, cwd=repo_dir)
