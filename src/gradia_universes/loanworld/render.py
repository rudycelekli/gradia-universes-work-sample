"""Optional pixel renderer for LoanWorld uploads (extra: ``loanworld-render``).

Native-PDF uploads (K0) are written as PDFs whose glyphs are Courier at the
exact layout positions. A ``text_layer_overrides`` entry makes the visible glyph
an image of the true text while the extractable text layer carries the override,
which is the T-ADV text-layer-mismatch trap.

Image uploads are rasterized and degraded with seeded parameters (K1 scan, K2
phone, K3 fax, K4 photocopy, and since phase 7: K5 skew/rotation with mixed page
orientations, K6 hard shadow and spine curl, K7 phone screenshot with UI chrome
and a decoy status-bar date, K8 two pages in one photo). For each output page the
manifest records its SHA-256, its pixel size and ``quad_px``: where the four page corners
(top-left, top-right, bottom-right, bottom-left) landed in output pixels, so any
truth box in centipoints can be mapped into the image with a homography.
``quad_exact`` is false only for K6, whose curl bends the page; there the quad is
the page's unbent outline and boxes near the curled edge are approximate. K7 may
crop the page, so a corner can fall outside the image.

Handwritten runs use a Times-Italic font placeholder. That is recorded as
``font_placeholder_not_valid_for_test``: real handwriting comes from a consented
writer corpus later, never from fonts, in any test split.

Requires pymupdf, numpy and pillow at the pinned versions in pyproject.toml;
byte-identical output is only promised at those versions.
"""

from __future__ import annotations

import hashlib
import io
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import fitz
import numpy as np
from PIL import Image, ImageFilter

from ..canonical import digest

MANIFEST_SCHEMA = "gradia.loanworld.render-manifest.v0"
_FONT = {"courier": "cour", "hand_placeholder": "tiit"}


def _rng(seed: str, upload_id: str, page: int) -> np.random.Generator:
    material = hashlib.sha256(f"{seed}|render|{upload_id}|{page}".encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(material[:16], "big")))


def _page_pdf(upload: dict[str, Any], page_number: int) -> Any:
    """Build one fitz page document for an upload page, applying text-layer overrides."""
    width, height = (v / 100 for v in upload["page_size"])
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    overrides = {
        o["run_index"]: o["text"]
        for o in upload["text_layer_overrides"].get(str(page_number), [])
    }
    for index, run in enumerate(upload["pages"][page_number - 1]["runs"]):
        origin = fitz.Point(run["x_cpt"] / 100, run["baseline_cpt"] / 100)
        font = _FONT[run["font"]]
        if index not in overrides:
            page.insert_text(origin, run["text"], fontsize=run["size_pt"], fontname=font)
            continue
        # Visible truth as a non-extractable image; invisible override as the text layer.
        scratch = fitz.open()
        scratch_page = scratch.new_page(width=width, height=height)
        scratch_page.insert_text(origin, run["text"], fontsize=run["size_pt"], fontname=font)
        x0, y0, x1, y1 = (v / 100 for v in run["bbox_cpt"])
        clip = fitz.Rect(x0, y0, x1, y1)
        pixmap = scratch_page.get_pixmap(clip=clip, dpi=600)
        page.insert_image(clip, stream=pixmap.tobytes("png"))
        page.insert_text(
            origin, overrides[index], fontsize=run["size_pt"], fontname=font, render_mode=3
        )
    return doc


def _homography(src: list[tuple[float, float]], dst: list[tuple[float, float]]) -> list[float]:
    """PIL PERSPECTIVE coefficients mapping output (dst) pixels back to input (src)."""
    rows, rhs = [], []
    for (x, y), (u, v) in zip(dst, src, strict=True):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        rhs.extend([u, v])
    solved = np.linalg.solve(np.array(rows, dtype=np.float64), np.array(rhs, dtype=np.float64))
    return [float(value) for value in solved]


