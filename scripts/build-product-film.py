#!/usr/bin/env python3
"""Assemble the Pli product film: generated family scenes + real app takes.

Sound is recorded, not re-voiced: family scenes keep the speech generated with their picture
(Figma Weave, Seedance 2.5 since v6), and feature scenes use Pli's own voice: the sentences the edge
voice server synthesized, placed where the app played them (scripts/film_clean_voice.py).

v6 (2026-11-14 audit fixes): generated clips are used at their own 1080p size and frame rate converted
by repeating frames (no motion interpolation, no crop-and-upscale); every line is levelled with a
measured linear gain to one target (no per-line dynamic loudnorm); no synthesized music or fake road
noise; captions carry what was actually said and sit above the Pleos dock on app cuts.

Family scenes are generated moving footage whose recorded provenance must match
media/pli-film/production.json; feature scenes are real recordings of the public
Pli APK (scripts/record-film-features.py) whose logs must exist. Stills are never
substituted. Captions are burned in for every line; feature labels name what the
app is doing. `--stage-portal` copies a reviewed render into demo-v2 with its
captions, transcript and identity.
"""
from pathlib import Path
from fractions import Fraction
import argparse, asyncio, hashlib, json, os, runpy, shutil, subprocess, time

import numpy as np

import film_audio
import film_endcard
import film_overlay
import film_voice

ROOT = Path(__file__).resolve().parents[1]
# v10: PLI_FILM_VARIANT=landscape builds the 1920x1080 version from its own plan into its own work folder and master
VARIANT = os.environ.get('PLI_FILM_VARIANT', 'vertical')
SUFFIX = '' if VARIANT == 'vertical' else f'-{VARIANT}'
PLAN = ROOT / f'media/pli-film/production{SUFFIX}.json'
WORK = ROOT / f'.tools/product-film/new-cut{SUFFIX}'
MASTER = ROOT / f'artifacts/pli-product-film{SUFFIX}.mp4'
FONTS = ROOT / 'android/app/src/main/res/font'
LOOKS = {'before': 'eq=saturation=0.86:contrast=1.03,colorbalance=rs=-0.02:bs=0.04:bm=0.02',
         'after': 'eq=saturation=1.05:contrast=1.02,colorbalance=rs=0.03:rm=0.02:bs=-0.03',
         # a sunlit afternoon scene brought to the story's 17:30 November dusk (after sunset), like the other car scenes
         'dusk': "eq=gamma=0.86:saturation=0.86:contrast=1.05,colorbalance=rs=-0.02:gs=-0.02:bs=0.03:rm=-0.01:bm=0.01:rh=-0.05:gh=-0.03:bh=0.0,"
                 "curves=all='0/0 0.55/0.42 1/0.74'"}
GENERATOR = runpy.run_path(str(ROOT / 'scripts/generate-film-clips.py'))
TAKES = ROOT / '.tools/product-film/app-takes'
WEAVE = ROOT / '.tools/product-film/weave'
VERTICAL = ROOT / '.tools/product-film/vertical'  # v8 family scenes made 9:16 on Hugging Face (scripts/make-vertical-scenes.py)
VOICE_LUFS = -20.0   # every spoken line, family and Pli alike
FILM_LUFS = -16.0
SPEAKER_COLOURS = {'플리': '&H008DCDE4', '하연': '&H00F5F4EE', '엄마': '&H00D9E8EE'}  # ASS BGR


def run(args: list) -> None:
    done = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if done.returncode != 0:  # show why ffmpeg refused, not just that it did
        raise SystemExit(f'{args[0]} failed ({done.returncode}): {done.stderr.strip()[-1500:]}')


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def probe_duration(path: Path) -> float:
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                          '-of', 'csv=p=0', str(path)]).strip())


def timeline(plan: dict) -> tuple:
    """Start time and length of every cut and the end card, after transitions overlap."""
    cuts, at, fps = [], 0.0, plan['format']['fps']
    for cut in plan['edit']:
        overlap = cut.get('transition', {}).get('seconds', 0.0)
        length = round(round((cut['out'] - cut['in']) / cut['speed'] * fps) / fps, 4)  # whole frames
        at = round(at - overlap, 3)
        cuts.append({**cut, 'start': at, 'length': length})
        at = round(at + length, 3)
    card = plan['endCard']
    start = round(at - card.get('transition', {}).get('seconds', 0.0), 3)
    return cuts, {**card, 'start': start}, round(start + card['seconds'], 3)


def take_record(take: str) -> dict:
    return json.loads((TAKES / f'{take}.json').read_text())


