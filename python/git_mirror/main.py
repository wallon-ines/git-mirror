"""Main entry point for git-mirror CLI.

Corresponds to: src/main.rs
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .config import MirrorOptions
from .errors import GitMirrorError
from .provider import GitLab, GitHub, Provider
from .mirror import do_mirror


def setup_logging(verbosity: int) -> None:
    """Setup logging based on verbosity level.
    
    Corresponds to Rust's env_logger setup.
    
    Args:
        verbosity: Verbosity level (0-4, higher = more verbose)
    """
    # Map verbosity to log levels
    # Rust: 0=error, 1=warn, 2=info, 3=debug, 4+=trace
    log_levels = {
        0: logging.ERROR,
        1: logging.WARNING,
        2: logging.INFO,
        3: logging.DEBUG,
        4: logging.DEBUG,  # Python doesn't have TRACE, use DEBUG
    }
    
    # Cap verbosity at 4
    level_index = min(verbosity, 4)
    level = log_levels[level_index]
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Corresponds to Rust's clap parser in src/main.rs
    """
    parser = argparse.ArgumentParser(
        prog="git-mirror",
        description="Sync between different git repositories",
    )
    
    # Provider selection
    parser.add_argument(
        "-p", "--provider",
        choices=["GitLab", "GitHub"],
        default="GitLab",
        help="Provider to use for fetching repositories (default: GitLab)",
    )
    
    # Instance URL
    parser.add_argument(
        "-u", "--url",
        type=str,
        default=None,  # Will be set based on provider
        help="URL of the instance to get repositories from",
    )
    
    # Group/Organization name (required)
    parser.add_argument(
        "-g", "--group",
        type=str,
        required=True,
        help="Name of the group/organization to check for repositories to sync",
    )
    
    # Mirror directory
    parser.add_argument(
        "-m", "--mirror-dir",
        type=Path,
        default=Path("./mirror-dir"),
        help="Directory where the local clones are stored (default: ./mirror-dir)",
    )
    
    # Verbosity
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity level (can be used multiple times: -v, -vv, -vvv, -vvvv)",
    )
    
    # HTTP instead of SSH
    parser.add_argument(
        "--http",
        action="store_true",
        help="Use HTTP(S) instead of SSH to sync repositories",
    )
    
    # Dry run
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be done without actually running any git commands",
    )
    
    # Concurrent workers
    parser.add_argument(
        "-c", "--worker-count",
        type=int,
        default=1,
        help="Number of concurrent mirror jobs (default: 1)",
    )
    
    # Metrics file
    parser.add_argument(
        "--metric-file",
        type=Path,
        default=None,
        help="Location where to store metrics for consumption by Prometheus",
    )
    
    # JUnit report
    parser.add_argument(
        "--junit-report",
        type=Path,
        default=None,
        help="Location where to store the JUnit XML report",
    )
    
    # Git executable
    parser.add_argument(
        "--git-executable",
        type=str,
        default="git",
        help="Git executable to use (default: git)",
    )
    
    # Private token (can come from PRIVATE_TOKEN env var)
    parser.add_argument(
        "--private-token",
        type=str,
        default=None,
        help="Private/Personal access token to access the GitLab or GitHub API. "
             "Can also be set via PRIVATE_TOKEN environment variable.",
    )
    
    # Refspec
    parser.add_argument(
        "--refspec",
        type=str,
        action="append",
        default=None,
        help="Default refspec used to mirror repositories, can be overridden per project. "
             "Can be used multiple times.",
    )
    
    # Remove working repository
    parser.add_argument(
        "--remove-workrepo",
        action="store_true",
        help="Remove the local working repository after pushing. "
             "This requires a full re-clone on the next run.",
    )
    
    # Fail on sync error
    parser.add_argument(
        "--fail-on-sync-error",
        action="store_true",
        help="Exit with error code if any sync task fails",
    )
    
    # Mirror LFS
    parser.add_argument(
        "--lfs",
        action="store_true",
        help="Mirror git LFS objects as well",
    )
    
    # Git timeout
    parser.add_argument(
        "--git-timeout",
        type=float,
        default=None,
        help="Timeout in seconds for individual git operations",
    )
    
    return parser.parse_args()


def create_provider(args: argparse.Namespace) -> Provider:
    """Create the appropriate provider based on arguments.
    
    Corresponds to Rust's provider instantiation in src/main.rs
    """
    # Determine default URL based on provider
    if args.url is None:
        if args.provider == "GitLab":
            args.url = "https://gitlab.com"
        elif args.provider == "GitHub":
            args.url = "https://api.github.com"
    
    if args.provider == "GitLab":
        return GitLab(
            url=args.url,
            group=args.group,
            use_http=args.http,
            private_token=args.private_token,
            recursive=True,
        )
    elif args.provider == "GitHub":
        return GitHub(
            url=args.url,
            org=args.group,
            use_http=args.http,
            private_token=args.private_token,
            useragent=f"git-mirror/0.14.16",
        )
    else:
        raise ValueError(f"Unknown provider: {args.provider}")


def main() -> int:
    """Main entry point for the git-mirror CLI.
    
    Corresponds to Rust's main() function in src/main.rs
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Parse command-line arguments
        args = parse_arguments()
        
        # Setup logging
        setup_logging(args.verbose)
        logger = logging.getLogger(__name__)
        
        logger.debug(f"Arguments: {args}")
        
        # Get private token from environment if not provided as argument
        private_token = args.private_token
        if private_token is None:
            import os
            private_token = os.environ.get("PRIVATE_TOKEN")
        
        # Create provider
        provider = create_provider(args)
        if private_token:
            # Update provider's token if it came from env
            provider.private_token = private_token
        
        # Create mirror options
        mirror_opts = MirrorOptions(
            mirror_dir=args.mirror_dir,
            dry_run=args.dry_run,
            metrics_file=args.metric_file,
            junit_file=args.junit_report,
            worker_count=args.worker_count,
            git_executable=args.git_executable,
            refspec=args.refspec,
            remove_workrepo=args.remove_workrepo,
            fail_on_sync_error=args.fail_on_sync_error,
            mirror_lfs=args.lfs,
            git_timeout=args.git_timeout,
        )
        
        # Execute mirroring
        do_mirror(provider, mirror_opts)
        
        logger.info("All done")
        return 0
        
    except GitMirrorError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error occurred: {e}")
        return e.exit_code
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
