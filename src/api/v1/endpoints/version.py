"""
EasyPay Payment Gateway - API Version Endpoints
"""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from typing import Optional

from src.api.v1.schemas.versioning import VersionResponse, VersionInfo, API_VERSIONS
from src.api.v1.middleware.auth import require_auth

router = APIRouter()


@router.get(
    "/version",
    response_model=VersionResponse,
    responses={
        200: {"description": "API version information retrieved successfully"},
        400: {"model": dict, "description": "Invalid version header"},
        401: {"model": dict, "description": "Authentication required"}
    },
    summary="Get API Version Information",
    description="""
    Retrieve information about the current API version and all supported versions.
    
    ### Version Information
    - **Current Version**: The active API version
    - **Supported Versions**: All stable versions available for use
    - **Deprecated Versions**: Versions that are deprecated but still supported
    - **Beta Versions**: Experimental versions for testing
    
    ### Version Status
    - `stable`: Production-ready version
    - `deprecated`: Version is deprecated but still supported
    - `beta`: Experimental version for testing
    
    ### Version Headers
    You can specify the API version using the `API-Version` header:
    ```
    API-Version: v1
    ```
    
    ### Migration Support
    - Migration guides are available for deprecated versions
    - Changelog URLs provide detailed version information
    - Sunset dates indicate when versions will be removed
    """,
    tags=["version"]
)
async def get_api_version(
    api_version: Optional[str] = Header(None, alias="API-Version", description="Requested API version"),
    auth_context: dict = Depends(require_auth)
) -> VersionResponse:
    """
    Get API version information.
    
    Args:
        api_version: Requested API version from header
        auth_context: Authentication context
        
    Returns:
        VersionResponse: API version information
        
    Raises:
        HTTPException: If requested version is not supported
    """
    # Validate requested version
    if api_version and api_version not in API_VERSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported API version: {api_version}. Supported versions: {list(API_VERSIONS.keys())}"
        )
    
    # Build version information
    supported_versions = []
    deprecated_versions = []
    beta_versions = []
    
    for version, info in API_VERSIONS.items():
        version_info = VersionInfo(
            version=version,
            status=info["status"],
            release_date=info["release_date"],
            deprecation_date=info.get("deprecation_date"),
            sunset_date=info.get("sunset_date"),
            changelog_url=info.get("changelog_url"),
            migration_guide_url=info.get("migration_guide_url")
        )
        
        if info["status"] == "stable":
            supported_versions.append(version_info)
        elif info["status"] == "deprecated":
            deprecated_versions.append(version_info)
        elif info["status"] == "beta":
            beta_versions.append(version_info)
    
    return VersionResponse(
        current_version="v1",
        supported_versions=supported_versions,
        deprecated_versions=deprecated_versions,
        beta_versions=beta_versions
    )


@router.get(
    "/version/{version}",
    response_model=VersionInfo,
    responses={
        200: {"description": "Version details retrieved successfully"},
        404: {"model": dict, "description": "Version not found"},
        401: {"model": dict, "description": "Authentication required"}
    },
    summary="Get Specific Version Details",
    description="""
    Get detailed information about a specific API version.
    
    ### Version Details Include
    - Version status and lifecycle information
    - Release and deprecation dates
    - Available features and endpoints
    - Migration guides and changelog URLs
    
    ### Version Lifecycle
    1. **Beta**: Experimental version for testing
    2. **Stable**: Production-ready version
    3. **Deprecated**: Version marked for removal
    4. **Sunset**: Version no longer supported
    """,
    tags=["version"]
)
async def get_version_details(
    version: str,
    auth_context: dict = Depends(require_auth)
) -> VersionInfo:
    """
    Get detailed information about a specific API version.
    
    Args:
        version: API version to get details for
        auth_context: Authentication context
        
    Returns:
        VersionInfo: Detailed version information
        
    Raises:
        HTTPException: If version is not found
    """
    if version not in API_VERSIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found"
        )
    
    info = API_VERSIONS[version]
    return VersionInfo(
        version=version,
        status=info["status"],
        release_date=info["release_date"],
        deprecation_date=info.get("deprecation_date"),
        sunset_date=info.get("sunset_date"),
        changelog_url=info.get("changelog_url"),
        migration_guide_url=info.get("migration_guide_url")
    )
