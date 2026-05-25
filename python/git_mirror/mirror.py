"""Core mirroring logic.

Corresponds to: src/lib.rs
"""

import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Union
from datetime import datetime
import time
from threading import Lock

from .config import MirrorOptions
from .errors import GitMirrorError, GenericError
from .git_wrapper import GitWrapper
from .provider import Provider, Mirror, MirrorError

logger = logging.getLogger(__name__)

# Simple metrics storage (in-memory for now)
metrics = {
    "total": 0,
    "success": 0,
    "failed": 0,
    "skipped": 0,
    "timeout": 0,
}
metrics_lock = Lock()


def _slugify_path(url: str) -> str:
    """Convert a URL to a filesystem-safe directory name.
    
    Corresponds to Rust's slug::slugify function.
    
    Args:
        url: URL to slugify
        
    Returns:
        Slugified string safe for filesystem
    """
    import re
    # Remove common prefixes
    slug = url.replace("https://", "").replace("http://", "").replace("git@", "")
    # Replace non-alphanumeric characters with hyphens
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug.lower()


def mirror_repo(
    origin: str,
    destination: str,
    refspec: List[str],
    lfs: bool,
    opts: MirrorOptions,
) -> None:
    """Mirror a single repository.
    
    Corresponds to Rust's mirror_repo function in src/lib.rs
    
    Args:
        origin: Source repository URL
        destination: Destination repository URL
        refspec: Optional list of refspecs to push
        lfs: Whether to mirror LFS objects
        opts: Mirror options
        
    Raises:
        GitMirrorError: If mirroring fails
    """
    if opts.dry_run:
        logger.info(f"[DRY RUN] Would mirror: {origin} -> {destination}")
        return
    
    # Create local directory name from origin URL
    origin_dir = Path(opts.mirror_dir) / _slugify_path(origin)
    logger.debug(f"Using origin dir: {origin_dir}")
    
    # Create git wrapper
    git = GitWrapper(
        executable=opts.git_executable,
        lfs_enabled=opts.mirror_lfs,
        timeout=opts.git_timeout,
    )
    
    # Check git and git-lfs availability
    git.git_version()
    if opts.mirror_lfs:
        git.git_lfs_version()
    
    # Clone or update
    if origin_dir.is_dir():
        git.git_update_mirror(origin, origin_dir, lfs)
    elif not origin_dir.exists():
        git.git_clone_mirror(origin, origin_dir, lfs)
    else:
        raise GenericError(
            f"Local origin dir is a file: {origin_dir}"
        )
    
    # Push to destination
    git.git_push_mirror(destination, origin_dir, refspec, lfs)
    
    # Remove working repository if requested
    if opts.remove_workrepo:
        import shutil
        try:
            shutil.rmtree(origin_dir)
            logger.info(f"Removed working repository: {origin_dir}")
        except Exception as e:
            raise GenericError(
                f"Unable to delete working repository {origin_dir}: {e}"
            )


def _process_mirror_result(
    index: int,
    total: int,
    result: Union[Mirror, MirrorError],
    opts: MirrorOptions,
    label: str,
) -> dict:
    """Process a single mirror result (success or error).
    
    Corresponds to the processing in Rust's run_sync_task function.
    
    Returns:
        Dictionary with result information
    """
    start_time = time.time()
    
    if isinstance(result, Mirror):
        # Valid mirror job
        name = f"{result.origin} -> {result.destination}"
        print(f"START {index}/{total} [{datetime.now().isoformat()}]: {name}")
        
        try:
            mirror_repo(
                result.origin,
                result.destination,
                result.refspec or [],
                result.lfs,
                opts,
            )
            
            duration = time.time() - start_time
            print(f"END(OK) {index}/{total} [{datetime.now().isoformat()}]: {name}")
            
            with metrics_lock:
                metrics["success"] += 1
            
            return {
                "status": "success",
                "name": name,
                "duration": duration,
            }
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"END(FAIL) {index}/{total} [{datetime.now().isoformat()}]: {name} ({e})")
            logger.error(f"Unable to sync repo {name}: {e}")
            
            with metrics_lock:
                metrics["failed"] += 1
            
            return {
                "status": "failed",
                "name": name,
                "duration": duration,
                "error": str(e),
            }
    
    elif isinstance(result, MirrorError):
        # Skipped or errored repository
        duration = time.time() - start_time
        
        error_msg = str(result)
        print(f"SKIP {index}/{total} [{datetime.now().isoformat()}]: {error_msg}")
        logger.warning(f"Skipping repository: {error_msg}")
        
        with metrics_lock:
            metrics["skipped"] += 1
        
        return {
            "status": "skipped",
            "name": error_msg,
            "duration": duration,
        }
    
    else:
        raise GitMirrorError(f"Unknown result type: {type(result)}")


