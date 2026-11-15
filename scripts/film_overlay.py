"""On-screen graphics of the product film: feature labels and the real-footage tag.

Rendered once as transparent PNGs in the end card's palette (scripts/film_endcard.py),
then faded in and out over the picture by ffmpeg.
"""
from pathlib import Path
import hashlib, json

from PIL import Image, ImageDraw, ImageFont

from film_endcard import CREAM, FONT, GOLD

SCALE = 3  # supersampled, then reduced for smooth edges
PANEL = (14, 21, 16, 214)
EDGE = (228, 205, 141, 120)


def _font(size: int, weight: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(FONT), size * SCALE)
    try:
        font.set_variation_by_axes([weight])
    except (OSError, AttributeError):  # static font: keep its single weight
        pass
    return font


def _pill(size: tuple, radius: int) -> tuple:
    w, h = size
    image = Image.new('RGBA', (w * SCALE, h * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, w * SCALE - 1, h * SCALE - 1), radius * SCALE, fill=PANEL, outline=EDGE, width=2 * SCALE)
    return image, draw


def feature_label(number: str, title: str, detail: str, target: Path) -> Path:
    """'01 | 무엇이든 물어보기 / 엣지 AI가 차 안에서 답해요' as a top-left card."""
    big, small, tag = _font(40, 700), _font(25, 500), _font(24, 700)
    probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    text_w = max(probe.textlength(title, font=big), probe.textlength(detail, font=small)) / SCALE
    w, h = int(132 + text_w + 44), 124
    image, draw = _pill((w, h), 26)
    cx, cy, r = 62 * SCALE, h * SCALE // 2, 34 * SCALE
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GOLD + (255,))
    draw.text((cx, cy), number, font=tag, fill=(20, 28, 22, 255), anchor='mm')
    draw.text((118 * SCALE, 20 * SCALE), title, font=big, fill=CREAM + (255,))
    draw.text((118 * SCALE, 74 * SCALE), detail, font=small, fill=GOLD + (235,))
    image.resize((w, h), Image.LANCZOS).save(target)
    return target


def footage_tag(text: str, target: Path) -> Path:
    """Small top-right marker that the picture is the real app, not generated."""
    font = _font(24, 600)
    probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    w, h = int(probe.textlength(text, font=font) / SCALE + 64), 52
    image, draw = _pill((w, h), 26)
    draw.ellipse((22 * SCALE, 20 * SCALE, 34 * SCALE, 32 * SCALE), fill=(232, 96, 82, 255))
    draw.text((44 * SCALE, h * SCALE // 2), text, font=font, fill=CREAM + (255,), anchor='lm')
    image.resize((w, h), Image.LANCZOS).save(target)
    return target


def render_all(labels: list, tag: str, folder: Path) -> dict:
    """Cached by content: {label index or 'tag': png path}."""
    folder.mkdir(parents=True, exist_ok=True)
    stamp = hashlib.sha256((Path(__file__).read_bytes() + FONT.read_bytes()[:4096])).hexdigest()[:8]
    made = {}
    for index, label in enumerate(labels):
        key = hashlib.sha256(json.dumps([label['number'], label['title'], label['detail'], stamp], ensure_ascii=False).encode()).hexdigest()[:12]
        target = folder / f'label-{key}.png'
        made[index] = target if target.is_file() else feature_label(label['number'], label['title'], label['detail'], target)
    key = hashlib.sha256(json.dumps([tag, stamp], ensure_ascii=False).encode()).hexdigest()[:12]
    target = folder / f'tag-{key}.png'
    made['tag'] = target if target.is_file() else footage_tag(tag, target)
    return made
