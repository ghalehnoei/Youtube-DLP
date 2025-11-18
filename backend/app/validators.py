"""
URL validation utilities.
"""
from urllib.parse import urlparse
from typing import Optional, List, Tuple
from app.config import settings


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format and check against allowed hosts.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in ['http', 'https']:
            return False, "URL must use http or https protocol"
        
        # Check netloc (domain)
        if not parsed.netloc:
            return False, "Invalid URL: missing domain"
        
        # Check allowed hosts if configured
        if settings.allowed_hosts:
            allowed = [h.strip() for h in settings.allowed_hosts.split(',')]
            host = parsed.netloc.lower()
            # Remove port if present
            if ':' in host:
                host = host.split(':')[0]
            
            # Check if host is in allowed list
            if not any(allowed_host in host or host.endswith('.' + allowed_host) for allowed_host in allowed):
                return False, f"Domain not allowed. Allowed domains: {', '.join(allowed)}"
        
        return True, None
    
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"