def _rotate_quad(
    quad: list[tuple[float, float]], angle_deg: float, size: tuple[int, int]
) -> tuple[list[tuple[float, float]], tuple[int, int]]:
    """Where corners land after PIL ``rotate(angle, expand=True)`` (counter-clockwise)."""
    width, height = size
    angle = np.deg2rad(angle_deg)
    cos, sin = float(np.cos(angle)), float(np.sin(angle))
    out_w = round(abs(width * cos) + abs(height * sin))
    out_h = round(abs(width * sin) + abs(height * cos))
    cx, cy, ox, oy = width / 2, height / 2, out_w / 2, out_h / 2
    rotated = [
        (ox + (x - cx) * cos + (y - cy) * sin, oy - (x - cx) * sin + (y - cy) * cos)
        for x, y in quad
    ]
    return rotated, (out_w, out_h)


def _distractor(width: int, height: int, seed: str) -> Image.Image:
    """A synthetic second sheet for K8: a receipt-like page with decoy numbers."""
    rng = np.random.Generator(
        np.random.PCG64(int.from_bytes(hashlib.sha256(seed.encode()).digest()[:16], "big"))
    )
    doc = fitz.open()
    page = doc.new_page(width=width * 72 / 200, height=height * 72 / 200)
    page.insert_text(fitz.Point(40, 60), "STORE RECEIPT - NOT PART OF FILE", fontsize=12)
    for line in range(1, 26):
        amount = f"{int(rng.integers(1, 999))}.{int(rng.integers(0, 99)):02d}"
        page.insert_text(fitz.Point(40, 70 + 22 * line), f"ITEM {line:02d}", fontsize=9)
        page.insert_text(fitz.Point(300, 70 + 22 * line), amount, fontsize=9)
    pixmap = page.get_pixmap(dpi=200, colorspace=fitz.csGRAY)
    sheet = Image.frombytes("L", (pixmap.width, pixmap.height), pixmap.samples)
    return sheet.resize((width, height), Image.Resampling.BILINEAR)


