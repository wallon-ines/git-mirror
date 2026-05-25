"""GitHub provider implementation.

Corresponds to: src/provider/github.rs
"""

import logging
from typing import List, Optional, Union

import requests

from . import (
    Provider,
    Mirror,
    MirrorError,
    DescriptionError,
    SkipError,
    RepositoryDescription,
)

logger = logging.getLogger(__name__)


class GitHub(Provider):
    """GitHub repository provider."""
    
    def __init__(
        self,
        url: str = "https://api.github.com",
        org: str = "",
        use_http: bool = False,
        private_token: Optional[str] = None,
        useragent: str = "git-mirror/0.14.16",
    ):
        """Initialize GitHub provider."""
        self.url = url
        self.org = org
        self.use_http = use_http
        self.private_token = private_token
        self.useragent = useragent
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": useragent,
            "Accept": "application/vnd.github.v3+json",
        })
        if private_token:
            self.session.headers.update({"Authorization": f"token {private_token}"})
    
    def get_label(self) -> str:
        return f"{self.url}/orgs/{self.org}"
    
    def get_mirror_repos(self) -> List[Union[Mirror, MirrorError]]:
        """Get list of repositories to mirror."""
        mirrors = []
        
        try:
            url = f"{self.url}/orgs/{self.org}/repos"
            logger.debug(f"URL: {url}")
            
            response = self.session.get(url, timeout=30)
            logger.debug(f"HTTP Status: {response.status_code}")
            
            if response.status_code == 401:
                raise MirrorError(
                    f"Unauthorized ({response.status_code}) for {url}. "
                    "Please check your PRIVATE_TOKEN."
                )
            elif response.status_code != 200:
                raise MirrorError(
                    f"API call failed with status {response.status_code} for {url}"
                )
            
            try:
                projects = response.json()
            except ValueError as e:
                raise MirrorError(f"Failed to parse JSON response: {e}")
            
            for project in projects:
                description = project.get("description") or ""
                web_url = project.get("html_url", "")
                ssh_url = project.get("ssh_url", "")
                clone_url = project.get("clone_url", "")
                
                try:
                    repo_desc = RepositoryDescription.from_yaml(description)
                    
                    if repo_desc.skip:
                        mirrors.append(SkipError(web_url))
                        logger.info(f"Skipping {web_url}")
                        continue
                    
                    destination = clone_url if self.use_http else ssh_url
                    logger.debug(f"Mirror: {repo_desc.origin} -> {destination}")
                    
                    mirror = Mirror(
                        origin=repo_desc.origin,
                        destination=destination,
                        refspec=repo_desc.refspec,
                        lfs=repo_desc.lfs,
                    )
                    mirrors.append(mirror)
                    
                except ValueError as e:
                    mirrors.append(DescriptionError(web_url, e))
                    logger.warning(f"Invalid description for {web_url}: {e}")
        
        except requests.RequestException as e:
            raise MirrorError(f"Failed to connect to GitHub: {e}")
        
        return mirrors
