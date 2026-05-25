"""GitLab provider implementation.

Corresponds to: src/provider/gitlab.rs
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

PER_PAGE = 100


class GitLab(Provider):
    """GitLab repository provider."""
    
    def __init__(
        self,
        url: str = "https://gitlab.com",
        group: str = "",
        use_http: bool = False,
        private_token: Optional[str] = None,
        recursive: bool = True,
    ):
        """Initialize GitLab provider."""
        self.url = url
        self.group = group
        self.use_http = use_http
        self.private_token = private_token
        self.recursive = recursive
        
        self.session = requests.Session()
        if private_token:
            self.session.headers.update({"PRIVATE-TOKEN": private_token})
    
    def get_label(self) -> str:
        return f"{self.url}/{self.group}"
    
    def _get_paged(self, endpoint: str) -> List[dict]:
        """Get paginated results from GitLab API."""
        results = []
        page = 1
        
        while True:
            url = f"{self.url}/api/v4{endpoint}?per_page={PER_PAGE}&page={page}"
            logger.debug(f"URL: {url}")
            
            try:
                response = self.session.get(url, timeout=30)
            except requests.RequestException as e:
                raise MirrorError(f"Unable to connect to {url}: {e}")
            
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
                page_results = response.json()
            except ValueError as e:
                raise MirrorError(f"Failed to parse JSON response: {e}")
            
            results.extend(page_results)
            
            if "x-next-page" not in response.headers or not response.headers["x-next-page"]:
                logger.debug("No more pages")
                break
            
            page += 1
        
        return results
    
    def _get_subgroups(self, group_id: str) -> List[str]:
        """Get all subgroups recursively."""
        subgroups = [group_id]
        
        try:
            endpoint = f"/groups/{group_id}/subgroups"
            groups_data = self._get_paged(endpoint)
            
            for group in groups_data:
                subgroups.extend(self._get_subgroups(str(group["id"])))
        except MirrorError as e:
            logger.warning(f"Unable to get subgroups: {e}")
        
        return subgroups
    
    def get_mirror_repos(self) -> List[Union[Mirror, MirrorError]]:
        """Get list of repositories to mirror."""
        mirrors = []
        
        try:
            if self.recursive:
                groups = self._get_subgroups(self.group)
            else:
                groups = [self.group]
            
            projects = []
            for group_id in groups:
                try:
                    endpoint = f"/groups/{group_id}/projects"
                    group_projects = self._get_paged(endpoint)
                    projects.extend(group_projects)
                except MirrorError as e:
                    logger.warning(f"Failed to get projects from group {group_id}: {e}")
            
            for project in projects:
                description = project.get("description") or ""
                web_url = project.get("web_url", "")
                ssh_url = project.get("ssh_url_to_repo", "")
                http_url = project.get("http_url_to_repo", "")
                
                try:
                    repo_desc = RepositoryDescription.from_yaml(description)
                    
                    if repo_desc.skip:
                        mirrors.append(SkipError(web_url))
                        logger.info(f"Skipping {web_url}")
                        continue
                    
                    destination = http_url if self.use_http else ssh_url
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
        
        except MirrorError as e:
            logger.error(f"Failed to get mirror repos: {e}")
            raise
        
        return mirrors
