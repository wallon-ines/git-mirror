"""Provider implementations for different Git services.

Corresponds to: src/provider/mod.rs
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Union
import yaml


@dataclass
class Mirror:
    """Representation of a mirror job from origin to destination."""
    origin: str
    destination: str
    refspec: Optional[List[str]] = None
    lfs: bool = True


class MirrorError(Exception):
    """Error during mirror creation."""
    pass


class DescriptionError(MirrorError):
    """Error parsing repository description."""
    def __init__(self, url: str, error: Exception):
        self.url = url
        self.error = error
        super().__init__(f"Error parsing description for {url}: {error}")


class SkipError(MirrorError):
    """Repository should be skipped."""
    def __init__(self, url: str):
        self.url = url
        super().__init__(f"Repository {url} is explicitly skipped")


class RepositoryDescription:
    """Parsed repository description from YAML."""
    
    def __init__(self, data: dict):
        self.origin: str = data.get("origin", "")
        self.skip: bool = data.get("skip", False)
        self.refspec: Optional[List[str]] = data.get("refspec")
        self.lfs: bool = data.get("lfs", True)
    
    @staticmethod
    def from_yaml(yaml_text: str) -> "RepositoryDescription":
        """Parse repository description from YAML."""
        if not yaml_text or not yaml_text.strip():
            raise ValueError("Empty description")
        
        try:
            data = yaml.safe_load(yaml_text) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
        
        if not isinstance(data, dict):
            raise ValueError("Description must be a YAML object")
        
        if "origin" not in data:
            raise ValueError("Missing required 'origin' field")
        
        return RepositoryDescription(data)


class Provider(ABC):
    """Abstract base class for repository providers."""
    
    @abstractmethod
    def get_mirror_repos(self) -> List[Union[Mirror, MirrorError]]:
        """Get list of repositories to mirror."""
        pass
    
    @abstractmethod
    def get_label(self) -> str:
        """Get a label for this provider instance."""
        pass


from .gitlab import GitLab
from .github import GitHub

__all__ = [
    "Mirror",
    "MirrorError",
    "DescriptionError",
    "SkipError",
    "RepositoryDescription",
    "Provider",
    "GitLab",
    "GitHub",
]
