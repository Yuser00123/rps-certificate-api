"""
Rock Paper Scissors Champion Certificate Generator API
========================================================
Flask app designed for Vercel (serverless) + local development.
Certificate for winning Rock Paper Scissors against the AI.
NO SCORE — only name + date of issue.

Endpoints
---------
GET  /                                  -> Landing page with live form
GET  /health                            -> {"status": "ok"}
GET  /certificate?name=Aarav            -> PNG certificate image
GET  /certificate/<name>                -> PNG certificate image (path param)
POST /certificate                       -> JSON {"name": "..."} -> PNG
GET  /api/certificate?...               -> alias of /certificate

Optional query params
---------------------
download=true   -> force file download instead of inline preview
format=jpg|png|json -> image format (default png; json = base64 response)
date=15 November 2026 -> override date of issue (defaults to today, Asia/Kolkata)

Template: assets/certificate_template.png (cream/navy/gold template, grey border cropped)
Fonts:    assets/fonts/*.ttf (Cinzel, Great Vibes, Poppins, Montserrat)
"""

import base64
import io
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

from flask import Flask, Response, jsonify, request, send_file
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Paths (work both locally and on Vercel where this file lives in /api)
# ---------------------------------------------------------------------------
THIS_DIR = Path(__file__).resolve().parent          # .../api
BASE_DIR = THIS_DIR.parent                           # project root
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

TEMPLATE_CANDIDATES = [
    ASSETS_DIR / "certificate_template.png",
    THIS_DIR / "certificate_template.png",
    Path.cwd() / "assets" / "certificate_template.png",
    Path("/home/user/rps-certificate-api/assets/certificate_template.png"),
]

FONT_FILES = {
    "cinzel": FONTS_DIR / "Cinzel-Bold.ttf",
    "script": FONTS_DIR / "GreatVibes-Regular.ttf",
    "poppins": FONTS_DIR / "Poppins-Regular.ttf",
    "poppins_bold": FONTS_DIR / "Poppins-Bold.ttf",
    "poppins_semi": FONTS_DIR / "Poppins-SemiBold.ttf",
    "montserrat": FONTS_DIR / "Montserrat-Regular.ttf",
}

FALLBACK_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
]

# Colours sampled from the template
CREAM = (255, 248, 237, 255)
NAVY = (30, 54, 90, 255)
NAVY_DARK = (22, 32, 54, 255)
GOLD = (201, 168, 106, 255)
INK = (34, 34, 34, 255)
GREY = (90, 90, 90, 255)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_template() -> Path:
    for p in TEMPLATE_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError(
        "certificate_template.png not found. Place it in assets/certificate_template.png"
    )


def get_font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_FILES.get(kind)
    if path and path.exists():
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            pass
    for fb in FALLBACK_FONTS:
        if os.path.exists(fb):
            try:
                return ImageFont.truetype(fb, size)
            except Exception:
                continue
    return ImageFont.load_default()


def fit_font(kind: str, text: str, max_width: int, start_size: int, min_size: int = 28):
    size = start_size
    while size > min_size:
        font = get_font(kind, size)
        try:
            w = font.getlength(text)
        except Exception:
            w = size * len(text) * 0.6
        if w <= max_width:
            return font, size
        size -= 4
    return get_font(kind, min_size), min_size


