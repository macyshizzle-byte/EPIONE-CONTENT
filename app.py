"""Flask web app cho Epione B2B Sales Content Agent."""

import json
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from agent import EpioneSalesAgent
from design_generator import DesignGenerator
from drive_browser import download_drive_file, list_drive_folders, list_drive_images
from google_drive import GoogleDriveUploader
from inventory import estimate_delivery, get_stock
from quote_manager import create_quote, get_quote, list_quotes

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload

# Vercel filesystem is read-only — use /tmp for uploads
if os.environ.get("VERCEL"):
    UPLOAD_DIR = "/tmp/uploads"
else:
    UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Init agent
api_key = os.getenv("ANTHROPIC_API_KEY")
agent = EpioneSalesAgent(api_key=api_key) if api_key else None
design_gen = DesignGenerator()

# Init Google Drive uploader
drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
drive_uploader = None
if drive_folder_id and (os.getenv("GCP_KEY_JSON") or os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gcp-key.json"))):
    try:
        drive_uploader = GoogleDriveUploader(root_folder_id=drive_folder_id)
    except Exception as e:
        print(f"⚠️  Google Drive init failed: {e}")

# Load product catalog
CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "products", "catalog.json")
with open(CATALOG_PATH, "r", encoding="utf-8") as f:
    CATALOG = json.load(f)


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
        gender = data.get("gender", "nam")
        result = agent.generate(content_type, user_input, role=role, gender=gender)
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
        gender = request.form.get("gender", "nam")
        platform = request.form.get("platform", "linkedin")
        result = agent.generate_from_image(
            image_path=filepath,
            user_request=extra,
            platform=platform,
            role=role,
            gender=gender,
        )
        response = {
            "content": result,
            "image_path": filepath,
            "image_url": f"/images/uploads/{file.filename}",
        }

        # Auto-upload lên Google Drive nếu có chọn sản phẩm
        product_name = request.form.get("product", "")
        if drive_uploader and product_name:
            try:
                drive_result = drive_uploader.upload_file(filepath, product_name)
                response["drive"] = drive_result
            except Exception as drive_err:
                response["drive_error"] = str(drive_err)

        return jsonify(response)
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
    gender = data.get("gender", "nam")

    if not topic:
        return jsonify({"error": "Vui lòng nhập chủ đề bài đăng"}), 400

    agent.reset_conversation()

    # Build prompt với rules của cộng đồng
    user_msg = f"Viết bài đăng trong cộng đồng Facebook: {community_name}\n\n"
    if rules:
        user_msg += f"QUY ĐỊNH CỘNG ĐỒNG (PHẢI TUÂN THỦ):\n{rules}\n\n"
    user_msg += f"Chủ đề bài viết: {topic}"

    try:
        style = data.get("style", "short")
        content_type = "community_" + style
        result = agent.generate(content_type, user_msg, role=role, gender=gender)
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


# ========== PRODUCT CATALOG API ==========

@app.route("/api/products")
def products():
    """Return full product catalog with optional category filter."""
    category = request.args.get("category")
    products_list = CATALOG["products"]
    if category:
        products_list = [p for p in products_list if p["category"] == category]
    return jsonify({"categories": CATALOG["categories"], "products": products_list})


@app.route("/api/products/<product_id>")
def product_detail(product_id):
    """Return single product with inventory info."""
    product = next((p for p in CATALOG["products"] if p["id"] == product_id), None)
    if not product:
        return jsonify({"error": "Sản phẩm không tồn tại"}), 404

    # Attach stock info to each variant
    for variant in product.get("variants", []):
        variant["stock"] = get_stock(variant["sku"])

    return jsonify(product)


@app.route("/api/inventory/<sku>")
def inventory(sku):
    """Get stock info for a SKU."""
    return jsonify(get_stock(sku))


@app.route("/api/inventory/delivery", methods=["POST"])
def delivery_estimate():
    """Estimate delivery for a SKU + quantity."""
    data = request.json
    sku = data.get("sku", "")
    quantity = int(data.get("quantity", 1))
    return jsonify(estimate_delivery(sku, quantity))


# ========== QUOTE API ==========

@app.route("/api/quote", methods=["POST"])
def create_quote_api():
    """Create a new quote."""
    data = request.json
    if not data.get("items"):
        return jsonify({"error": "Chưa có sản phẩm trong báo giá"}), 400
    quote = create_quote(data)
    return jsonify(quote)


