"""Animated end card built from the app's own Pli mark (res/drawable/ic_pli.xml)."""
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
MARK = ROOT / 'android/app/src/main/res/drawable/ic_pli.xml'
FONT = ROOT / 'android/app/src/main/res/font/pretendard.ttf'
ANDROID = '{http://schemas.android.com/apk/res/android}'
BG_CENTER, BG_EDGE = np.array([47, 61, 48]), np.array([24, 32, 26])
CREAM, GOLD, STAR = (240, 240, 229), (228, 205, 141), (246, 212, 123)
SUPERSAMPLE = 3
MARK_SIZE, GAP = 250, 56


def _bezier(points: list, steps: int = 24) -> list:
    t = np.linspace(0, 1, steps)[:, None]
    p = np.array(points, dtype=float)
    if len(p) == 3:
        curve = (1 - t) ** 2 * p[0] + 2 * (1 - t) * t * p[1] + t ** 2 * p[2]
    else:
        curve = (1 - t) ** 3 * p[0] + 3 * (1 - t) ** 2 * t * p[1] + 3 * (1 - t) * t ** 2 * p[2] + t ** 3 * p[3]
    return [tuple(xy) for xy in curve[1:]]


def parse_path(data: str) -> list:
    """Absolute M/C/Q/V/H/Z path data → list of polylines (the subset ic_pli uses)."""
    tokens = re.findall(r'[MCQVHZ]|-?\d+(?:\.\d+)?', data)
    lines, current, pos, i, command = [], [], (0.0, 0.0), 0, None
    while i < len(tokens):
        if tokens[i].isalpha():
            command, i = tokens[i], i + 1
            if command == 'Z' and current:
                current.append(current[0])
            continue
        if command == 'M':
            if current:
                lines.append(current)
            pos = (float(tokens[i]), float(tokens[i + 1]))
            current, i = [pos], i + 2
        elif command in ('C', 'Q'):
            n = 6 if command == 'C' else 4
            values = [float(v) for v in tokens[i:i + n]]
            ctrl = [pos] + [tuple(values[k:k + 2]) for k in range(0, n, 2)]
            current += _bezier(ctrl)
            pos, i = ctrl[-1], i + n
        elif command == 'V':
            pos = (pos[0], float(tokens[i]))
            current.append(pos)
            i += 1
        elif command == 'H':
            pos = (float(tokens[i]), pos[1])
            current.append(pos)
            i += 1
        else:
            raise ValueError('Unsupported path command: ' + str(command))
    if current:
        lines.append(current)
    return lines


def load_mark() -> dict:
    paths = ET.parse(MARK).getroot().findall('path')
    body = next(p for p in paths if p.get(ANDROID + 'fillColor') == '#F6D47B')
    face = next(p for p in paths if p.get(ANDROID + 'strokeColor'))
    return {'body': parse_path(body.get(ANDROID + 'pathData')), 'face': parse_path(face.get(ANDROID + 'pathData')),
            'faceColor': face.get(ANDROID + 'strokeColor'), 'faceWidth': float(face.get(ANDROID + 'strokeWidth'))}


