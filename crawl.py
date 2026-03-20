from urllib.parse import urlparse

def normalize_url(input_url):
    parsed_parts = urlparse(input_url)
    parsed_url = parsed_parts.netloc + parsed_parts.path
    final = parsed_url.removesuffix("/")
    return final
