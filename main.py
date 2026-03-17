"""CLI interface cho Epione B2B Sales Content Agent."""

from __future__ import annotations

import json
import os
import re
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from agent import EpioneSalesAgent
from design_generator import DesignGenerator

load_dotenv()

console = Console()

MENU = """
[bold #10069F]EPIONE — B2B Sales Content Agent[/bold #10069F]

Chọn loại content muốn tạo:

  [bold]1.[/bold] LinkedIn (bài đăng cho sale, thought leadership)
  [bold]2.[/bold] Facebook / Instagram (showcase, dự án, behind the scenes)
  [bold]3.[/bold] Outreach (email, Zalo, LinkedIn DM cho khách)
  [bold]4.[/bold] Case Study (viết case study dự án)
  [bold]5.[/bold] Content Calendar (lên ý tưởng theo tuần/tháng)
  [bold]6.[/bold] Research & Adapt (đọc bài từ web → chuyển thể content)
  [bold]7.[/bold] Image → Design (bỏ ảnh vào → viết content + tạo design)
  [bold]8.[/bold] Đổi chủ đề (reset hội thoại)
  [bold]9.[/bold] Thoát
"""

CONTENT_TYPES = {
    "1": ("linkedin", "LinkedIn B2B"),
    "2": ("facebook", "Facebook / Instagram"),
    "3": ("outreach", "Outreach Message"),
    "4": ("casestudy", "Case Study"),
    "5": ("ideas", "Content Calendar"),
}

SUGGESTED_SOURCES = [
    ("Steelcase Insights", "https://www.steelcase.com/research/"),
    ("Herman Miller Research", "https://www.hermanmiller.com/research/"),
    ("Haworth Knowledge", "https://www.haworth.com/eu/en/knowledge.html"),
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")


def _is_image_path(path: str) -> bool:
    """Kiểm tra xem path có phải file ảnh không."""
    return any(path.lower().endswith(ext) for ext in IMAGE_EXTENSIONS)


def _ensure_today_folder() -> str:
    """Tạo folder ngày hôm nay nếu chưa có, trả về path."""
    from datetime import date
    today = date.today().isoformat()
    folder = os.path.join(IMAGES_DIR, today)
    os.makedirs(folder, exist_ok=True)
    return folder


def _list_date_folders() -> list[str]:
    """Liệt kê các folder ngày trong images/, mới nhất lên đầu."""
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR, exist_ok=True)
        return []
    folders = []
    for name in sorted(os.listdir(IMAGES_DIR), reverse=True):
        full = os.path.join(IMAGES_DIR, name)
        if os.path.isdir(full) and not name.startswith("."):
            folders.append(name)
    return folders


def _list_images_in_folder(folder_path: str) -> list[str]:
    """Liệt kê tất cả ảnh trong 1 folder."""
    images = []
    for name in sorted(os.listdir(folder_path)):
        if _is_image_path(name):
            images.append(os.path.join(folder_path, name))
    return images


def _parse_design_from_response(response: str) -> dict:
    """Parse thông tin design từ response của Claude để tạo HTML.

    Tìm headline, subtext, CTA từ phần HƯỚNG DẪN DESIGN trong output.
    """
    design = {
        "headline": "",
        "subtext": "",
        "cta": "",
        "platform": "instagram",
        "text_position": "bottom",
        "overlay_opacity": 0.4,
    }

    # Tìm headline
    headline_match = re.search(r'Headline:\s*["\u201c](.+?)["\u201d]', response)
    if headline_match:
        design["headline"] = headline_match.group(1)

    # Tìm subtext
    subtext_match = re.search(r'Subtext:\s*["\u201c](.+?)["\u201d]', response)
    if subtext_match:
        design["subtext"] = subtext_match.group(1)

    # Tìm CTA
    cta_match = re.search(r'CTA:\s*["\u201c](.+?)["\u201d]', response)
    if cta_match:
        design["cta"] = cta_match.group(1)

    # Tìm platform
    if "linkedin" in response.lower():
        design["platform"] = "linkedin"
    if "instagram" in response.lower() and "1:1" in response:
        design["platform"] = "instagram"
    if "4:5" in response:
        design["platform"] = "instagram_portrait"
    if "story" in response.lower() and "9:16" in response:
        design["platform"] = "story"

    # Tìm text position
    if "top" in response.lower() and "vị trí: top" in response.lower():
        design["text_position"] = "top"
    elif "center" in response.lower() and "vị trí: center" in response.lower():
        design["text_position"] = "center"

    return design