def ease_out(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_back(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 + 2.4 * (x - 1) ** 3 + 1.4 * (x - 1) ** 2


def background(width: int, height: int) -> Image.Image:
    yy, xx = np.mgrid[0:height, 0:width]
    r = np.sqrt(((xx - width * 0.5) / width) ** 2 + ((yy - height * 0.46) / height) ** 2) * 1.6
    mix = np.clip(r, 0, 1)[..., None]
    return Image.fromarray((BG_CENTER * (1 - mix) + BG_EDGE * mix).astype('uint8'))


def draw_mark(mark: dict, size: int, blink: float) -> Image.Image:
    """Render the mark at `size` px (supersampled); blink 0..1 squashes the eyes."""
    s = size * SUPERSAMPLE
    image = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    scale = s / 64
    for line in mark['body']:
        draw.polygon([(x * scale, y * scale) for x, y in line], fill=STAR + (255,))
    width = max(1, int(mark['faceWidth'] * scale))
    color = tuple(int(mark['faceColor'][k:k + 2], 16) for k in (1, 3, 5)) + (255,)
    for line in mark['face']:
        points = [(x * scale, y * scale) for x, y in line]
        if len(points) == 2:  # eyes are vertical strokes; squash them while blinking
            (x0, y0), (x1, y1) = points
            mid, half = (y0 + y1) / 2, abs(y1 - y0) / 2 * (1 - 0.85 * blink)
            points = [(x0, mid - half), (x1, mid + half)]
        draw.line(points, fill=color, width=width, joint='curve')
        for x, y in (points[0], points[-1]):  # round caps
            draw.ellipse([x - width / 2, y - width / 2, x + width / 2, y + width / 2], fill=color)
    return image.resize((size, size), Image.LANCZOS)


def font(size: int, weight: str) -> ImageFont.FreeTypeFont:
    face = ImageFont.truetype(str(FONT), size)
    face.set_variation_by_name(weight)
    return face


def text_layer(canvas: Image.Image, xy: tuple, text: str, face: ImageFont.FreeTypeFont, fill: tuple,
               progress: float, rise: int = 28) -> None:
    alpha = int(255 * ease_out(progress))
    if alpha <= 0:
        return
    layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((xy[0], xy[1] + rise * (1 - ease_out(progress))), text, font=face, fill=fill + (alpha,))
    canvas.alpha_composite(layer)


def frame(t: float, spec: dict, mark: dict, base: Image.Image, fonts: dict) -> Image.Image:
    width, height = base.size
    canvas = base.convert('RGBA')
    grow = ease_back((t - 0.1) / 0.75)
    size = max(1, int(MARK_SIZE * (0.55 + 0.45 * grow)))
    blink = max(0.0, 1 - abs(t - spec['blinkAt']) / 0.09) if spec.get('blinkAt') else 0.0
    text_w = max(fonts['brand'].getbbox(spec['brand'])[2], fonts['copy'].getbbox(spec['copy'])[2])
    left = (width - (MARK_SIZE + GAP + text_w)) // 2
    cx, cy = left + MARK_SIZE // 2, height // 2 - 10
    if t > 0.1:
        glow = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        radius = int(size * 0.62)
        ImageDraw.Draw(glow).ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                                     fill=STAR + (int(70 * ease_out(t / 1.2)),))
        canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(70)))
        icon = draw_mark(mark, size, blink)
        fade = ease_out((t - 0.1) / 0.4)
        icon.putalpha(icon.getchannel('A').point(lambda a: int(a * fade)))
        canvas.alpha_composite(icon, (cx - size // 2, cy - size // 2))
    text_x = left + MARK_SIZE + GAP
    text_layer(canvas, (text_x, cy - 150), spec['brand'], fonts['brand'], CREAM, (t - 0.45) / 0.6)
    text_layer(canvas, (text_x + 6, cy + 52), spec['copy'], fonts['copy'], CREAM, (t - 0.8) / 0.6)
    text_layer(canvas, (text_x + 8, cy + 122), spec['platform'], fonts['platform'], GOLD, (t - 1.15) / 0.6, rise=16)
    return canvas.convert('RGB')


def render(spec: dict, output: Path, width: int, height: int, fps: int) -> Path:
    """Encode the end card to `output` (H.264, yuv420p) and return it."""
    mark, base = load_mark(), background(width, height)
    fonts = {'brand': font(176, 'Bold'), 'copy': font(50, 'Medium'), 'platform': font(36, 'SemiBold')}
    rng = np.random.default_rng(17)
    encoder = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                                '-s', f'{width}x{height}', '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', 'slow',
                                '-crf', '14', '-pix_fmt', 'yuv420p', str(output)], stdin=subprocess.PIPE)
    try:
        for index in range(round(spec['seconds'] * fps)):
            pixels = np.asarray(frame(index / fps, spec, mark, base, fonts)).astype(np.int16)
            grain = rng.normal(0, 2.2, pixels.shape[:2])[..., None]
            encoder.stdin.write(np.clip(pixels + grain, 0, 255).astype('uint8').tobytes())
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError('End card encode failed')
    return output