def validate(plan: dict) -> list:
    problems = []
    shots = {shot['id']: shot for shot in plan['shots']}
    for cut in plan['edit']:
        if 'weave' in cut or 'vertical' in cut:
            name, folder = (cut['weave'], WEAVE) if 'weave' in cut else (cut['vertical'], ROOT / cut['folder'] if cut.get('folder') else VERTICAL)
            clip, record = folder / cut.get('clip', f"{name}.mp4"), folder / f"{name}.json"
            if not clip.is_file() or not record.is_file():
                problems.append(name + ': generated clip or its provenance record missing')
                continue
            if cut['out'] > probe_duration(clip) + 1e-6:
                problems.append(name + f": out point {cut['out']}s beyond the clip")
            continue
        if 'app' in cut:
            clip, log = TAKES / f"{cut['app']}.mp4", TAKES / f"{cut['app']}.json"
            if not clip.is_file() or not log.is_file():
                problems.append(cut['app'] + ': real app take missing (scripts/record-film-features.py)')
                continue
            record = take_record(cut['app'])
            if record.get('profile') != 'public':
                problems.append(cut['app'] + ': app takes must come from the public profile')
            if cut['out'] > float(record['video']['format']['duration']) + 1e-6:
                problems.append(cut['app'] + f": out point {cut['out']}s beyond the take")
            continue
        shot = shots.get(cut['shot'])
        if shot is None:
            problems.append(cut['shot'] + ': not a declared generated shot')
            continue
        if not GENERATOR['is_current'](plan, shot):
            problems.append(cut['shot'] + ': generated clip missing or does not match the plan')
            continue
        stream = json.loads(GENERATOR['provenance_path'](shot).read_text())['video']['streams'][0]
        frames, rate = int(stream['nb_frames']), float(Fraction(stream['r_frame_rate']))  # (v5 LTX shots)
        if stream['codec_name'] in {'png', 'mjpeg', 'gif', 'webp'} or frames < 8:
            problems.append(cut['shot'] + ': source must be moving video')
        if cut['out'] > frames / rate + 1e-6:
            problems.append(cut['shot'] + f': out point {cut["out"]}s beyond {frames / rate:.2f}s of footage')
    total = timeline(plan)[2]
    if abs(total - plan['format']['durationSeconds']) > 0.05:
        problems.append(f'edit lasts {total}s but plan declares {plan["format"]["durationSeconds"]}s')
    if not 30 <= total <= 60:
        problems.append(f'film must be 30-60s, edit is {total}s')
    return problems


def source_seconds(shot: dict) -> float:
    stream = json.loads(GENERATOR['provenance_path'](shot).read_text())['video']['streams'][0]
    return int(stream['nb_frames']) / float(Fraction(stream['r_frame_rate']))


def cut_chain(cut: dict, available: float, fmt: dict, frame: dict) -> str:
    """Filter chain of one cut. Generated 16 fps clips are motion-interpolated and graded;
    real app takes (30 fps gRPC grabs of the 2560x1440 display, film_grab.py) keep their pixels:
    the app panel is framed, and the profile chip that names the real child is removed."""
    width, height, fps = fmt['width'], fmt['height'], fmt['fps']
    tail = min(cut['out'] + 0.15, available)
    timing = f"trim=start={cut['in']}:end={tail},setpts=(PTS-STARTPTS)/{cut['speed']},"
    if 'app' in cut:
        removed = ''.join(f'delogo=x={rx}:y={ry}:w={rw}:h={rh},' for rx, ry, rw, rh in cut.get('remove', []))
        if frame.get('mode') == 'closeup':  # v8: the whole display first, then a tall close-up of Pli's card filling the picture area
            sw, sh = frame['stream']
            band_h = round(width * sh / sw / 2) * 2
            x, y, w, h = cut.get('region') or frame['region']  # display pixels of the close-up
            centred = frame['closeY'] == 'center'  # v9: the close-up in the middle of the app area
            margin = frame.get('closeMargin', 0)  # v9: a floating card with the cabin showing at its sides
            close_w = width - 2 * margin
            close_h = min(frame['areaHeight'] - (0 if centred else 2 * frame['closeY']), round(close_w * h / w / 2) * 2)
            close_y = (frame['areaHeight'] - close_h) // 2 if centred else frame['closeY']
            switch = cut.get('closeAt', frame.get('closeAt', 1.0))
            backdrop, mask_full = band_assets({**frame, 'bandY': frame['fullY']}, width, height)
            mask_close = rounded_mask(close_w, close_h)
            return (timing + f"fps={fps},{removed}split=2[b][c];movie={backdrop},loop=loop=-1:size=1,fps={fps},format=yuv420p[bg];"
                    f"movie={mask_full},loop=loop=-1:size=1,fps={fps},format=gray[m1];movie={mask_close},loop=loop=-1:size=1,fps={fps},format=gray[m2];"
                    f"[b]scale={width}:{band_h}:flags=lanczos,format=yuva420p[f1o];[f1o][m1]alphamerge[f1];"
                    f"[c]crop={w}:{h}:{x}:{y},scale={close_w}:{close_h}:flags=lanczos,format=yuva420p[f2o];[f2o][m2]alphamerge[f2];"
                    f"[bg][f1]overlay=0:{frame['fullY']}:shortest=1:enable='lt(t,{switch})'[o1];"
                    f"[o1][f2]overlay={margin}:{close_y}:shortest=1:enable='gte(t,{switch})',tpad=stop_mode=clone:stop=4,setsar=1,format=yuv420p")
        if frame.get('mode') == 'band':  # vertical film: the whole display as a band over a blurred, darkened copy of itself
            sw, sh = frame['stream']
            band_h = round(width * sh / sw / 2) * 2

            def window(zoom: float, cx: float, cy: float) -> str:  # part of the display, never past the stream's own pixels
                cw, ch = round(sw / zoom / 2) * 2, round(sh / zoom / 2) * 2
                x0 = min(max(0, round(cx * sw - cw / 2)), sw - cw)
                y0 = min(max(0, round(cy * sh - ch / 2)), sh - ch)
                return f"crop={cw}:{ch}:{x0}:{y0},scale={width}:{band_h}:flags=lanczos"
            whole = window(cut.get('zoom', 1.0), cut.get('cx', 0.5), cut.get('cy', 0.5))
            punch = cut.get('punchIn')  # the whole screen first, then a closer look at Pli's card from `at` seconds into the cut
            closer = window(punch['zoom'], punch['cx'], punch['cy']) if punch else whole
            switch = punch['at'] if punch else 1e9
            if frame.get('background'):  # the evening cabin behind the car's screen, the band with rounded corners
                backdrop, mask = band_assets(frame, width, height)
                return (timing + f"fps={fps},{removed}split=2[b][c];movie={backdrop},loop=loop=-1:size=1,fps={fps},format=yuv420p[bg];"
                        f"movie={mask},loop=loop=-1:size=1,fps={fps},format=gray,split=2[m1][m2];"
                        f"[b]{whole},format=yuva420p[f1o];[f1o][m1]alphamerge[f1];[c]{closer},format=yuva420p[f2o];[f2o][m2]alphamerge[f2];"
                        f"[bg][f1]overlay=0:{frame['bandY']}:shortest=1:enable='lt(t,{switch})'[o1];"
                        f"[o1][f2]overlay=0:{frame['bandY']}:shortest=1:enable='gte(t,{switch})',tpad=stop_mode=clone:stop=4,setsar=1,format=yuv420p")
            base = (timing + f"fps={fps},{removed}split=3[a][b][c];[a]scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height},boxblur=30:2,eq=brightness=-0.24:saturation=0.8[bg];")
            return (base + f"[b]{whole}[f1];[c]{closer}[f2];[bg][f1]overlay=0:{frame['bandY']}:enable='lt(t,{switch})'[o1];"
                    f"[o1][f2]overlay=0:{frame['bandY']}:enable='gte(t,{switch})',tpad=stop_mode=clone:stop=4,setsar=1,format=yuv420p")
        if cut.get('frame') == 'fit':  # the whole window (album photos and captions), over a blurred copy of itself
            return (timing + f"fps={fps},{removed}split[a][b];[a]scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height},boxblur=28:2,eq=brightness=-0.14[bg];[b]scale=-2:{height}:flags=lanczos[fg];"
                    f"[bg][fg]overlay=(W-w)/2:0,tpad=stop_mode=clone:stop=4,setsar=1,format=yuv420p")
        x, y, w, h = cut.get('crop') or frame['crop']
        return (timing + f"fps={fps},{removed}crop={w}:{h}:{x}:{y},scale={width}:{height}:flags=lanczos,"
                f"unsharp=3:3:0.35,tpad=stop_mode=clone:stop=4,setsar=1,format=yuv420p")
    if 'vertical' in cut:  # 24 fps, made 9:16, frames repeated to 30 fps
        shift = cut.get('shiftY', 0)  # move the picture up
        # v8 clips are 704x1248 (scaled 1.54x, sharpened); v9 clips are already 1080x1920 (Real-ESRGAN), no extra sharpening
        sharpen = '' if cut.get('clip') else 'unsharp=5:5:0.4,'
        grade = cut['grade'] + ',' if cut.get('grade') else ''  # v9: per-scene night colour match (plan-product-film.py night_grade)
        tall = round(height * cut.get('zoom', 1.0) / 2) * 2  # v9: a closer framing anchored at the top (newcar: the caption box band)
        return (timing + f"fps={fps},scale=-2:{tall}:flags=lanczos,pad=iw:ih+{shift}:0:0:black,crop={width}:{height}:(iw-{width})/2:{shift},{sharpen}"
                f"{LOOKS[cut.get('look', 'after')]},{grade}tpad=stop_mode=clone:stop=4,setsar=1,format=yuv420p")
    if 'weave' in cut:  # 1080p, 24 fps: frames are repeated to 30 fps, never invented (no minterpolate warping)
        x, y, w, h = cut.get('crop') or (0, 0, 1920, 1080)  # the vertical film takes a 9:16 window of the 16:9 scene
        sharpen = 'unsharp=5:5:0.5,' if w < width else ''
        return (timing + f"fps={fps},crop={w}:{h}:{x}:{y},scale={width}:{height}:flags=lanczos,{LOOKS[cut['look']]},{sharpen}"
                f"tpad=stop_mode=clone:stop=4,setsar=1,format=yuv420p")
    zoom = cut.get('zoom', 1.0)  # keep the top of the frame: the video model sometimes draws text at the bottom
    keep = f"crop=iw*{zoom}:ih*{zoom}:(iw-iw*{zoom})/2:0," if zoom != 1.0 else ''
    return (timing + f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,{keep}"
            f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height},{LOOKS[cut['look']]},"
            f"unsharp=5:5:0.45,noise=alls=3:allf=t,vignette=angle=0.32,tpad=stop_mode=clone:stop=4,format=yuv420p")