def _degrade(
    gray: Image.Image,
    params: dict[str, Any],
    rng: np.random.Generator,
    page_number: int = 1,
    today: str = "2026-01-01",
) -> tuple[Image.Image, list[list[int]]]:
    width, height = gray.size
    corners = [
        (0.0, 0.0),
        (float(width), 0.0),
        (float(width), float(height)),
        (0.0, float(height)),
    ]
    condition = params["condition"]
    if condition == "K1":
        image = gray.filter(ImageFilter.GaussianBlur(params["blur_tenths"] / 10))
        quad = corners
    elif condition == "K2":
        pad = int(0.08 * width)
        angle = np.deg2rad(params["skew_tenths_deg"] / 10)
        cx, cy = width / 2 + pad, height / 2 + pad
        jitter = params["perspective_pct"] / 100
        quad = []
        for (x, y), (jx, jy) in zip(corners, ((1, 1), (-1, 1), (-1, -1), (1, -1)), strict=True):
            x += jx * jitter * width * float(rng.uniform(0.2, 1.0))
            y += jy * jitter * height * float(rng.uniform(0.2, 1.0))
            dx, dy = x + pad - cx, y + pad - cy
            quad.append(
                (
                    cx + dx * np.cos(angle) - dy * np.sin(angle),
                    cy + dx * np.sin(angle) + dy * np.cos(angle),
                )
            )
        out_w, out_h = width + 2 * pad, height + 2 * pad
        image = gray.transform(
            (out_w, out_h),
            Image.Transform.PERSPECTIVE,
            _homography(corners, quad),
            Image.Resampling.BILINEAR,
            fillcolor=96,
        )
        shade = np.linspace(1.0, 1.0 - params["shadow_pct"] / 100, out_w, dtype=np.float64)
        array = np.asarray(image, dtype=np.float64) * shade[np.newaxis, :]
        array += rng.normal(0, params["noise_pct"] * 2.55, array.shape)
        image = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))
        image = image.filter(ImageFilter.GaussianBlur(0.6))
    elif condition == "K3":
        out_w = round(width * params["dpi_x"] / 200)
        out_h = round(height * params["dpi_y"] / 200)
        small = np.asarray(gray.resize((out_w, out_h), Image.Resampling.BILINEAR))
        binary = np.where(small < 255 * params["threshold_pct"] / 100, 0, 255).astype(np.uint8)
        for _ in range(params["dropout_lines"]):
            binary[int(rng.integers(0, out_h)), :] = 255
        for _ in range(params["streaks"]):
            binary[:, int(rng.integers(0, out_w))] = 0
        image = Image.fromarray(binary)
        quad = [
            (0.0, 0.0),
            (float(out_w), 0.0),
            (float(out_w), float(out_h)),
            (0.0, float(out_h)),
        ]
    elif condition == "K4":
        array = np.asarray(gray, dtype=np.float64)
        contrast = params["contrast_pct"] / 100
        array = 255 - (255 - array) * contrast
        speckle = rng.random(array.shape) < params["speckle_pct"] / 100
        array[speckle] = rng.uniform(80, 200, int(speckle.sum()))
        for _ in range(params["toner_streaks"]):
            column = int(rng.integers(0, width))
            array[:, column : column + 2] *= 0.75
        image = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))
        quad = corners
    elif condition == "K5":
        turns = params["quarter_turns"]
        if params["mixed_pages"] and page_number % 2 == 0:
            turns = (turns + 2) % 4  # an upside-down page inside the same upload
        angle = 90.0 * turns + params["fine_tenths_deg"] / 10
        image = gray.rotate(
            angle, resample=Image.Resampling.BILINEAR, expand=True, fillcolor=255
        )
        quad, _ = _rotate_quad(corners, angle, (width, height))
    elif condition == "K6":
        array = np.asarray(gray, dtype=np.float64)
        amplitude = params["curl_pct"] / 100 * height
        cols = np.arange(width, dtype=np.float64) / max(width - 1, 1)
        edge = cols if params["curl_edge"] == "right" else 1 - cols
        shift = (amplitude * edge**3).astype(np.int64)  # bends rows near the spine
        curled = np.full_like(array, 255.0)
        for column in range(width):
            offset = int(shift[column])
            curled[offset:, column] = array[: height - offset, column]
            curled[:offset, column] = 70.0
        theta = np.deg2rad(params["shadow_angle_deg"])
        yy, xx = np.mgrid[0:height, 0:width]
        diagonal = (xx * np.cos(theta) + yy * np.sin(theta)) / (width + height)
        band = (diagonal > 0.35) & (diagonal < 0.62)
        curled[band] *= 1 - params["shadow_pct"] / 100
        curled += rng.normal(0, 3.0, curled.shape)
        image = Image.fromarray(np.clip(curled, 0, 255).astype(np.uint8))
        quad = corners
    elif condition == "K7":
        out_w, out_h = params["viewport_px"]
        status_h, toolbar_h = 140, 220
        scale = out_w / width
        page_h = round(height * scale)
        canvas = Image.new("L", (out_w, out_h), 238)
        crop_top = round(page_h * params["crop_top_pct"] / 100)
        crop_bottom = round(page_h * params["crop_bottom_pct"] / 100)
        scaled = gray.resize((out_w, page_h), Image.Resampling.BILINEAR)
        visible = scaled.crop((0, crop_top, out_w, page_h - crop_bottom))
        top = status_h + toolbar_h
        room = out_h - top - 160
        canvas.paste(visible.crop((0, 0, out_w, min(room, visible.size[1]))), (0, top))
        chrome = fitz.open()
        bar = chrome.new_page(width=out_w * 72 / 300, height=top * 72 / 300)
        decoy = date.fromisoformat(today) + timedelta(days=params["decoy_date_offset_days"])
        bar.insert_text(fitz.Point(10, 14), params["status_time"], fontsize=9)
        bar.insert_text(fitz.Point(170, 14), decoy.strftime("%a %b %d %Y"), fontsize=8)
        bar.insert_text(fitz.Point(10, 44), "< Back      Document.pdf      Share", fontsize=10)
        pixmap = bar.get_pixmap(dpi=300, colorspace=fitz.csGRAY)
        strip = Image.frombytes("L", (pixmap.width, pixmap.height), pixmap.samples)
        canvas.paste(strip.resize((out_w, top), Image.Resampling.BILINEAR), (0, 0))
        image = canvas
        y0 = top - crop_top
        quad = [
            (0.0, float(y0)),
            (float(out_w), float(y0)),
            (float(out_w), float(y0 + page_h)),
            (0.0, float(y0 + page_h)),
        ]
    elif condition == "K8":
        scale = params["dpi"] / 200
        page_w, page_h = round(width * scale), round(height * scale)
        target = gray.resize((page_w, page_h), Image.Resampling.BILINEAR)
        other = _distractor(page_w, page_h, params["distractor_seed"])
        margin = 60
        if params["layout"] == "side_by_side":
            out_w, out_h = 2 * page_w + 3 * margin, page_h + 2 * margin
            canvas = Image.new("L", (out_w, out_h), 90)
            canvas.paste(other, (margin, margin))
            x0, y0 = 2 * margin + page_w, margin
        else:
            shift = round(page_w * params["overlap_pct"] / 100)
            out_w, out_h = page_w + shift + 2 * margin, page_h + shift + 2 * margin
            canvas = Image.new("L", (out_w, out_h), 90)
            canvas.paste(other, (margin, margin))
            x0, y0 = margin + shift, margin + shift
        canvas.paste(target, (x0, y0))
        page_quad = [
            (float(x0), float(y0)),
            (float(x0 + page_w), float(y0)),
            (float(x0 + page_w), float(y0 + page_h)),
            (float(x0), float(y0 + page_h)),
        ]
        angle = params["skew_tenths_deg"] / 10
        image = canvas.rotate(
            angle, resample=Image.Resampling.BILINEAR, expand=True, fillcolor=90
        )
        quad, _ = _rotate_quad(page_quad, angle, (out_w, out_h))
    else:
        raise NotImplementedError(f"capture_condition_not_in_renderer:{condition}")
    return image, [[round(x), round(y)] for x, y in quad]


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=False, compress_level=6)
    return buffer.getvalue()


