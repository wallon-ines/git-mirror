#!/usr/bin/env python3
"""Git Mirror - Python port of the Rust utility.

Usage examples:

    # Mirror GitLab group
    export PRIVATE_TOKEN="your_token"
    python -m git_mirror -g mirror-test
    
    # Mirror GitHub organization
    export PRIVATE_TOKEN="your_token"
    python -m git_mirror -p GitHub -g my-org
    
    # Use custom GitLab instance
    python -m git_mirror -g mirror-test -u http://gitlab.example.org
    
    # Dry run
    python -m git_mirror -g mirror-test --dry-run -vv
    
    # Parallel execution (8 workers)
    python -m git_mirror -g mirror-test -c 8
    
    # With timeout for git operations
    python -m git_mirror -g mirror-test --git-timeout 120
"""

import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from git_mirror.main import main

if __name__ == "__main__":
    sys.exit(main())