def _pick_image_from_folder() -> str | None:
    """Cho user chọn ảnh từ folder images/ hoặc paste path trực tiếp.

    Returns:
        Đường dẫn ảnh hoặc None nếu user quay lại.
    """
    today_folder = _ensure_today_folder()
    date_folders = _list_date_folders()

    console.print(f"\n[bold]📁 Folder ảnh: [#10069F]{IMAGES_DIR}[/#10069F][/bold]")
    console.print(f"[dim]Bỏ ảnh vào folder ngày (ví dụ: images/2026-03-17/) rồi chọn từ đây[/dim]\n")

    # Hiển thị các folder ngày
    if date_folders:
        table = Table(border_style="dim")
        table.add_column("#", style="bold", width=4)
        table.add_column("Ngày", style="bold")
        table.add_column("Số ảnh", justify="right")
        for i, folder_name in enumerate(date_folders, 1):
            folder_path = os.path.join(IMAGES_DIR, folder_name)
            img_count = len(_list_images_in_folder(folder_path))
            style = "#10069F" if folder_name == os.path.basename(today_folder) else ""
            label = f"{folder_name} (hôm nay)" if folder_name == os.path.basename(today_folder) else folder_name
            table.add_row(str(i), f"[{style}]{label}[/{style}]" if style else label, str(img_count))
        console.print(table)
    else:
        console.print("[yellow]Chưa có folder ngày nào. Bỏ ảnh vào images/YYYY-MM-DD/[/yellow]")

    console.print("\n[bold]Chọn:[/bold]")
    console.print("  • Nhập [bold]số[/bold] để chọn folder ngày")
    console.print("  • Kéo thả / paste [bold]đường dẫn ảnh[/bold] trực tiếp")
    console.print("  • Gõ [bold]'back'[/bold] để quay lại menu\n")

    user_input = Prompt.ask("[bold green]Chọn folder hoặc paste ảnh[/bold green]")

    if user_input.lower() in ("back", "menu", "quay lại"):
        return None

    # Nếu user paste đường dẫn ảnh trực tiếp
    clean_path = user_input.strip().strip("'\"")
    if os.path.isfile(clean_path) and _is_image_path(clean_path):
        return clean_path

    # Nếu user chọn số folder
    try:
        idx = int(user_input) - 1
        if 0 <= idx < len(date_folders):
            folder_path = os.path.join(IMAGES_DIR, date_folders[idx])
        else:
            console.print("[red]Số không hợp lệ[/red]")
            return None
    except ValueError:
        console.print("[red]Không nhận diện được. Nhập số folder hoặc paste đường dẫn ảnh.[/red]")
        return None

    # Liệt kê ảnh trong folder đã chọn
    images = _list_images_in_folder(folder_path)
    if not images:
        console.print(f"[yellow]Folder {date_folders[idx]} trống. Bỏ ảnh vào: {folder_path}[/yellow]")
        return None

    console.print(f"\n[bold]Ảnh trong {date_folders[idx]}:[/bold]\n")
    for i, img_path in enumerate(images, 1):
        filename = os.path.basename(img_path)
        size_kb = os.path.getsize(img_path) / 1024
        console.print(f"  [bold]{i}.[/bold] {filename} [dim]({size_kb:.0f} KB)[/dim]")

    console.print(f"\n  [bold]a.[/bold] Xử lý [bold]tất cả[/bold] ảnh trong folder")

    pick = Prompt.ask("\nChọn ảnh (số hoặc 'a' cho tất cả)")

    if pick.lower() == "a":
        return folder_path  # Trả về folder path, xử lý batch ở ngoài

    try:
        img_idx = int(pick) - 1
        if 0 <= img_idx < len(images):
            return images[img_idx]
        console.print("[red]Số không hợp lệ[/red]")
        return None
    except ValueError:
        console.print("[red]Vui lòng nhập số[/red]")
        return None


