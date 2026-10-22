"""Four fixed PRIKOL mascots; four color holds with hard cuts, 4K/30 fps."""
from pathlib import Path
import json
import subprocess
import sys

sys.path.insert(0, '/tmp/prikol-logo-lib')
import aggdraw
from PIL import Image

ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT, FPS = 3840, 2160, 30
HOLD_FRAMES = 36
PALETTES = [
    ('0F4AFB', 'FF8400'),
    ('FFFEEF', 'FF3916'),
    ('0F4AFB', 'FFFEEF'),
    ('FF8400', '0F4AFB'),
]


def ellipse(cx, cy, rx, ry):
    k = 0.5522847498307936
    return [
        ('M', cx + rx, cy),
        ('C', cx + rx, cy + k*ry, cx + k*rx, cy + ry, cx, cy + ry),
        ('C', cx - k*rx, cy + ry, cx - rx, cy + k*ry, cx - rx, cy),
        ('C', cx - rx, cy - k*ry, cx - k*rx, cy - ry, cx, cy - ry),
        ('C', cx + k*rx, cy - ry, cx + rx, cy - k*ry, cx + rx, cy),
        ('Z',),
    ]


# Contours transcribed from the supplied 380 x 1160 mascot artwork.
# One unchanged silhouette is used for every palette and every mascot.
HEAD = ellipse(192.5, 284, 161.5, 256)
BODY = [
    ('M', 146.5, 606.5), ('L', 248.5, 606.5),
    ('L', 354.2, 1118.2), ('L', 223.3, 1118.2),
    ('L', 185.4, 995.5), ('L', 146.3, 1118.2),
    ('L', 20.5, 1118.2), ('Z',),
]
LEFT_ARM = [
    ('M', 111, 759.5),
    ('C', 103, 758.5, 95.5, 755.8, 88, 752),
    ('C', 108, 736, 105, 711, 88, 696),
    ('C', 72, 681, 48, 681, 31, 694),
    ('C', 12, 708, 14, 730, 26, 749),
    ('C', 41, 776, 69, 790, 103, 795.5),
    ('Z',),
]
RIGHT_ARM = [
    ('M', 280.5, 762.5),
    ('C', 288, 761, 295, 757.5, 301, 753.5),
    ('C', 283, 737, 285, 715.5, 299, 701),
    ('C', 314, 685, 339, 685, 355, 699),
    ('C', 373, 714, 371, 735, 357, 756),
    ('C', 342, 779, 317, 791, 287.5, 796),
    ('Z',),
]
EYES = [ellipse(125.5, 284, 28.5, 44), ellipse(260.5, 284, 28.5, 44)]
MOUTH = [
    ('M', 166.8, 404.5), ('L', 218.5, 404.5),
    ('C', 226.5, 428, 211.5, 438, 192.5, 438),
    ('C', 173.5, 438, 160, 428, 166.8, 404.5), ('Z',),
]


def mascot_path(commands, center_x, supersample):
    scale = 1720 / (1118.2 - 28)
    center_y = (1118.2 + 28) / 2
    path = aggdraw.Path()
    for command in commands:
        if command[0] == 'Z':
            path.close()
            continue
        points = []
        for i in range(1, len(command), 2):
            points.extend((
                ((command[i] - 192.5)*scale + center_x)*supersample,
                ((command[i+1] - center_y)*scale + HEIGHT/2)*supersample,
            ))
        if command[0] == 'M':
            path.moveto(*points)
        elif command[0] == 'L':
            path.lineto(*points)
        elif command[0] == 'C':
            path.curveto(*points)
    return path


def render(background, foreground):
    ss = 2
    image = Image.new('RGB', (WIDTH*ss, HEIGHT*ss), '#' + background)
    draw = aggdraw.Draw(image)
    for cx in (600, 1480, 2360, 3240):
        for commands in (HEAD, LEFT_ARM, RIGHT_ARM, BODY):
            draw.path(mascot_path(commands, cx, ss), aggdraw.Brush('#' + foreground))
        for commands in (*EYES, MOUTH):
            draw.path(mascot_path(commands, cx, ss), aggdraw.Brush('#' + background))
    draw.flush()
    return image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def main():
    output = ROOT / 'prikol_mascots_colors_4k.mp4'
    command = [
        'ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y',
        '-f', 'rawvideo', '-pixel_format', 'rgb24',
        '-video_size', f'{WIDTH}x{HEIGHT}', '-framerate', str(FPS),
        '-i', '-', '-an',
        '-vf', ('scale=in_range=full:out_range=tv:out_color_matrix=bt709,'
                'setparams=range=limited:color_primaries=bt709:'
                'color_trc=bt709:colorspace=bt709'),
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '10',
        '-pix_fmt', 'yuv420p', '-profile:v', 'high',
        '-color_primaries', 'bt709', '-color_trc', 'bt709',
        '-colorspace', 'bt709', '-color_range', 'tv',
        '-movflags', '+faststart', str(output),
    ]
    previews = []
    with (ROOT / 'encode.log').open('w') as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            for i, (background, foreground) in enumerate(PALETTES):
                frame = render(background, foreground)
                frame.save(ROOT / f'palette_{i+1}.png')
                previews.append(frame.resize((960, 540), Image.Resampling.LANCZOS))
                data = frame.tobytes()
                for _ in range(HOLD_FRAMES):
                    process.stdin.write(data)
                print(f'Palette {i+1}/4 rendered and encoded', flush=True)
        finally:
            process.stdin.close()
        result = process.wait()
    if result:
        raise RuntimeError((ROOT / 'encode.log').read_text())
    contact = Image.new('RGB', (1920, 1080))
    for i, preview in enumerate(previews):
        contact.paste(preview, ((i % 2)*960, (i // 2)*540))
    contact.save(ROOT / 'contact_sheet.png')
    (ROOT / 'timing.json').write_text(json.dumps({
        'width': WIDTH, 'height': HEIGHT, 'fps': FPS,
        'duration': 4*HOLD_FRAMES/FPS,
        'palettes': [
            {'start': i*HOLD_FRAMES/FPS, 'end': (i+1)*HOLD_FRAMES/FPS,
             'background': '#' + bg, 'mascots': '#' + fg}
            for i, (bg, fg) in enumerate(PALETTES)
        ],
    }, indent=2))
    print('Created', output, output.stat().st_size, 'bytes', flush=True)


if __name__ == '__main__':
    main()