def band_assets(frame: dict, width: int, height: int) -> tuple:
    """The vertical film's app backdrop (a blurred, darkened still of the evening cabin, with the band's shadow baked in)
    and the band's rounded-corner mask, made once and cached by their inputs."""
    from PIL import Image, ImageDraw, ImageFilter
    band_h = round(width * frame['stream'][1] / frame['stream'][0] / 2) * 2
    spec = frame['background']
    source = sha(ROOT / spec['image']) if spec.get('image') else None
    key = hashlib.sha256(json.dumps([spec, width, height, band_h, frame['bandY'], source]).encode()).hexdigest()[:12]
    backdrop, mask = WORK / f'band-backdrop-{key}.png', WORK / f'band-mask-{key}.png'
    if spec.get('style') == 'night' and (not backdrop.is_file() or not mask.is_file()):
        night_backdrop(spec, width, height, frame['bandY'], band_h).save(backdrop)
        edge = Image.new('L', (width, band_h), 0)
        ImageDraw.Draw(edge).rounded_rectangle((0, 0, width - 1, band_h - 1), 28, fill=255)
        edge.save(mask)
    if not backdrop.is_file() or not mask.is_file():
        x, y, w, h = spec['crop']
        still = Image.open(ROOT / spec['image']).convert('RGB').crop((x, y, x + w, y + h)).resize((width, height), Image.LANCZOS)
        still = still.filter(ImageFilter.GaussianBlur(36))
        knee = spec.get('knee')  # v9: soft-limit bright spots (the blurred mascot on the cabin's own display) so they don't glow
        still = Image.eval(still, (lambda v: int(min(v * 0.62, knee + max(0.0, v * 0.62 - knee) * 0.3))) if knee else (lambda v: int(v * 0.62)))
        if spec.get('lowerShade'):  # v9: no caption panel any more, so the lower part of the backdrop is darkened instead
            ramp = np.clip((np.arange(height) / height - 0.45) / 0.3, 0, 1)
            shade = (1 - (1 - spec['lowerShade']) * ramp)[:, None, None]
            still = Image.fromarray((np.asarray(still, dtype='float32') * shade).astype('uint8'))
        shadow = Image.new('L', (width, height), 0)
        ImageDraw.Draw(shadow).rounded_rectangle((24, frame['bandY'] + 18, width - 24, frame['bandY'] + band_h + 30), 36, fill=170)
        shadow = shadow.filter(ImageFilter.GaussianBlur(26))
        backdrop_image = Image.composite(Image.new('RGB', (width, height), (4, 6, 8)), still, shadow)
        backdrop_image.save(backdrop)
        edge = Image.new('L', (width, band_h), 0)
        ImageDraw.Draw(edge).rounded_rectangle((0, 0, width - 1, band_h - 1), 28, fill=255)
        edge.save(mask)
    return backdrop, mask