def _process_single_image(agent: EpioneSalesAgent, design_gen: DesignGenerator, image_path: str):
    """Xử lý 1 ảnh: phân tích + viết content + tạo design."""
    filename = os.path.basename(image_path)
    console.print(f"\n[bold #10069F]Đang xử lý: {filename}[/bold #10069F]")

    # Hỏi thêm context
    extra = Prompt.ask(
        "[dim]Ghi chú thêm (sản phẩm gì, dùng cho gì... hoặc Enter để bỏ qua)[/dim]",
        default="",
    )

    platform = Prompt.ask(
        "Platform",
        choices=["instagram", "linkedin", "facebook", "story"],
        default="instagram",
    )

    # Claude Vision phân tích + viết content
    with console.status("[bold #10069F]Đang phân tích ảnh và viết content...[/bold #10069F]"):
        try:
            result = agent.generate_from_image(
                image_path=image_path,
                user_request=extra,
                platform=platform,
            )
        except Exception as e:
            console.print(f"[red]Lỗi: {e}[/red]")
            return

    console.print()
    console.print(Panel(
        Markdown(result),
        title=f"[bold]{filename}[/bold]",
        border_style="#10069F",
        padding=(1, 2),
    ))

    # Hỏi tạo design HTML
    make_design = Prompt.ask("\nTạo design HTML?", choices=["y", "n"], default="y")

    if make_design == "y":
        design_data = _parse_design_from_response(result)
        design_data["platform"] = platform

        # Chọn style
        console.print("\n[bold]Chọn style design:[/bold]")
        console.print("  [bold]1.[/bold] Gradient — ảnh full + text overlay gradient (mặc định)")
        console.print("  [bold]2.[/bold] Card — ảnh trên + text dưới nền trắng")
        console.print("  [bold]3.[/bold] Minimal — ảnh full + thanh glass bar phía dưới")
        style_choice = Prompt.ask("Style", choices=["1", "2", "3"], default="1")
        design_data["style"] = {"1": "gradient", "2": "solid", "3": "minimal"}[style_choice]

        console.print("\n[bold]Thông tin design (chỉnh sửa nếu cần):[/bold]")
        design_data["headline"] = Prompt.ask(
            "  Headline", default=design_data["headline"] or "Focus by Epione",
        )
        design_data["subtext"] = Prompt.ask(
            "  Subtext", default=design_data["subtext"],
        )
        design_data["cta"] = Prompt.ask(
            "  CTA button", default=design_data["cta"] or "Liên hệ tư vấn",
        )

        with console.status("[bold #10069F]Đang tạo design...[/bold #10069F]"):
            try:
                filepath = design_gen.create_post(image_path, design_data)
            except Exception as e:
                console.print(f"[red]Lỗi tạo design: {e}[/red]")
                return

        console.print(f"[green]Đã tạo: {filepath}[/green]")

        open_browser = Prompt.ask("Mở trong browser?", choices=["y", "n"], default="y")
        if open_browser == "y":
            design_gen.open_in_browser(filepath)

    # Cho phép chỉnh sửa tiếp
    console.print("\n[dim]Gõ tiếp để chỉnh sửa, hoặc Enter để xử lý ảnh tiếp theo.[/dim]")

    while True:
        followup = Prompt.ask("[bold green]Bạn[/bold green]", default="")
        if not followup.strip():
            break
        if followup.lower() in ("back", "menu", "quay lại"):
            break

        with console.status("[bold #10069F]Đang chỉnh sửa...[/bold #10069F]"):
            try:
                result = agent.generate("image", followup)
            except Exception as e:
                console.print(f"[red]Lỗi: {e}[/red]")
                continue

        console.print()
        console.print(Panel(Markdown(result), title="[bold]Chỉnh sửa[/bold]", border_style="#10069F", padding=(1, 2)))

    agent.reset_conversation()


