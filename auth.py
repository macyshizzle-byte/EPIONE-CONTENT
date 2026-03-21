"""Server-side Supabase JWT authentication for Flask."""

import os
from functools import wraps

import jwt
from flask import g, jsonify, request


SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")


def require_auth(f):
    """Decorator: verify Supabase JWT token from Authorization header."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if not SUPABASE_JWT_SECRET:
            return jsonify({"error": "Server chưa cấu hình SUPABASE_JWT_SECRET"}), 500

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Chưa đăng nhập"}), 401

        token = auth_header[7:]
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
            g.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Phiên đăng nhập hết hạn, vui lòng đăng nhập lại"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token không hợp lệ"}), 401

        return f(*args, **kwargs)

    return decorated