def night_backdrop(spec: dict, width: int, height: int, band_y: int, band_h: int):
    """v10 (user: "뒷배경 같은게 이상하잖아"): behind the car's screen a clean night gradient in the app's own colours, a soft
    glow behind the card and fine grain against banding, instead of v9's blurred cabin photo (brown blobs under the card)."""
    from PIL import Image, ImageDraw, ImageFilter
    top, bottom = np.array(spec.get('top', (13, 17, 32)), 'float32'), np.array(spec.get('bottom', (4, 5, 9)), 'float32')
    ramp = np.linspace(0, 1, height, dtype='float32')[:, None, None] ** 0.8
    image = np.broadcast_to(top * (1 - ramp) + bottom * ramp, (height, width, 3)).copy()
    yy, xx = np.mgrid[0:height, 0:width].astype('float32')
    cy = band_y + band_h / 2
    for (gx, gy, rx, ry, colour, alpha) in ((0.5, cy / height, 0.62, 0.20, (52, 82, 150), 0.42),    # blue behind the card
                                            (0.78, 0.62, 0.45, 0.16, (88, 56, 128), 0.20)):          # violet below, as the app's aurora
        d = ((xx / width - gx) / rx) ** 2 + ((yy / height - gy) / ry) ** 2
        weight = (alpha * np.exp(-d * 1.6))[..., None]
        image = image * (1 - weight) + np.array(colour, 'float32') * weight
    image += np.random.default_rng(10).normal(0, 1.4, image.shape).astype('float32')  # grain, so the gradient never bands
    picture = Image.fromarray(np.clip(image, 0, 255).astype('uint8'))
    shadow = Image.new('L', (width, height), 0)
    ImageDraw.Draw(shadow).rounded_rectangle((24, band_y + 18, width - 24, band_y + band_h + 30), 36, fill=150)
    shadow = shadow.filter(ImageFilter.GaussianBlur(26))
    return Image.composite(Image.new('RGB', (width, height), (3, 4, 7)), picture, shadow)


def rounded_mask(width: int, height: int, radius: int = 28) -> Path:
    from PIL import Image, ImageDraw
    target = WORK / f'mask-{width}x{height}-{radius}.png'
    if not target.is_file():
        edge = Image.new('L', (width, height), 0)
        ImageDraw.Draw(edge).rounded_rectangle((0, 0, width - 1, height - 1), radius, fill=255)
        edge.save(target)
    return target


def caption_panel(width: int, height: int, top: int) -> Path:
    """v8: a dark panel under the picture area for captions, labels and notes; it also covers the strip where the
    video model draws its own garbled captions (always below 65% of the frame in the 2026-11-14 clips)."""
    from PIL import Image
    target = WORK / f'panel-{width}x{height}-{top}-solid.png'
    if not target.is_file():
        ramp = 90
        alpha = np.zeros(height, dtype='float32')
        alpha[top - ramp:top] = np.linspace(0, 1.0, ramp)
        alpha[top:] = 1.0  # solid: at 0.97 the model's own captions still showed faintly through it
        rgba = np.zeros((height, width, 4), dtype='uint8')
        rgba[..., :3] = (10, 12, 14)
        rgba[..., 3] = (alpha * 255).astype('uint8')[:, None]
        Image.fromarray(rgba, 'RGBA').save(target)
    return target


def caption_gradient(width: int, height: int, top: int) -> Path:
    """v9: the family scenes fill the frame; from `top` down a soft dark gradient (eased, up to 78%) keeps the captions,
    notes and tag legible over the picture without a hard panel edge."""
    from PIL import Image
    target = WORK / f'gradient-{width}x{height}-{top}.png'
    if not target.is_file():
        alpha = np.zeros(height, dtype='float32')
        ramp = np.linspace(0, 1, height - top)
        alpha[top:] = 0.78 * (3 * ramp ** 2 - 2 * ramp ** 3).clip(0, 1) ** 0.8
        rgba = np.zeros((height, width, 4), dtype='uint8')
        rgba[..., :3] = (8, 10, 12)
        rgba[..., 3] = (alpha * 255).astype('uint8')[:, None]
        Image.fromarray(rgba, 'RGBA').save(target)
    return target


