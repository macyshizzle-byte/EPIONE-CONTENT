"""Tạo HTML social media post design (gradient style) từ ảnh + content."""

import base64
import mimetypes
import os
from datetime import datetime
from pathlib import Path


class DesignGenerator:
    """Tạo file HTML social media post với gradient overlay + branding Epione."""

    RATIOS = {
        "instagram": ("1080px", "1080px"),
        "instagram_portrait": ("1080px", "1350px"),
        "facebook": ("1200px", "630px"),
        "linkedin": ("1200px", "627px"),
        "story": ("1080px", "1920px"),
    }

    def __init__(self):
        if os.environ.get("VERCEL"):
            self.OUTPUT_DIR = "/tmp/designs"
        else:
            self.OUTPUT_DIR = "designs"
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def create_post(self, image_path: str, design_data: dict) -> str:
        """Tạo file HTML social media post.

        Returns:
            Đường dẫn file HTML đã tạo.
        """
        platform = design_data.get("platform", "instagram")
        width, height = self.RATIOS.get(platform, self.RATIOS["instagram"])

        img_path = Path(image_path)
        media_type, _ = mimetypes.guess_type(str(img_path))
        with open(img_path, "rb") as f:
            img_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
        img_src = f"data:{media_type};base64,{img_b64}"

        headline = design_data.get("headline", "")
        subtext = design_data.get("subtext", "")
        cta = design_data.get("cta", "")
        text_position = design_data.get("text_position", "bottom")

        if text_position == "top":
            gradient = "linear-gradient(to bottom, rgba(16,6,80,0.85) 0%, rgba(16,6,80,0.4) 40%, transparent 70%)"
            text_css = "top: 0; padding: 48px 48px 0 48px;"
        elif text_position == "center":
            gradient = "linear-gradient(to bottom, rgba(16,6,80,0.3) 0%, rgba(16,6,80,0.7) 35%, rgba(16,6,80,0.7) 65%, rgba(16,6,80,0.3) 100%)"
            text_css = "top: 50%; transform: translateY(-50%); padding: 0 48px;"
        else:
            gradient = "linear-gradient(to top, rgba(16,6,80,0.9) 0%, rgba(16,6,80,0.5) 35%, transparent 65%)"
            text_css = "bottom: 0; padding: 0 48px 48px 48px;"

        subtext_html = f'<p class="subtext">{subtext}</p>' if subtext else ""
        cta_html = f'<div class="cta-wrap"><span class="cta-btn">{cta}</span></div>' if cta else ""

        html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Epione - {platform.title()} Post</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ display:flex; flex-direction:column; justify-content:center; align-items:center; min-height:100vh; background:#1a1a2e; font-family:'Nunito Sans',sans-serif; padding:40px; }}
.post {{ width:{width}; height:{height}; position:relative; overflow:hidden; border-radius:16px; box-shadow:0 24px 80px rgba(0,0,0,0.4); }}
.post img {{ width:100%; height:100%; object-fit:cover; display:block; }}
.gradient {{ position:absolute; inset:0; background:{gradient}; }}
.accent {{ position:absolute; bottom:0; left:0; width:100%; height:4px; background:linear-gradient(90deg,#10069F 0%,#4a3aff 50%,transparent 100%); }}
.logo {{ position:absolute; top:24px; left:28px; z-index:3; display:flex; align-items:center; gap:10px; }}
.logo .brand {{ font-size:13px; font-weight:700; letter-spacing:2.5px; color:#fff; text-shadow:0 2px 8px rgba(0,0,0,0.4); }}
.logo .sub {{ font-size:9px; font-weight:400; letter-spacing:1.5px; color:rgba(255,255,255,0.85); }}
.text {{ position:absolute; left:0; right:0; {text_css} z-index:2; }}
.text h1 {{ font-size:32px; font-weight:700; color:#fff; line-height:1.25; letter-spacing:-0.5px; text-shadow:0 2px 12px rgba(0,0,0,0.4); max-width:85%; }}
.subtext {{ font-size:15px; color:rgba(255,255,255,0.88); margin-top:10px; line-height:1.5; text-shadow:0 1px 6px rgba(0,0,0,0.3); }}
.cta-wrap {{ margin-top:20px; }}
.cta-btn {{ display:inline-block; background:#10069F; color:#fff; padding:13px 36px; border-radius:28px; font-weight:600; font-size:14px; box-shadow:0 4px 20px rgba(16,6,159,0.5); }}
</style>
</head>
<body>
<div class="post">
  <img src="{img_src}" alt="Epione">
  <div class="gradient"></div>
  <div class="accent"></div>
  <div class="logo">
    <svg width="30" height="30" viewBox="0 0 120 120" fill="none">
      <circle cx="60" cy="60" r="52" stroke="#fff" stroke-width="1.5" opacity=".3"/>
      <circle cx="60" cy="60" r="38" stroke="#fff" stroke-width="2" opacity=".5"/>
      <circle cx="60" cy="60" r="24" stroke="#fff" stroke-width="2.5" opacity=".7"/>
      <circle cx="60" cy="60" r="10" fill="#fff"/>
    </svg>
    <div><div class="brand">FOCUS</div><div class="sub">by Epione</div></div>
  </div>
  <div class="text">
    <h1>{headline}</h1>
    {subtext_html}
    {cta_html}
  </div>
</div>
</body>
</html>"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"epione_{platform}_{timestamp}.html"
        filepath = os.path.join(self.OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        return filepath
