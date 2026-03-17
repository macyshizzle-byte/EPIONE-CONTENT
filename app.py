"""Flask web app cho Epione B2B Sales Content Agent."""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from agent import EpioneSalesAgent
from design_generator import DesignGenerator

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Init agent
api_key = os.getenv("ANTHROPIC_API_KEY")
agent = EpioneSalesAgent(api_key=api_key) if api_key else None
design_gen = DesignGenerator()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def generate():
    """Tạo content từ text input."""
    if not agent:
        return jsonify({"error": "Chưa cấu hình ANTHROPIC_API_KEY"}), 500

    data = request.json
    content_type = data.get("type", "linkedin")
    user_input = data.get("prompt", "").strip()

    if not user_input:
        return jsonify({"error": "Vui lòng nhập nội dung yêu cầu"}), 400

    # Reset conversation mỗi request (stateless cho web)
    agent.reset_conversation()

    try:
        role = data.get("role", "sale_b2b")
        result = agent.generate(content_type, user_input, role=role)
        return jsonify({"content": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/research", methods=["POST"])
def research():
    """Đọc bài từ URL và chuyển thể."""
    if not agent:
        return jsonify({"error": "Chưa cấu hình ANTHROPIC_API_KEY"}), 500

    data = request.json
    url = data.get("url", "").strip()

    if not url or not url.startswith("http"):
        return jsonify({"error": "Vui lòng nhập URL hợp lệ"}), 400

    agent.reset_conversation()

    try:
        result = agent.research_from_url(url)
        return jsonify({"content": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/image", methods=["POST"])
def image_content():
    """Phân tích ảnh và tạo content + design."""
    if not agent:
        return jsonify({"error": "Chưa cấu hình ANTHROPIC_API_KEY"}), 500

    if "image" not in request.files:
        return jsonify({"error": "Chưa chọn ảnh"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "Chưa chọn ảnh"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        return jsonify({"error": f"Định dạng không hỗ trợ. Chấp nhận: {', '.join(IMAGE_EXTENSIONS)}"}), 400

    # Lưu ảnh
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    file.save(filepath)

    extra = request.form.get("prompt", "")

    agent.reset_conversation()

    try:
        role = request.form.get("role", "sale_b2b")
        platform = request.form.get("platform", "linkedin")
        result = agent.generate_from_image(
            image_path=filepath,
            user_request=extra,
            platform=platform,
            role=role,
        )
        return jsonify({
            "content": result,
            "image_path": filepath,
            "image_url": f"/images/uploads/{file.filename}",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/community", methods=["POST"])
def community():
    """Tạo bài đăng cho cộng đồng Facebook."""
    if not agent:
        return jsonify({"error": "Chưa cấu hình ANTHROPIC_API_KEY"}), 500

    data = request.json
    community_name = data.get("community", "").strip()
    rules = data.get("rules", "").strip()
    topic = data.get("topic", "").strip()
    role = data.get("role", "sale_b2b")

    if not topic:
        return jsonify({"error": "Vui lòng nhập chủ đề bài đăng"}), 400

    agent.reset_conversation()

    # Build prompt với rules của cộng đồng
    user_msg = f"Viết bài đăng trong cộng đồng Facebook: {community_name}\n\n"
    if rules:
        user_msg += f"QUY ĐỊNH CỘNG ĐỒNG (PHẢI TUÂN THỦ):\n{rules}\n\n"
    user_msg += f"Chủ đề bài viết: {topic}"

    try:
        result = agent.generate("community", user_msg, role=role)
        return jsonify({"content": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/design", methods=["POST"])
def create_design():
    """Tạo design HTML từ ảnh + text."""
    data = request.json
    image_path = data.get("image_path", "")
    headline = data.get("headline", "Focus by Epione")
    subtext = data.get("subtext", "")
    cta = data.get("cta", "Liên hệ tư vấn")
    platform = data.get("platform", "instagram")

    if not image_path or not os.path.exists(image_path):
        return jsonify({"error": "Không tìm thấy ảnh"}), 400

    try:
        filepath = design_gen.create_post(image_path, {
            "headline": headline,
            "subtext": subtext,
            "cta": cta,
            "platform": platform,
        })
        return jsonify({"design_path": filepath})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload-image", methods=["POST"])
def upload_image():
    """Upload ảnh và trả về đường dẫn (không phân tích)."""
    if "image" not in request.files:
        return jsonify({"error": "Chưa chọn ảnh"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "Chưa chọn ảnh"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        return jsonify({"error": "Định dạng không hỗ trợ"}), 400

    filepath = os.path.join(UPLOAD_DIR, file.filename)
    file.save(filepath)
    return jsonify({"image_path": filepath, "image_url": f"/images/uploads/{file.filename}"})


@app.route("/designs/<path:filename>")
def serve_design(filename):
    """Serve file design HTML."""
    from flask import send_from_directory
    return send_from_directory("designs", filename)


@app.route("/images/uploads/<path:filename>")
def serve_upload(filename):
    """Serve uploaded images."""
    from flask import send_from_directory
    return send_from_directory(UPLOAD_DIR, filename)


if __name__ == "__main__":
    if not api_key:
        print("⚠️  Chưa cấu hình ANTHROPIC_API_KEY! Tạo file .env")
    print("🚀 Epione Content Agent đang chạy tại: http://localhost:3000")
    port = int(os.environ.get("PORT", 3000))
    app.run(debug=False, host="0.0.0.0", port=port)
