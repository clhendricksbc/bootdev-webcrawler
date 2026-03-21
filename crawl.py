from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin

def normalize_url(input_url):
    parsed_parts = urlparse(input_url)
    parsed_url = parsed_parts.netloc + parsed_parts.path
    final = parsed_url.rstrip("/")
    return final.lower()

def get_heading_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    h_tag = soup.find("h1") or soup.find("h2")
    if h_tag:
        return h_tag.get_text(strip=True)
    else: return ""

def get_first_paragraph_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    main = soup.find("main")
    para = soup.find("p")
    if isinstance(main, Tag):
        main_p = main.find("p")
        if main_p:
            return main_p.get_text(strip=True)
    elif para:
        return para.get_text(strip=True)
    else: return ""

def get_urls_from_html(html, base_url):
    result = []
    soup = BeautifulSoup(html, 'html.parser')
    find_a = soup.find_all("a")
    for a in find_a:
        if href := a.get("href"): # type: ignore
            try:
                abs_url = urljoin(base_url, href) # type: ignore
                result.append(abs_url)
            except Exception as e:
                print(f"{str(e)}: {href}")
    return result

def get_images_from_html(html, base_url):
    result = []
    soup = BeautifulSoup(html, 'html.parser')
    find_img_url = soup.find_all("img")
    for img in find_img_url:
        if src := img.get("src"): # pyright: ignore[reportAttributeAccessIssue]
            try:
                abs_url = urljoin(base_url, src) # pyright: ignore[reportArgumentType]
                result.append(abs_url)
            except Exception as e:
                print(f"{str(e)}: {src}")
    return result

def extract_page_data(html, page_url):
    result = {}
    result["url"] = page_url
    result["heading"] = get_heading_from_html(html)
    result["first_paragraph"] = get_first_paragraph_from_html(html)
    result["outgoing_links"] = get_urls_from_html(html, page_url)
    result["image_urls"] = get_images_from_html(html, page_url)
    return result


