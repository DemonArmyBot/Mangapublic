import os
from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import List, AsyncIterable
from httpx import AsyncClient, Response
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class MangaCard:
    client: "MangaClient"
    name: str
    url: str
    picture_url: str

    def get_url(self):
        return self.url

    def unique(self):
        return str(hash(self.url))

@dataclass
class MangaChapter:
    client: "MangaClient"
    name: str
    url: str
    manga: MangaCard
    pictures: List[str]

    def get_url(self):
        return self.url

    def unique(self):
        return str(hash(self.url))

def clean(name, length=-1):
    while '  ' in name:
        name = name.replace('  ', ' ')
    name = name.replace(':', '')
    if length != -1:
        name = name[:length]
    return name

class LanguageSingleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        name = kwargs.get('name', args[0] if args else 'default')
        if name not in cls._instances:
            cls._instances[name] = super().__call__(*args, **kwargs)
        return cls._instances[name]

class MangaClient(AsyncClient, metaclass=LanguageSingleton):
    def __init__(self, *args, name="client", **kwargs):
        if name == "client":
            raise NotImplementedError
        super().__init__(*args, **kwargs)
        self.name = name
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
        })

    async def get_url(self, url, *args, file_name=None, cache=False, req_content=True, method='get', data=None, **kwargs):
        if cache:
            path = Path(f'cache/{self.name}/{file_name}')
            os.makedirs(path.parent, exist_ok=True)
            try:
                with open(path, 'rb') as f:
                    content = f.read()
                if req_content:
                    return content
                else:
                    return Response(status_code=200, content=content)
            except FileNotFoundError:
                if method == 'get':
                    response = await self.get(url, *args, **kwargs)
                elif method == 'post':
                    response = await self.post(url, data=data or {}, **kwargs)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                if str(response.status_code).startswith('2'):
                    content = response.content
                    with open(path, 'wb') as f:
                        f.write(content)
        else:
            if method == 'get':
                response = await self.get(url, *args, **kwargs)
            elif method == 'post':
                response = await self.post(url, data=data or {}, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            content = response.content
        if req_content:
            return content
        else:
            return response

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def set_pictures(self, manga_chapter: MangaChapter):
        requests_url = manga_chapter.url
        headers = {**self.headers}
        if manga_chapter.manga:
            headers['referer'] = manga_chapter.manga.url
        logger.debug(f"Fetching URL: {requests_url} with headers: {headers}")
        response = await self.get(requests_url, headers=headers)
        logger.debug(f"Response status: {response.status_code}, type: {type(response)}")
        if response.status_code == 403:
            logger.warning("403 Forbidden: Attempting to bypass with Playwright")
            html_content = await self.fetch_with_playwright(requests_url)
            manga_chapter.pictures = await self.pictures_from_chapters(html_content.encode('utf-8'), html_content)
        else:
            content = response.content
            manga_chapter.pictures = await self.pictures_from_chapters(content, response)
        return manga_chapter

    async def fetch_with_playwright(self, url: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            html_content = await page.content()
            await browser.close()
            return html_content

    async def download_pictures(self, manga_chapter: MangaChapter):
        if not manga_chapter.pictures:
            await self.set_pictures(manga_chapter)

        folder_name = f'{clean(manga_chapter.manga.name)}/{clean(manga_chapter.name)}'
        i = 0
        for picture in manga_chapter.pictures:
            ext = picture.split('.')[-1].split('?')[0].lower()
            file_name = f'{folder_name}/{format(i, "05d")}.{ext}'
            for _ in range(3):
                req = await self.get_picture(manga_chapter, picture, file_name=file_name, cache=True, req_content=False)
                if str(req.status_code).startswith('2'):
                    break
            else:
                raise ValueError(f"Failed to download picture: {picture}")
            i += 1

        return Path(f'cache/{manga_chapter.client.name}') / folder_name

    async def get_picture(self, manga_chapter: MangaChapter, url, *args, **kwargs):
        return await self.get_url(url, *args, **kwargs)

    async def get_cover(self, manga_card: MangaCard, *args, **kwargs):
        return await self.get_url(manga_card.picture_url, *args, **kwargs)

    async def check_updated_urls(self, last_chapters: List['LastChapter']):
        return [lc.url for lc in last_chapters], []

    @abstractmethod
    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        raise NotImplementedError

    @abstractmethod
    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:
        raise NotImplementedError

    @abstractmethod
    async def contains_url(self, url: str):
        raise NotImplementedError

    @abstractmethod
    async def iter_chapters(self, manga_url: str, manga_name: str) -> AsyncIterable[MangaChapter]:
        raise NotImplementedError

    @abstractmethod
    async def pictures_from_chapters(self, content: bytes, response=None):
        raise NotImplementedError