def render_cut(cut: dict, source: Path, available: float, output: Path, fmt: dict, frame: dict) -> Path:
    """Trim, retime and frame one cut to an exact frame count, so cut lengths (and every
    dialogue cue after them) never drift. Interpolation needs the source frame after the
    out point, so the trim keeps up to 0.15 s of tail."""
    frames = round(cut['length'] * fmt['fps'])
    chain = cut_chain(cut, available, fmt, frame)
    key = hashlib.sha256(json.dumps([chain, frames, sha(source)]).encode()).hexdigest()[:12]
    output = output.with_name(output.stem + '-' + key + '.mp4')
    if not output.is_file():
        partial = output.with_suffix('.part.mp4')
        run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source), '-an', '-vf', chain,
             '-frames:v', str(frames), '-r', str(fmt['fps']), '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', str(partial)])
        partial.replace(output)
    counted = int(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                                           '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', str(output)]))
    if counted != frames:
        raise SystemExit(f'{output.name}: {counted} frames, edit needs {frames}')
    return output


def compose_video(plan: dict, cuts: list, card: dict, clips: list, output: Path) -> None:
    """Hard cuts by default; xfade where a cut or the end card declares a transition."""
    inputs, graph, label, length = [], [], '[n0]', cuts[0]['length']
    for index, path in enumerate(clips):  # xfade needs one shared timebase on both inputs
        inputs += ['-i', str(path)]
        graph.append(f'[{index}:v]settb=AVTB,setpts=PTS-STARTPTS,setsar=1[n{index}]')  # app cuts arrive with a rounded SAR
    for index, item in enumerate(cuts[1:] + [card], start=1):
        nxt, out = f'[n{index}]', f'[v{index}]'
        transition = item.get('transition')
        item_length = item.get('length', item.get('seconds'))
        if transition:
            offset = round(length - transition['seconds'], 3)
            graph.append(f"{label}{nxt}xfade=transition={transition['type']}:duration={transition['seconds']}:offset={offset}{out}")
            length = round(offset + item_length, 3)
        else:
            graph.append(f'{label}{nxt}concat=n=2:v=1:a=0{out}')
            length = round(length + item_length, 3)
        label = out
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *inputs, '-filter_complex', ';'.join(graph),
         '-map', label, '-r', str(plan['format']['fps']), '-c:v', 'libx264', '-preset', 'medium', '-crf', '14',
         '-pix_fmt', 'yuv420p', str(output)])


def sounding(plan: dict) -> list:
    """Dialogue entries that carry sound; caption-only entries just time a caption."""
    return [line for line in plan['dialogue'] if not line.get('captionOnly')]


def loudness(path: Path, extra: list | None = None) -> float:
    """Integrated loudness (LUFS) by ffmpeg's EBU R128 meter."""
    done = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', *(extra or []), '-i', str(path), '-vn', '-af', 'ebur128=framelog=quiet',
                           '-f', 'null', '-'], capture_output=True, text=True)
    found = [line for line in done.stderr.splitlines() if line.strip().startswith('I:')]
    return float(found[-1].split()[1]) if found else -70.0


def recorded_voice(line: dict) -> Path:
    """A line's real sound: a span of a generated scene (picture and voice from one model) or of
    Pli's original voice in an app take, brought to VOICE_LUFS by one measured linear gain."""
    audio = line['audio']
    source = ROOT / audio['source']
    # v10: the denoiser runs at 44.1 kHz. The landscape scenes carry the 48 kHz voice input itself (the vertical ones the
    # model's 44.1 kHz AAC of it); on that afftdn left the hiss between words 10 dB higher (-37 vs -49 dBFS at the cut)
    denoise = f"aresample=44100,{audio['denoise']}" if audio.get('denoise') else None
    key = hashlib.sha256(json.dumps([sha(source), audio['from'], audio['to'], VOICE_LUFS, 'linear', audio.get('eq'), denoise, 40,
                                     audio.get('gate'), audio.get('fadeIn'), audio.get('fadeOut')]).encode()).hexdigest()[:12]
    target = WORK / 'recorded' / f"{line['id']}-{key}.wav"
    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        fade = min(0.04, (audio['to'] - audio['from']) / 4)
        # v9: a scene's own background fades in before its line and out after it, instead of switching at the cut (G3)
        fade_in, fade_out = max(fade, audio.get('fadeIn', 0.0)), max(fade, audio.get('fadeOut', 0.0))
        span = ['-ss', str(audio['from']), '-to', str(audio['to'])]
        gain = max(-20.0, min(40.0, VOICE_LUFS - loudness(source, span)))  # app takes are recorded very quietly (-43 dBFS)
        run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *span, '-i', str(source),
             '-vn', '-af', f"{audio['eq'] + ',' if audio.get('eq') else ''}{denoise + ',' if denoise else ''}"
             f"volume={gain:.2f}dB,{audio['gate'] + ',' if audio.get('gate') else ''}alimiter=limit=0.89:level=false,"
             f"afade=t=in:d={fade_in},areverse,afade=t=in:d={fade_out},areverse",
             '-ac', '2', '-ar', '48000', str(target)])
    return target


def synthesize_voices(plan: dict) -> dict:
    """Recorded sound for lines that have it (generated scenes, the app's speaker); edge-tts only
    for lines without (scripts/film_voice.py)."""
    lines = sounding(plan)
    made = film_voice.synthesize([line for line in lines if not line.get('audio')])
    made.update({line['id']: recorded_voice(line) for line in lines if line.get('audio')})
    return {key: (path, probe_duration(path)) for key, path in made.items()}


def check_dialogue(plan: dict, voices: dict, total: float) -> list:
    """Lines never overlap each other and finish before the film ends."""
    problems, lines = [], sorted(sounding(plan), key=lambda l: l['at'])
    for line, nxt in zip(lines, lines[1:] + [None]):
        end = line['at'] + voices[line['id']][1]
        if nxt and end > nxt['at'] + 0.002:  # v6: each cut's sound ends exactly where the next begins (both fade 40 ms)
            problems.append(f"{line['id']} ends at {end:.2f}s, overlapping {nxt['id']} at {nxt['at']}s")
        if end > total - 0.3:
            problems.append(f"{line['id']} ends at {end:.2f}s, after the film")
    return problems


