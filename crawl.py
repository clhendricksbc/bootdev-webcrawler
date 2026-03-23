from locale import normalize
from tabnanny import check

from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin
import aiohttp
import asyncio
import requests

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

def get_html(url):
    try:
        response = requests.get(url, headers={"User-Agent": "BootCrawler/1.0"})
    except Exception as e:
        raise Exception(f"Error while fetching {url}: {e}")
    if response.status_code >= 400:
        raise Exception(f"HTTP error: {response.status_code} {response.reason}")
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type :
        raise Exception(f"Content type is not text/html; it is {content_type}")
    return response.text


def crawl_page(base_url, current_url=None, page_data=None):
    if current_url is None:
        current_url = base_url
    if page_data is None:
        page_data = {}
    if urlparse(current_url).netloc != urlparse(base_url).netloc:
        return page_data
    current_normalized = normalize_url(current_url)
    if current_normalized in page_data:
        return page_data
    try:
        current_html = get_html(current_url)
    except Exception as e:
        print(f"Error occurred: {e}")
        return page_data
    print(current_url)
    extracted_info = extract_page_data(current_html, current_normalized)
    page_data[current_normalized] = extracted_info
    urls_list = get_urls_from_html(current_html, base_url)
    for url in urls_list:
        page_data = crawl_page(base_url, url, page_data)
    return page_data

class AsyncCrawler:
    def __init__(self, base_url, max_concurrency, max_pages):
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        self.page_data = {}
        self.lock = asyncio.Lock()
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(self.max_concurrency)
        self.session = None
        self.max_pages = max_pages
        self.should_stop = False
        self.all_tasks = set()
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
    
    async def add_page_visit(self, normalized_url):
        
        async with self.lock:
            if self.should_stop:
                return False
            if len(self.page_data) >= self.max_pages:
                self.should_stop = True
                print("reached maximum number of pages to crawl")
                for task in self.all_tasks:
                    task.cancel()
                return False
            if normalized_url in self.page_data:
                return False
            else: 
                return True
            
    async def get_html(self, url):
        try:
            async with self.session.get(url, headers={"User-Agent": "BootCrawler/1.0"}) as response:
                if response.status > 399:
                    raise Exception(f"got HTTP error: {response.status}")
                    return None
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type:
                    raise Exception(f"got non-HTML response: {content_type}")
                    return None
                return await response.text()
        except Exception as e:
            raise Exception(f"Error while fetching {url}: {e}")
            return None
    
    async def crawl_page(self, current_url):
        if self.should_stop:
            return
        if urlparse(current_url).netloc != self.base_domain:
            return
        normalized_url = normalize_url(current_url)
        new_page_visit = await self.add_page_visit(normalized_url)
        if not new_page_visit:
            return
        async with self.semaphore:
            print(
                f"Crawling {normalized_url} (Active: {self.max_concurrency - self.semaphore._value})"
            )
            html = await self.get_html(current_url)
            if html is None:
                return
            page_data = extract_page_data(html, current_url)
            async with self.lock:
                self.page_data[normalized_url] = page_data
            next_urls = get_urls_from_html(html, self.base_url)
        tasks = []
        for url in next_urls:
            crawl_task = asyncio.create_task(self.crawl_page(url))
            tasks.append(crawl_task)
            self.all_tasks.add(crawl_task)
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            finally:
                for task in tasks:
                    self.all_tasks.discard(task)
        
    
    async def crawl(self):
        await self.crawl_page(self.base_url)
        return self.page_data
    
async def crawl_site_async(base_url, max_concurrency, max_pages):
    async with AsyncCrawler(base_url, max_concurrency, max_pages) as crawler:
        return await crawler.crawl()


            


        