def run_sync_task(
    mirrors: List[Union[Mirror, MirrorError]],
    label: str,
    opts: MirrorOptions,
) -> dict:
    """Run synchronization tasks for all mirrors.
    
    Corresponds to Rust's run_sync_task function in src/lib.rs
    
    Args:
        mirrors: List of mirrors or errors
        label: Label for logging
        opts: Mirror options
        
    Returns:
        Dictionary with results
    """
    total = len(mirrors)
    results = []
    
    logger.debug(f"Starting sync task for {total} mirrors with {opts.worker_count} workers")
    
    # Reset metrics
    with metrics_lock:
        metrics["total"] = total
        metrics["success"] = 0
        metrics["failed"] = 0
        metrics["skipped"] = 0
        metrics["timeout"] = 0
    
    # Execute mirrors in parallel
    with ThreadPoolExecutor(max_workers=opts.worker_count) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                _process_mirror_result,
                i,
                total,
                mirror,
                opts,
                label,
            ): i for i, mirror in enumerate(mirrors)
        }
        
        # Collect results as they complete
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Unexpected error in mirror task: {e}", exc_info=True)
                with metrics_lock:
                    metrics["failed"] += 1
    
    # Print summary
    success_count = sum(1 for r in results if r["status"] == "success")
    print(f"DONE [{datetime.now().isoformat()}]: {success_count}/{total}")
    
    return {
        "results": results,
        "total": total,
        "success": success_count,
        "failed": metrics["failed"],
        "skipped": metrics["skipped"],
    }


def do_mirror(provider: Provider, opts: MirrorOptions) -> None:
    """Execute the main mirroring operation.
    
    Corresponds to Rust's do_mirror function in src/lib.rs
    
    Args:
        provider: Repository provider (GitLab or GitHub)
        opts: Mirror options
        
    Raises:
        GitMirrorError: If mirroring fails
    """
    logger.debug(f"Starting mirror operation with provider: {provider.get_label()}")
    
    # Create mirror directory
    mirror_dir = Path(opts.mirror_dir)
    logger.debug(f"Creating mirror directory at {mirror_dir}")
    try:
        mirror_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise GenericError(f"Unable to create mirror dir: {mirror_dir} ({e})")
    
    # Create lockfile to prevent concurrent execution
    lockfile_path = mirror_dir / "git-mirror.lock"
    try:
        # Simple file-based locking
        import fcntl
        lockfile = open(lockfile_path, "w")
        try:
            fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            raise GenericError(
                f"Another instance is already running against the same mirror directory: {mirror_dir}"
            )
        logger.debug(f"Acquired lockfile: {lockfile_path}")
    except GenericError:
        raise
    except Exception as e:
        raise GenericError(f"Unable to open lockfile: {lockfile_path} ({e})")
    
    try:
        # Get list of repositories to mirror
        logger.debug("Getting list of repositories from provider...")
        mirrors = provider.get_mirror_repos()
        
        # Run synchronization
        logger.debug(f"Running sync task with {len(mirrors)} mirrors")
        sync_results = run_sync_task(mirrors, provider.get_label(), opts)
        
        # Check for errors
        error_count = sync_results["failed"]
        
        if opts.fail_on_sync_error and error_count > 0:
            raise GitMirrorError(f"{error_count} sync tasks failed")
        
        logger.info("Mirror operation completed successfully")
        
    finally:
        # Release lockfile
        try:
            import fcntl
            fcntl.flock(lockfile.fileno(), fcntl.LOCK_UN)
            lockfile.close()
        except Exception as e:
            logger.warning(f"Failed to release lockfile: {e}")
