"""Module đọc và parse nội dung bài viết từ URL."""

import re

import requests
from bs4 import BeautifulSoup


class WebReader:
    """Đọc nội dung bài viết từ URL, trả về text sạch."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    # Các tag không chứa nội dung chính
    REMOVE_TAGS = [
        "script", "style", "nav", "header", "footer",
        "aside", "form", "iframe", "noscript",
    ]

    # Các class/id thường là noise
    NOISE_PATTERNS = re.compile(
        r"(cookie|popup|modal|sidebar|widget|advert|promo|newsletter|subscribe|social|share|related|comment)",
        re.IGNORECASE,
    )

    def fetch(self, url: str, timeout: int = 15) -> dict:
        """Fetch và parse nội dung từ URL.

        Returns:
            dict với keys: title, content, url, success, error
        """
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return self._parse(resp.text, url)
        except requests.RequestException as e:
            return {"title": "", "content": "", "url": url, "success": False, "error": str(e)}

    def fetch_article_links(self, url: str, timeout: int = 15) -> list[dict]:
        """Fetch danh sách bài viết từ trang listing (blog/insights page).

        Returns:
            list of dict với keys: title, url
        """
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return self._extract_links(resp.text, url)
        except requests.RequestException:
            return []

    def _parse(self, html: str, url: str) -> dict:
        """Parse HTML thành text sạch."""
        soup = BeautifulSoup(html, "html.parser")

        # Lấy title
        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

        # Xóa các tag noise
        for tag_name in self.REMOVE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Xóa elements có class/id là noise
        for el in soup.find_all(True):
            if not el.attrs:
                continue
            classes = " ".join(el.get("class", []) or [])
            el_id = el.get("id", "") or ""
            if self.NOISE_PATTERNS.search(classes) or self.NOISE_PATTERNS.search(el_id):
                el.decompose()

        # Ưu tiên lấy content từ article tag hoặc main
        content_el = soup.find("article") or soup.find("main") or soup.find("body")

        if not content_el:
            return {"title": title, "content": "", "url": url, "success": False, "error": "Không tìm thấy nội dung"}

        # Extract text có cấu trúc
        paragraphs = []
        for el in content_el.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote"]):
            text = el.get_text(strip=True)
            if not text or len(text) < 10:
                continue
            if el.name.startswith("h"):
                paragraphs.append(f"\n## {text}\n")
            elif el.name == "li":
                paragraphs.append(f"- {text}")
            elif el.name == "blockquote":
                paragraphs.append(f"> {text}")
            else:
                paragraphs.append(text)

        content = "\n\n".join(paragraphs)

        # Giới hạn độ dài để không vượt context window
        if len(content) > 8000:
            content = content[:8000] + "\n\n[... bài viết đã được cắt ngắn ...]"

        return {
            "title": title,
            "content": content,
            "url": url,
            "success": bool(content.strip()),
            "error": "" if content.strip() else "Không extract được nội dung",
        }

    def _extract_links(self, html: str, base_url: str) -> list[dict]:
        """Extract danh sách link bài viết từ trang listing."""
        from urllib.parse import urljoin

        soup = BeautifulSoup(html, "html.parser")

        # Tìm tất cả link có vẻ là bài viết
        links = []
        seen_urls = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)
            title = a_tag.get_text(strip=True)

            # Filter: chỉ lấy link có vẻ là bài viết (có title dài, URL hợp lệ)
            if (
                title
                and len(title) > 15
                and full_url not in seen_urls
                and not any(skip in href for skip in ["#", "javascript:", "mailto:", ".pdf", ".jpg", ".png"])
                and any(hint in href for hint in ["/insights", "/research", "/blog", "/article", "/post", "/story"])
            ):
                links.append({"title": title, "url": full_url})
                seen_urls.add(full_url)

        return links[:20]  # Max 20 bài