def render_scenario(scenario: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    seed = scenario["generator"]["seed"]
    files: list[dict[str, Any]] = []
    for upload_id, upload in sorted(scenario["ledgers"]["uploads"].items()):
        target = out_dir / scenario["scenario_id"] / upload_id
        target.mkdir(parents=True, exist_ok=True)
        if upload["media"] == "pdf":
            combined = fitz.open()
            for page_number in range(1, len(upload["pages"]) + 1):
                combined.insert_pdf(_page_pdf(upload, page_number))
            combined.set_metadata({})
            data = combined.tobytes(garbage=4, deflate=True, no_new_id=True)
            path = target / "upload.pdf"
            path.write_bytes(data)
            files.append(
                {
                    "upload_id": upload_id,
                    "page": None,
                    "media": "pdf",
                    "path": str(path.relative_to(out_dir)),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
            continue
        dpi = 200
        for page_number in range(1, len(upload["pages"]) + 1):
            pixmap = _page_pdf(upload, page_number)[0].get_pixmap(
                dpi=dpi, colorspace=fitz.csGRAY
            )
            gray = Image.frombytes("L", (pixmap.width, pixmap.height), pixmap.samples)
            image, quad = _degrade(
                gray,
                upload["capture"],
                _rng(seed, upload_id, page_number),
                page_number,
                scenario["ledgers"]["clock"]["today"],
            )
            data = _png(image)
            path = target / f"p{page_number}.png"
            path.write_bytes(data)
            files.append(
                {
                    "upload_id": upload_id,
                    "page": page_number,
                    "media": "image",
                    "path": str(path.relative_to(out_dir)),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "width_px": image.size[0],
                    "height_px": image.size[1],
                    "source_dpi": dpi,
                    "quad_px": quad,
                    "quad_exact": upload["capture"]["condition"] != "K6",
                }
            )
    import PIL

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "scenario_id": scenario["scenario_id"],
        "scenario_sha256": digest(scenario),
        "renderer": {
            "pymupdf": fitz.VersionBind,
            "numpy": np.__version__,
            "pillow": PIL.__version__,
        },
        "handwriting_source": "font_placeholder_not_valid_for_test",
        "files": files,
    }
    return {**manifest, "manifest_sha256": digest(manifest)}