def mix_audio(plan: dict, voices: dict, total: float, output: Path) -> dict:
    """Every line at its place; an optional licensed music bed (plan sound.music) ducked under speech.
    No synthesized music or road noise. The whole mix gets one measured linear gain to FILM_LUFS."""
    inputs, delays, lines = [], [], sounding(plan)
    for index, line in enumerate(lines):
        inputs += ['-i', str(voices[line['id']][0])]
        delays.append(f"[{index}:a]adelay={round(line['at'] * 1000)}:all=1[d{index}]")
    lines_in = ''.join(f'[d{i}]' for i in range(len(lines)))
    music = plan.get('sound', {}).get('music')
    raw = WORK / 'mix-raw.wav'
    if music:
        n = len(lines)
        inputs += ['-i', str(ROOT / music['file'])]
        graph = delays + [
            f'{lines_in}amix=inputs={n}:normalize=0,apad,atrim=0:{total},asplit=2[voice][key]',
            f"[{n}:a]atrim=0:{round(total - music.get('start', 0.0), 3)},acompressor=threshold=-30dB:ratio=3:attack=200:release=1200:makeup=4,"
            f"volume={music.get('gainDb', -24)}dB,afade=t=in:d=1.0,"
            f"afade=t=out:st={round(total - music.get('start', 0.0) - 2.5, 3)}:d=2.5,adelay={round(music.get('start', 0.0) * 1000)}:all=1,"
            f"apad,atrim=0:{total},aresample=48000[bed]",
            '[bed][key]sidechaincompress=threshold=0.03:ratio=3:attack=60:release=700,asplit=2[ducked][bedstem]',  # duck gently: the bed is the app cuts' floor
            f'[ducked][voice]amix=inputs=2:normalize=0,atrim=0:{total},aresample=48000[mix]']
    else:
        graph = delays + [f'{lines_in}amix=inputs={len(lines)}:normalize=0,apad,atrim=0:{total},aresample=48000[mix]']
    # the music bed as heard (ducked), beside the mix: scripts/check-film.py holds it level across a cut to measure the
    # background change the cut itself makes (G3)
    stem = ['-map', '[bedstem]', '-ac', '1', str(WORK / 'music-stem.wav')] if music else []
    (WORK / 'music-stem.wav').unlink(missing_ok=True)
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *inputs, '-filter_complex', ';'.join(graph),
         '-map', '[mix]', '-ac', '2', str(raw), *stem])
    # the dialogue alone (no music bed): scripts/check-film.py measures the background of the lines on it
    voice_graph = delays + [f'{lines_in}amix=inputs={len(lines)}:normalize=0,apad,atrim=0:{total},aresample=48000[voice]']
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *inputs[:2 * len(lines)], '-filter_complex', ';'.join(voice_graph),
         '-map', '[voice]', '-ac', '1', str(WORK / 'voice-stem.wav')])
    measured = loudness(raw)
    gain = FILM_LUFS - measured
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(raw), '-af',
         f'volume={gain:.2f}dB,alimiter=limit=0.84:level=false', '-ac', '2', '-ar', '48000', str(output)])
    return {'measuredLufs': round(measured, 2), 'gainDb': round(gain, 2), 'targetLufs': FILM_LUFS, 'music': bool(music)}


def stamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    return f'{millis // 3600000:02}:{millis // 60000 % 60:02}:{millis // 1000 % 60:02}.{millis % 1000:03}'


def captions(plan: dict, voices: dict) -> list:
    """(start, end, speaker, text, burned): every line goes to VTT/transcript; lines the
    end card already shows on screen (`caption: false`) are not burned in twice. A caption
    never runs into the next one, so two lines are never stacked."""
    lines = sorted((l for l in plan['dialogue'] if l.get('text')), key=lambda l: l['at'])
    cues = []
    for line, nxt in zip(lines, lines[1:] + [None]):
        end = line['at'] + (line['seconds'] if line.get('captionOnly') else voices[line['id']][1]) + 0.35
        if nxt is not None:
            end = min(end, nxt['at'] - 0.04)
        end = min(end, line.get('until', end))  # never over the next shot: a caption belongs to its own cut
        cues.append((line['at'], round(end, 3), line['speaker'], line['text'], line.get('caption', True), line.get('marginV', 0),
                     line.get('align')))
    return cues