@app.route("/api/quote/<quote_id>")
def get_quote_api(quote_id):
    """Get quote by ID (JSON)."""
    quote = get_quote(quote_id)
    if not quote:
        return jsonify({"error": "Không tìm thấy báo giá"}), 404
    return jsonify(quote)


@app.route("/api/quotes")
def list_quotes_api():
    """List recent quotes."""
    return jsonify(list_quotes())


@app.route("/quote/<quote_id>")
def quote_page(quote_id):
    """Shareable quote page (HTML — for Zalo/Email links)."""
    quote = get_quote(quote_id)
    if not quote:
        return "Báo giá không tồn tại", 404
    return render_template("quote.html", quote=quote)


# ========== GOOGLE DRIVE API ==========

@app.route("/api/drive/upload", methods=["POST"])
def drive_upload():
    """Upload ảnh lên Google Drive theo thư mục sản phẩm."""
    if not drive_uploader:
        return jsonify({"error": "Chưa cấu hình Google Drive"}), 500

    if "image" not in request.files:
        return jsonify({"error": "Chưa chọn ảnh"}), 400

    product_name = request.form.get("product", "").strip()
    if not product_name:
        return jsonify({"error": "Chưa chọn sản phẩm"}), 400

    files = request.files.getlist("image")
    results = []

    for file in files:
        if not file.filename:
            continue

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            results.append({"name": file.filename, "error": "Định dạng không hỗ trợ"})
            continue

        filepath = os.path.join(UPLOAD_DIR, file.filename)
        file.save(filepath)

        try:
            drive_result = drive_uploader.upload_file(filepath, product_name)
            results.append(drive_result)
        except Exception as e:
            results.append({"name": file.filename, "error": str(e)})

    return jsonify({"uploaded": results, "folder": product_name})


@app.route("/api/drive/folders")
def drive_folders():
    """Liệt kê thư mục sản phẩm trên Drive."""
    if not drive_uploader:
        return jsonify({"error": "Chưa cấu hình Google Drive"}), 500
    try:
        folders = drive_uploader.list_folders()
        return jsonify({"folders": folders})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/drive/files/<path:folder_name>")
def drive_files(folder_name):
    """Liệt kê files trong thư mục sản phẩm."""
    if not drive_uploader:
        return jsonify({"error": "Chưa cấu hình Google Drive"}), 500
    try:
        files = drive_uploader.list_files_in_folder(folder_name)
        return jsonify({"files": files, "folder": folder_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== DRIVE BROWSER API (download/browse) ==========

DRIVE_BROWSE_FOLDER = os.getenv("DRIVE_FOLDER_ID", "")


@app.route("/api/drive/browse")
def drive_browse_files():
    """List images in a Drive folder for browsing."""
    folder_id = request.args.get("folder", DRIVE_BROWSE_FOLDER)
    if not folder_id:
        return jsonify({"error": "Chưa cấu hình DRIVE_FOLDER_ID"}), 400
    page_token = request.args.get("pageToken")
    try:
        result = list_drive_images(folder_id, page_token=page_token)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/drive/browse/folders")
def drive_browse_folders():
    """List sub-folders for browsing."""
    folder_id = request.args.get("folder", DRIVE_BROWSE_FOLDER)
    if not folder_id:
        return jsonify({"error": "Chưa cấu hình DRIVE_FOLDER_ID"}), 400
    try:
        folders = list_drive_folders(folder_id)
        return jsonify({"folders": folders})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/drive/download/<file_id>")
def drive_download(file_id):
    """Download a file from Drive."""
    from flask import Response
    try:
        file_bytes, filename, mime_type = download_drive_file(file_id)
        return Response(
            file_bytes,
            mimetype=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(file_bytes)),
            },
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/drive/preview/<file_id>")
def drive_preview(file_id):
    """Preview (inline) a file from Drive."""
    from flask import Response
    try:
        file_bytes, filename, mime_type = download_drive_file(file_id)
        return Response(
            file_bytes,
            mimetype=mime_type,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "public, max-age=3600",
            },
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    if not api_key:
        print("⚠️  Chưa cấu hình ANTHROPIC_API_KEY! Tạo file .env")
    if drive_uploader:
        print("✅ Google Drive đã kết nối")
    else:
        print("⚠️  Google Drive chưa cấu hình (thiếu gcp-key.json hoặc GOOGLE_DRIVE_FOLDER_ID)")
    print("🚀 Epione Content Agent đang chạy tại: http://localhost:3000")
    port = int(os.environ.get("PORT", 3000))
    app.run(debug=False, host="0.0.0.0", port=port)