def run_image_mode(agent: EpioneSalesAgent):
    """Chạy mode Image → Design."""
    console.print("\n[bold #10069F]Mode: Image → Design[/bold #10069F]")
    console.print("[dim]Bỏ ảnh vào folder images/YYYY-MM-DD/ → Agent phân tích + viết content + tạo design[/dim]")

    design_gen = DesignGenerator()

    while True:
        picked = _pick_image_from_folder()

        if picked is None:
            break

        # Nếu chọn cả folder (batch mode)
        if os.path.isdir(picked):
            images = _list_images_in_folder(picked)
            console.print(f"\n[bold]Xử lý {len(images)} ảnh trong {os.path.basename(picked)}:[/bold]")
            for i, img_path in enumerate(images, 1):
                console.print(f"\n{'='*60}")
                console.print(f"[bold]Ảnh {i}/{len(images)}[/bold]")
                _process_single_image(agent, design_gen, img_path)
            console.print(f"\n[green]Đã xử lý xong {len(images)} ảnh![/green]")
        else:
            _process_single_image(agent, design_gen, picked)


def run_research_mode(agent: EpioneSalesAgent):
    """Chạy mode Research & Adapt."""
    console.print("\n[bold #10069F]Mode: Research & Adapt[/bold #10069F]")
    console.print("[dim]Đọc bài viết từ các trang chuyên ngành → chuyển thể thành content Epione[/dim]\n")

    table = Table(title="Nguồn tham khảo gợi ý", border_style="#10069F")
    table.add_column("Tên", style="bold")
    table.add_column("URL", style="dim")
    for name, url in SUGGESTED_SOURCES:
        table.add_row(name, url)
    console.print(table)
    console.print()

    while True:
        console.print("[bold]Bạn có thể:[/bold]")
        console.print("  • Paste URL bài viết cụ thể để chuyển thể")
        console.print("  • Paste URL trang listing để xem danh sách bài")
        console.print("  • Gõ 'back' để quay lại menu\n")

        user_input = Prompt.ask("[bold green]URL hoặc lệnh[/bold green]")

        if user_input.lower() in ("back", "menu", "quay lại"):
            break

        if not user_input.strip():
            continue

        url = user_input.strip()

        if not url.startswith("http"):
            console.print("[red]Vui lòng nhập URL hợp lệ (bắt đầu bằng http)[/red]")
            continue

        action = Prompt.ask("Bạn muốn", choices=["doc", "list"], default="doc")

        if action == "list":
            with console.status("[bold #10069F]Đang quét danh sách bài viết...[/bold #10069F]"):
                articles = agent.list_articles(url)

            if not articles:
                console.print("[yellow]Không tìm thấy bài viết nào. Thử paste URL bài cụ thể.[/yellow]\n")
                continue

            console.print(f"\n[bold]Tìm thấy {len(articles)} bài viết:[/bold]\n")
            for i, article in enumerate(articles, 1):
                console.print(f"  [bold]{i}.[/bold] {article['title']}")
                console.print(f"     [dim]{article['url']}[/dim]")
            console.print()

            pick = Prompt.ask("Chọn số bài muốn đọc (hoặc 'skip')")
            if pick.lower() == "skip":
                continue
            try:
                idx = int(pick) - 1
                if 0 <= idx < len(articles):
                    url = articles[idx]["url"]
                    console.print(f"\n[bold]Đang đọc: {articles[idx]['title']}[/bold]")
                else:
                    console.print("[red]Số không hợp lệ[/red]")
                    continue
            except ValueError:
                console.print("[red]Vui lòng nhập số[/red]")
                continue

        with console.status("[bold #10069F]Đang đọc bài viết và chuyển thể content...[/bold #10069F]"):
            try:
                result = agent.research_from_url(url)
            except Exception as e:
                console.print(f"[red]Lỗi: {e}[/red]")
                continue

        console.print()
        console.print(Panel(
            Markdown(result),
            title="[bold]Research & Adapt[/bold]",
            border_style="#10069F",
            padding=(1, 2),
        ))
        console.print("[dim]Gõ tiếp để yêu cầu chỉnh sửa, paste URL mới, hoặc 'back' để quay lại menu.[/dim]")

        while True:
            console.print()
            followup = Prompt.ask("[bold green]Bạn[/bold green]")

            if followup.lower() in ("back", "menu", "quay lại"):
                agent.reset_conversation()
                return

            if followup.strip().startswith("http"):
                agent.reset_conversation()
                break

            if not followup.strip():
                continue

            with console.status("[bold #10069F]Đang chỉnh sửa...[/bold #10069F]"):
                try:
                    result = agent.generate("research", followup)
                except Exception as e:
                    console.print(f"[red]Lỗi: {e}[/red]")
                    continue

            console.print()
            console.print(Panel(
                Markdown(result),
                title="[bold]Research & Adapt[/bold]",
                border_style="#10069F",
                padding=(1, 2),
            ))


