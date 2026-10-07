from urllib.parse import urlparse

def is_valid_url(text):
    parts = urlparse(text.strip())
    return parts.scheme in ("http", "https") and bool(parts.netloc)