def write_captions(cues: list, header_note: str, fmt: dict | None = None) -> dict:
    ass = WORK / 'captions.ass'
    width, height = (fmt or {}).get('width', 1920), (fmt or {}).get('height', 1080)
    vertical = height > width  # a phone-sized short: larger text, narrower lines, kept above the player's own buttons
    size, side, bottom, name_size = (56, 80, 360, 40) if vertical else (50, 180, 64, 34)
    header = ['[Script Info]', 'ScriptType: v4.00+', f'PlayResX: {width}', f'PlayResY: {height}', 'WrapStyle: 0', '[V4+ Styles]',
              'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, '
              'Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
              f'Style: Line,Pretendard Variable,{size},&H00F5F4EE,&H000000FF,&H40141A16,&H60141A16,0,0,0,0,100,100,0,0,1,3,1.6,2,{side},{side},{bottom},1',
              '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    ass_time = lambda s: stamp(s)[1:-1]  # H:MM:SS.cc
    events = []
    for s, e, speaker, text, burned, margin, align in cues:
        if not burned:
            continue
        colour = SPEAKER_COLOURS.get(speaker, '&H00F5F4EE')
        tag = f'{{\\fs{name_size}\\b1\\c{colour}&}}{speaker}{{\\r}}  '
        place = f'\\an{align}' if align else ''  # e.g. 8: hang from the top margin, just under the app's screen band
        events.append(f'Dialogue: 0,{ass_time(s)},{ass_time(e)},Line,,0,0,{margin},,{{\\fad(90,120){place}}}{tag}{text}')
    ass.write_text('\n'.join(header + events) + '\n')
    vtt = 'WEBVTT\n\n' + '\n\n'.join(f'{stamp(c[0])} --> {stamp(c[1])}\n{c[2]}: {c[3]}' for c in cues) + '\n'
    transcript = header_note + '\n\n' + '\n'.join(f'[{stamp(c[0])[3:8]}] {c[2]}: {c[3]}' for c in cues) + '\n'
    return {'ass': ass, 'vtt': vtt, 'transcript': transcript}


def caption_scrim(width: int, height: int) -> Path:
    """Soft lower-third darkening so captions stay legible over bright knitwear."""
    from PIL import Image
    target = WORK / f'scrim-{width}x{height}.png'
    if not target.is_file():
        band = int(height * 0.26)
        alpha = (np.clip(np.linspace(-0.15, 1, band), 0, 1) ** 1.6 * 120).astype('uint8')
        rgba = np.zeros((height, width, 4), dtype='uint8')
        rgba[..., :3] = (12, 16, 13)
        rgba[height - band:, :, 3] = alpha[:, None]
        Image.fromarray(rgba, 'RGBA').save(target)
    return target


def name_boxes(source: Path, start: float, end: float) -> list:
    """Boxes where the family's name is drawn in this part of a take (scripts/film_redact.py), cached."""
    key = hashlib.sha256(json.dumps([sha(source), start, end, sha(ROOT / 'scripts/film_redact.py'),
                                     sorted(sha(t) for t in (ROOT / '.tools/product-film/redact').glob('name-*.png'))]).encode()).hexdigest()[:12]
    cache = WORK / 'redact' / f'{key}.json'
    if not cache.is_file():
        cache.parent.mkdir(parents=True, exist_ok=True)
        out = subprocess.check_output([str(ROOT / '.tools/edge-venv/bin/python'), str(ROOT / 'scripts/film_redact.py'),
                                       str(source), str(start), str(end)])
        cache.write_text(out.decode())
    return json.loads(cache.read_text())['boxes']


def cut_source(cut: dict, shots: dict) -> tuple:
    if 'vertical' in cut:
        clip = (ROOT / cut['folder'] if cut.get('folder') else VERTICAL) / cut.get('clip', f"{cut['vertical']}.mp4")
        return clip, probe_duration(clip)
    if 'weave' in cut:
        clip = WEAVE / f"{cut['weave']}.mp4"
        return clip, probe_duration(clip)
    if 'app' in cut:
        return TAKES / f"{cut['app']}.mp4", float(take_record(cut['app'])['video']['format']['duration'])
    shot = shots[cut['shot']]
    return GENERATOR['clip_path'](shot), source_seconds(shot)


def overlay_graph(plan: dict, cuts: list, graphics: dict, first_input: int) -> tuple:
    """Feature labels fade in top-left; the real-footage tag sits top-right on app cuts."""
    inputs, graph, label = [], [], '[base]'
    fade = 0.22
    for index, item in enumerate(plan['labels']):
        n = first_input + len(inputs) // 6
        inputs += ['-framerate', str(plan['format']['fps']), '-loop', '1', '-i', str(graphics[index])]
        a, b = item['at'], item['until']
        graph.append(f'[{n}:v]format=rgba,fade=in:st={a}:d={fade}:alpha=1,fade=out:st={round(b - fade, 3)}:d={fade}:alpha=1[l{index}]')
        y = item.get('y', plan.get('overlayY', 56))  # below the app header; a label can ask for its own place
        x = item.get('x', plan.get('labelX', 64))  # app cuts: over Pli's header, not the vehicle panel's speed and gear
        graph.append(f"{label}[l{index}]overlay={x}:{y}:shortest=1:enable='between(t,{a},{b})'[o{index}]")
        label = f'[o{index}]'
    card_start = round(cuts[-1]['start'] + cuts[-1]['length'] - plan['endCard'].get('transition', {}).get('seconds', 0.0), 3)
    spans = [(c['start'], min(card_start, round(c['start'] + c['length'], 3))) for c in cuts if 'app' in c]  # not over the end card
    if spans:
        n = first_input + len(inputs) // 6
        inputs += ['-framerate', str(plan['format']['fps']), '-loop', '1', '-i', str(graphics['tag'])]
        when = '+'.join(f'between(t,{a},{b})' for a, b in spans)
        graph.append(f"{label}[{n}:v]overlay=W-w-{plan.get('tagRight', 56)}:{plan.get('tagY', plan.get('overlayY', 56) + 4)}:shortest=1:enable='{when}'[tagged]")
        label = '[tagged]'
    for index, note in enumerate(plan.get('notes', [])):  # small honest notes, e.g. where waiting time was cut out
        n = first_input + len(inputs) // 6
        inputs += ['-framerate', str(plan['format']['fps']), '-loop', '1', '-i', str(graphics[f'note{index}'])]
        a, b = note['at'], note['until']
        graph.append(f"{label}[{n}:v]overlay={note.get('x', '(W-w)/2')}:{note['y']}:shortest=1:enable='between(t,{a},{b})'[note{index}]")
        label = f'[note{index}]'
    return inputs, graph, label


def render(plan: dict) -> dict:
    WORK.mkdir(parents=True, exist_ok=True)
    cuts, card, total = timeline(plan)
    shots = {shot['id']: shot for shot in plan['shots']}
    voices = synthesize_voices(plan)
    problems = check_dialogue(plan, voices, total)
    if problems:  # fail before any expensive video work
        raise SystemExit('Dialogue does not fit the cut: ' + '; '.join(problems))
    fmt = plan['format']
    clips = []
    for number, cut in enumerate(cuts):
        source, available = cut_source(cut, shots)
        if 'app' in cut and plan.get('appFrame', {}).get('redact'):  # optional: remove the family name from app cuts
            cut = {**cut, 'remove': name_boxes(source, cut['in'], min(cut['out'] + 0.15, available))}
        name = cut.get('app') or cut.get('weave') or cut.get('vertical') or cut['shot']
        clips.append(render_cut(cut, source, available, WORK / f'cut-{number}-{name}.mp4', fmt, plan.get('appFrame', {})))
    card_key = hashlib.sha256(json.dumps([card, fmt, sha(film_endcard.MARK), sha(film_endcard.FONT),
                                          sha(ROOT / 'scripts/film_endcard.py')], ensure_ascii=False).encode()).hexdigest()[:12]
    end_card = WORK / f'end-card-{card_key}.mp4'
    if not end_card.is_file():
        film_endcard.render(card, end_card.with_suffix('.part.mp4'), fmt['width'], fmt['height'], fmt['fps']).replace(end_card)
    clips.append(end_card)
    picture = WORK / 'picture.mp4'
    compose_video(plan, cuts, card, clips, picture)
    levels = mix_audio(plan, voices, total, WORK / 'mix.wav')
    text = write_captions(captions(plan, voices), plan['transcriptNote'], fmt)
    graphics = film_overlay.render_all(plan['labels'], plan['footageTag'], WORK / 'overlay')
    for index, note in enumerate(plan.get('notes', [])):
        graphics[f'note{index}'] = film_overlay.footage_tag(note['text'], WORK / 'overlay' / f'note-{index}.png')
    extra, graph, label = overlay_graph(plan, cuts, graphics, first_input=3)
    card_at = round(cuts[-1]['start'] + cuts[-1]['length'] - card.get('transition', {}).get('seconds', 0.0), 3)
    panel_until = f":enable='lt(t,{card_at})'" if plan.get('panelTop') or plan.get('scrimTop') else ''  # the end card keeps its own look
    graph = [f'[0:v][2:v]overlay=0:0{panel_until}[base]'] + graph + [f"{label}subtitles={text['ass']}:fontsdir={FONTS}[v]"]
    partial = MASTER.with_suffix('.part.mp4')
    scrim = (caption_gradient(fmt['width'], fmt['height'], plan['scrimTop']) if plan.get('scrimTop') else
             caption_panel(fmt['width'], fmt['height'], plan['panelTop']) if plan.get('panelTop') else caption_scrim(fmt['width'], fmt['height']))
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(picture), '-i', str(WORK / 'mix.wav'),
         '-i', str(scrim), *extra, '-filter_complex', ';'.join(graph),
         '-map', '[v]', '-map', '1:a', '-t', str(total),
         # Streamed through a public tunnel: cap the bitrate.
         '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-maxrate', '6M', '-bufsize', '12M',
         '-pix_fmt', 'yuv420p', '-profile:v', 'high',
         '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(partial)])
    partial.replace(MASTER)
    (WORK / 'preview.vtt').write_text(text['vtt'])
    (WORK / 'preview-transcript.txt').write_text(text['transcript'])
    sources = {}
    for cut in cuts:
        key = cut.get('app') or cut.get('weave') or cut.get('vertical') or cut['shot']
        sources[key] = sha(cut_source(cut, shots)[0])
    info = {'type': 'product-story', 'actualAppFootage': False,
            'generation': plan['identity'],
            'appTakes': {cut['app']: {'spoken': take_record(cut['app'])['spoken'], 'recordedAt': take_record(cut['app'])['recordedAt']}
                         for cut in cuts if 'app' in cut},
            'durationSeconds': round(probe_duration(MASTER), 3), 'videoSha256': sha(MASTER), 'apkSha256': None,
            'planSha256': sha(PLAN), 'sources': sources,
            'audioStems': levels, 'renderedAt': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    (WORK / 'render-info.json').write_text(json.dumps(info, ensure_ascii=False, indent=2))
    return info


def stage_portal() -> dict:
    """Copy the reviewed render into demo-v2 only if it still matches the plan and bytes."""
    info = json.loads((WORK / 'render-info.json').read_text())
    if info['planSha256'] != sha(PLAN) or info['videoSha256'] != sha(MASTER):
        raise SystemExit('Render is stale; run the build again before staging')
    portal = ROOT / 'demo-v2'
    shutil.copyfile(MASTER, portal / 'preview.mp4')
    shutil.copyfile(WORK / 'preview.vtt', portal / 'preview.vtt')
    shutil.copyfile(WORK / 'preview-transcript.txt', portal / 'preview-transcript.txt')
    public = {k: info[k] for k in ('type', 'actualAppFootage', 'generation', 'durationSeconds', 'videoSha256', 'apkSha256')}
    (portal / 'preview-info.json').write_text(json.dumps(public, ensure_ascii=False, indent=2) + '\n')
    return public


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='validate footage and edit without rendering')
    parser.add_argument('--stage-portal', action='store_true', help='copy the reviewed render into demo-v2')
    args = parser.parse_args()
    if args.stage_portal:
        print(json.dumps(stage_portal(), ensure_ascii=False))
        return 0
    plan = json.loads(PLAN.read_text())
    problems = validate(plan)
    if problems:
        print(json.dumps({'ready': False, 'reason': 'Generated moving footage is required; no still fallback.',
                          'problems': problems}, ensure_ascii=False))
        return 2
    if args.check:
        print(json.dumps({'ready': True, 'cuts': len(plan['edit']), 'seconds': timeline(plan)[2]}))
        return 0
    info = render(plan)
    print(json.dumps({'master': str(MASTER.relative_to(ROOT)), 'seconds': info['durationSeconds'],
                      'videoSha256': info['videoSha256']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