def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Chưa cấu hình ANTHROPIC_API_KEY![/red]")
        console.print("Tạo file .env với nội dung: ANTHROPIC_API_KEY=sk-ant-xxxxx")
        sys.exit(1)

    agent = EpioneSalesAgent(api_key=api_key)
    current_type = None

    console.print(Panel(
        "EPIONE — B2B Sales Content Agent",
        subtitle="Booth cách âm · Nội thất công thái học · Giải pháp không gian làm việc",
        style="bold #10069F",
        expand=False,
    ))
    console.print("[dim]Agent AI viết content cho đội sale B2B của Epione[/dim]\n")

    while True:
        console.print(MENU)
        choice = Prompt.ask(
            "Lựa chọn",
            choices=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
            default="1",
        )

        if choice == "9":
            console.print("[#10069F]Tạm biệt! Chốt deal ngon nha 💪[/#10069F]")
            break

        if choice == "8":
            agent.reset_conversation()
            current_type = None
            console.print("[green]Đã reset hội thoại. Chọn loại content mới.[/green]\n")
            continue

        if choice == "7":
            agent.reset_conversation()
            run_image_mode(agent)
            continue

        if choice == "6":
            agent.reset_conversation()
            run_research_mode(agent)
            continue

        content_type, type_label = CONTENT_TYPES[choice]

        if content_type != current_type:
            agent.reset_conversation()
            current_type = content_type

        console.print(f"\n[bold #10069F]Mode: {type_label}[/bold #10069F]")
        console.print("[dim]Mô tả yêu cầu cụ thể — ví dụ: chủ đề, đối tượng khách, sản phẩm, dự án...[/dim]")

        while True:
            console.print()
            user_input = Prompt.ask("[bold green]Bạn[/bold green]")

            if user_input.lower() in ("back", "menu", "quay lại"):
                break

            if not user_input.strip():
                continue

            with console.status("[bold #10069F]Đang viết content...[/bold #10069F]"):
                try:
                    result = agent.generate(content_type, user_input)
                except Exception as e:
                    console.print(f"[red]Lỗi: {e}[/red]")
                    continue

            console.print()
            console.print(Panel(
                Markdown(result),
                title=f"[bold]{type_label}[/bold]",
                border_style="#10069F",
                padding=(1, 2),
            ))
            console.print("[dim]Gõ tiếp để chỉnh sửa/bổ sung, hoặc 'back' để quay lại menu.[/dim]")


if __name__ == "__main__":
    main()