def text_size(draw: ImageDraw.ImageDraw, text: str, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_centered(draw, cx, y, text, font, fill):
    w, h = text_size(draw, text, font)
    draw.text((cx - w / 2, y), text, font=font, fill=fill)
    return w, h


def draw_spaced_centered(draw, cx, y, text, font, fill, spacing=8):
    widths, total = [], 0
    for ch in text:
        try:
            w = font.getlength(ch)
        except Exception:
            w = 20
        widths.append(w)
        total += w
    total += spacing * (len(text) - 1)
    x = cx - total / 2
    sx = x
    for ch, w in zip(text, widths):
        draw.text((sx, y), ch, font=font, fill=fill)
        sx += w + spacing
    return total


def current_date_str() -> str:
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
    except Exception:
        now = datetime.now()
    return now.strftime("%d %B %Y")


def generate_certificate(name: str, date_str=None) -> Image.Image:
    """Render name + date onto the RPS Champion template (no score)."""
    template_path = find_template()
    img = Image.open(template_path).convert("RGBA")
    W, H = img.size
    cx = W // 2
    draw = ImageDraw.Draw(img)

    # --- Cover the template's original text with cream rectangles ---
    # (template already contains CERTIFICATE / Name Surname / Lorem / DATE)
    covers = [
        (0.26, 0.115, 0.74, 0.230),   # title
        (0.34, 0.230, 0.66, 0.300),   # OF ACHIEVEMENT badge
        (0.28, 0.330, 0.72, 0.390),   # THIS CERTIFICATE IS PROUDLY PRESENTED TO
        (0.22, 0.390, 0.78, 0.530),   # Name Surname + its underline
        (0.16, 0.520, 0.87, 0.630),   # Lorem ipsum paragraph
        (0.18, 0.770, 0.46, 0.880),   # DATE line + label
    ]
    for x0, y0, x1, y1 in covers:
        draw.rectangle([W * x0, H * y0, W * x1, H * y1], fill=CREAM)

    # --- Title: ROCK PAPER SCISSORS (kept clear of the BEST AWARD ribbon) ---
    title_font, _ = fit_font("cinzel", "ROCK PAPER SCISSORS", int(W * 0.52), int(H * 0.062), 44)
    draw_spaced_centered(draw, cx - int(W * 0.04), H * 0.135, "ROCK PAPER SCISSORS", title_font, NAVY_DARK, spacing=4)

    # --- Badge: CHAMPION CERTIFICATE (hexagon outline like template) ---
    badge_y = H * 0.245
    badge_w = int(W * 0.36)
    badge_h = int(H * 0.058)
    bx0, by0 = cx - badge_w // 2, badge_y
    bx1, by1 = cx + badge_w // 2, badge_y + badge_h
    point = int(badge_h * 0.55)
    hexagon = [
        (bx0 + point, by0), (bx1 - point, by0),
        (bx1, by0 + badge_h // 2), (bx1 - point, by1),
        (bx0 + point, by1), (bx0, by0 + badge_h // 2),
    ]
    draw.polygon(hexagon, fill=CREAM, outline=NAVY_DARK, width=4)
    badge_font, _ = fit_font("cinzel", "CHAMPION CERTIFICATE", badge_w - point * 2 - 30, int(H * 0.026), 20)
    bw, bh = text_size(draw, "CHAMPION CERTIFICATE", badge_font)
    draw.text((cx - bw / 2, by0 + (badge_h - bh) / 2 - 4), "CHAMPION CERTIFICATE", font=badge_font, fill=NAVY_DARK)

    # --- THIS CERTIFICATE IS PROUDLY PRESENTED TO ---
    presented_font = get_font("poppins_semi", int(H * 0.021))
    draw_spaced_centered(
        draw, cx, H * 0.345,
        "THIS CERTIFICATE IS PROUDLY PRESENTED TO",
        presented_font, INK, spacing=4,
    )

    # --- Name (script, navy) — NO underline (it cut through names before) ---
    name_font, _ = fit_font("script", name, int(W * 0.58), int(H * 0.088), 44)
    nw, nh = text_size(draw, name, name_font)
    name_y = H * 0.405
    draw.text((cx - nw / 2, name_y), name, font=name_font, fill=NAVY)

    # --- Description: for defeating the AI in Rock Paper Scissors ---
    desc_font = get_font("poppins", int(H * 0.026))
    draw_centered(draw, cx, H * 0.545, "for defeating the AI in Rock Paper Scissors", desc_font, INK)

    # --- Date of Issue (line + date, like template's DATE block) ---
    date_display = date_str or current_date_str()
    date_font = get_font("poppins_semi", int(H * 0.021))
    date_text = f"Date of Issue:  {date_display}"
    dw, dh = text_size(draw, date_text, date_font)
    date_cx = int(W * 0.32)
    line_y = H * 0.795
    line_w = dw + 40
    draw.line([(date_cx - line_w / 2, line_y), (date_cx + line_w / 2, line_y)], fill=GREY, width=3)
    draw_centered(draw, date_cx, line_y + 14, date_text, date_font, INK)

    return img.convert("RGB")


def certificate_response(name, date_str=None, download=False, as_json=False, fmt="png"):
    if not name or not str(name).strip():
        return jsonify({"error": "Missing required parameter: name"}), 400

    name = str(name).strip()[:80]
    fmt = str(fmt or "png").lower()
    if fmt in ("jpg", "jpeg"):
        fmt = "jpeg"
    elif fmt != "png":
        fmt = "png"
    if as_json:
        fmt = "jpeg"
    try:
        img = generate_certificate(name, date_str=date_str)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to generate certificate: {e}"}), 500

    buf = io.BytesIO()
    if fmt == "jpeg":
        img.save(buf, format="JPEG", quality=90, optimize=True)
        mime, ext = "image/jpeg", "jpg"
    else:
        img.save(buf, format="PNG", compress_level=1)
        mime, ext = "image/png", "png"
    buf.seek(0)

    if as_json:
        b64 = base64.b64encode(buf.getvalue()).decode()
        return jsonify({
            "name": name,
            "date_of_issue": date_str or current_date_str(),
            "image_base64": b64,
            "data_uri": f"data:{mime};base64,{b64}",
        })

    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip().replace(" ", "_")
    filename = f"Rock_Paper_Scissors_Champion_Certificate_{safe_name}.{ext}"
    resp = send_file(buf, mimetype=mime, as_attachment=download, download_name=filename)
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Certificate-Name"] = name
    return resp


def parse_inputs():
    name = request.args.get("name")
    date_str = request.args.get("date")
    download = request.args.get("download", "").lower() in ("1", "true", "yes")
    fmt = request.args.get("format", "png").lower()
    as_json = fmt == "json"
    if fmt not in ("png", "jpg", "jpeg", "json"):
        fmt = "png"
    if request.is_json:
        data = request.get_json(silent=True) or {}
        name = name or data.get("name")
        date_str = date_str or data.get("date")
        download = download or bool(data.get("download"))
        if data.get("format"):
            fmt = str(data.get("format")).lower()
            as_json = fmt == "json"
    elif request.form:
        name = name or request.form.get("name")
        date_str = date_str or request.form.get("date")
    return name, date_str, download, as_json, fmt


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.after_request
def add_cors(resp: Response):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@app.route("/", methods=["GET"])
def index():
    html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rock Paper Scissors Champion Certificate</title>
<style>
 body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#101c33;color:#fff;
      min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
 .card{max-width:640px;width:100%;background:linear-gradient(160deg,#16294d,#1e365a);border:1px solid #c9a86a66;
       border-radius:20px;padding:28px;box-shadow:0 20px 60px #0009}
 h1{margin:0 0 6px;font-size:26px;color:#c9a86a} p{color:#cfd6ff;line-height:1.5}
 label{display:block;margin:14px 0 6px;font-weight:600} input{width:100%;padding:12px;border-radius:10px;border:1px solid #ffffff33;background:#101c33;color:#fff;font-size:16px;box-sizing:border-box}
 button{margin-top:18px;width:100%;padding:13px;border:0;border-radius:10px;background:#c9a86a;color:#16294d;font-weight:800;font-size:16px;cursor:pointer}
 button:hover{background:#e0c48a} img{max-width:100%;border-radius:12px;margin-top:18px;display:none}
 .api{background:#101c33;border:1px solid #ffffff22;border-radius:10px;padding:12px;overflow:auto;font-size:13px}
</style></head><body><div class="card">
<h1>✊✋✌️ Rock Paper Scissors Champion Certificate</h1>
<p>Enter a name to generate a Champion Certificate for beating the AI. No score needed.</p>
<form id="f">
<label>Name</label><input id="name" placeholder="e.g. Aarav Sharma" required>
<button>Generate Certificate</button></form>
<img id="out" alt="Certificate preview">
<p style="margin-top:18px">API usage:</p>
<div class="api">GET /certificate?name=Aarav<br>GET /certificate/Aarav<br>POST /certificate  {"name":"Aarav"}</div>
</div><script>
document.getElementById('f').onsubmit=e=>{e.preventDefault();
 const n=encodeURIComponent(document.getElementById('name').value);
 const img=document.getElementById('out'); img.src='/certificate?name='+n+'&format=jpg'; img.style.display='block';};
</script></body></html>"""
    return Response(html, mimetype="text/html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "rps-certificate-api"})


@app.route("/certificate", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/certificate", methods=["GET", "POST", "OPTIONS"])
def certificate():
    if request.method == "OPTIONS":
        return Response(status=204)
    name, date_str, download, as_json, fmt = parse_inputs()
    return certificate_response(name, date_str, download, as_json, fmt)


@app.route("/certificate/<path:name>", methods=["GET"])
@app.route("/api/certificate/<path:name>", methods=["GET"])
def certificate_path(name):
    name = unquote(name)
    date_str = request.args.get("date")
    download = request.args.get("download", "").lower() in ("1", "true", "yes")
    fmt = request.args.get("format", "png").lower()
    as_json = fmt == "json"
    return certificate_response(name, date_str, download, as_json, fmt)


app_obj = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
