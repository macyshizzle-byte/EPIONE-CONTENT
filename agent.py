"""Core agent logic cho Epione B2B Sales Content Writer."""

import base64
import mimetypes
from pathlib import Path

import anthropic
from prompts import get_prompt
from web_reader import WebReader


def _encode_image(image_path: str) -> tuple[str, str]:
    """Đọc file ảnh và encode base64.

    Returns:
        (base64_data, media_type)
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {image_path}")

    media_type, _ = mimetypes.guess_type(str(path))
    if not media_type or not media_type.startswith("image/"):
        raise ValueError(f"File không phải ảnh: {image_path}")

    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")

    return data, media_type


class EpioneSalesAgent:
    """Agent viết content B2B cho đội sale Epione sử dụng Claude API."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.conversation_history: list[dict] = []
        self.web_reader = WebReader()

    def generate(self, content_type: str, user_request: str, role: str = "sale_b2b") -> str:
        """Tạo content dựa trên loại, yêu cầu, và vai trò."""
        system_prompt = get_prompt(content_type, role)

        self.conversation_history.append({
            "role": "user",
            "content": user_request,
        })

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=self.conversation_history,
        )

        assistant_message = response.content[0].text

        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message,
        })

        return assistant_message

    def generate_from_image(
        self,
        image_path: str,
        user_request: str = "",
        platform: str = "",
        role: str = "sale_b2b",
    ) -> str:
        """Phân tích ảnh và tạo content + hướng dẫn design.

        Args:
            image_path: Đường dẫn đến file ảnh
            user_request: Yêu cầu bổ sung từ user (tùy chọn)
            platform: Platform cụ thể (linkedin/facebook/instagram)
            role: Vai trò người viết (sale_b2b/sale_b2c/ky_thuat)
        """
        system_prompt = get_prompt("image", role)
        image_data, media_type = _encode_image(image_path)

        # Build message content với ảnh + text
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                },
            },
        ]

        text_parts = [f"Nhìn ảnh này và viết caption cho {platform or 'LinkedIn'}."]
        if user_request:
            text_parts.append(f"Yêu cầu thêm: {user_request}")

        content.append({"type": "text", "text": "\n".join(text_parts)})

        self.conversation_history.append({"role": "user", "content": content})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system_prompt,
            messages=self.conversation_history,
        )

        assistant_message = response.content[0].text

        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message,
        })

        return assistant_message

    def generate_design_html(self, image_path: str, design_data: dict) -> str:
        """Tạo file HTML social media post từ ảnh + design data.

        Args:
            image_path: Đường dẫn ảnh gốc
            design_data: Dict chứa headline, subtext, cta, layout, ratio

        Returns:
            Đường dẫn file HTML đã tạo
        """
        from design_generator import DesignGenerator
        generator = DesignGenerator()
        return generator.create_post(image_path, design_data)

    def research_from_url(self, url: str) -> str:
        """Đọc bài viết từ URL và chuyển thể thành content Epione."""
        result = self.web_reader.fetch(url)

        if not result["success"]:
            return f"Không đọc được bài viết: {result['error']}\nURL: {url}"

        user_message = (
            f"Đây là bài viết gốc từ {url}:\n\n"
            f"**Tiêu đề**: {result['title']}\n\n"
            f"**Nội dung**:\n{result['content']}\n\n"
            f"---\n\n"
            f"Hãy chuyển thể bài viết trên thành content cho đội sale Epione. "
            f"Tạo đầy đủ các phiên bản: LinkedIn, Facebook, và Carousel nếu phù hợp."
        )

        return self.generate("research", user_message, role="sale_b2b")

    def list_articles(self, url: str) -> list[dict]:
        """Lấy danh sách bài viết từ trang listing."""
        return self.web_reader.fetch_article_links(url)

    def reset_conversation(self):
        """Xóa lịch sử hội thoại để bắt đầu chủ đề mới."""
        self.conversation_history.clear()
