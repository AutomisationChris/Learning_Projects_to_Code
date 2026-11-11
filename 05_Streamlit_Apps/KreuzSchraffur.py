"""Convert a photograph to millimetre-scale pen-plotter SVG paths."""

import argparse
import math
from pathlib import Path

from PIL import Image, ImageOps


BAYER = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


def line_bounds(offset, cosine, sine, width, height):
    """Return the interval of the scan line inside the image rectangle."""
    lower, upper = -math.inf, math.inf
    for origin, direction, extent in (
        (-offset * sine, cosine, width),
        (offset * cosine, sine, height),
    ):
        if abs(direction) < 1e-12:
            if not 0 <= origin <= extent:
                return 0, 0
            continue
        a, b = sorted((-origin / direction, (extent - origin) / direction))
        lower, upper = max(lower, a), min(upper, b)
    return lower, upper


def hatch(image, width, height, spacing, cell, minimum, angle, threshold):
    cosine, sine = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    offsets = (0, -width * sine, height * cosine, height * cosine - width * sine)
    pixels = image.load()
    paths = []
    for row in range(math.floor(min(offsets) / spacing) + 1,
                     math.ceil(max(offsets) / spacing)):
        offset = row * spacing
        lower, upper = line_bounds(offset, cosine, sine, width, height)
        phase = cell / 2 if row % 2 else 0
        intervals = []
        for column in range(math.floor((lower - phase) / cell),
                            math.ceil((upper - phase) / cell)):
            start = max(lower, phase + column * cell)
            end = min(upper, phase + (column + 1) * cell)
            if end - start < minimum:
                continue
            darkness = 0
            for sample in range(5):
                t = start + (end - start) * (sample + 0.5) / 5
                x = t * cosine - offset * sine
                y = t * sine + offset * cosine
                px = min(image.width - 1, max(0, int(x / width * image.width)))
                py = min(image.height - 1, max(0, int(y / height * image.height)))
                darkness += 1 - pixels[px, py] / 255
            coverage = max(0, (darkness / 5 - threshold) / (1 - threshold))
            length = (end - start) * coverage
            if length < minimum:
                # Preserve highlights by varying how often a minimum-length stroke appears.
                cutoff = (BAYER[row % 4][column % 4] + 0.5) / 16
                if length / minimum < cutoff:
                    continue
                length = minimum
            inset = (end - start - length) / 2
            a, b = start + inset, end - inset
            # Close gaps smaller than half the minimum movement to avoid extra lifts.
            if intervals and a - intervals[-1][1] <= minimum / 2:
                intervals[-1] = (intervals[-1][0], b)
            else:
                intervals.append((a, b))
        if row % 2:
            intervals = [(b, a) for a, b in reversed(intervals)]
        for a, b in intervals:
            x1, y1 = a * cosine - offset * sine, a * sine + offset * cosine
            x2, y2 = b * cosine - offset * sine, b * sine + offset * cosine
            paths.append(f'M {x1:.4f},{y1:.4f} L {x2:.4f},{y2:.4f}')
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('photo', type=Path)
    parser.add_argument('svg', type=Path)
    parser.add_argument('--width', type=float, default=180, help='image width in mm')
    parser.add_argument('--spacing', type=float, default=0.6, help='line spacing in mm')
    parser.add_argument('--cell', type=float, default=1.2, help='sample length in mm')
    parser.add_argument('--pen', type=float, default=0.2, help='pen width in mm')
    parser.add_argument('--min-stroke', type=float, default=0.2, help='minimum movement in mm')
    parser.add_argument('--shadow', type=float, default=0.6, help='darkness threshold for diagonal lines')
    args = parser.parse_args()
    dimensions = (args.width, args.spacing, args.cell, args.pen, args.min_stroke)
    if any(not math.isfinite(value) or value <= 0 for value in dimensions):
        parser.error('Dimensions must be finite and positive.')
    if args.min_stroke > args.cell or not 0 <= args.shadow < 1:
        parser.error('Use min-stroke <= cell and 0 <= shadow < 1.')
    if args.photo.resolve() == args.svg.resolve():
        parser.error('Use different paths for the input and output.')
    with Image.open(args.photo) as source:
        image = ImageOps.autocontrast(ImageOps.exif_transpose(source).convert('L'), cutoff=1)
    width = args.width
    height = width * image.height / image.width
    margin = args.pen / 2
    page_w, page_h = width + args.pen, height + args.pen
    with args.svg.open('w', encoding='utf-8') as output:
        output.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{page_w:.6f}mm" '
                     f'height="{page_h:.6f}mm" viewBox="{-margin} {-margin} {page_w:.6f} {page_h:.6f}">\n')
        for name, angle, threshold in [('horizontal', 0, 0), ('diagonal', 45, args.shadow)]:
            paths = hatch(image, width, height, args.spacing, args.cell,
                          args.min_stroke, angle, threshold)
            output.write(f'  <g id="{name}" fill="none" stroke="#000" '
                         f'stroke-width="{args.pen}" stroke-linecap="round">\n')
            for path in paths:
                output.write(f'    <path d="{path}"/>\n')
            output.write('  </g>\n')
            print(f'{name}: {len(paths)} strokes')
        output.write('</svg>\n')
    print(f'Image: {width:.1f} x {height:.1f} mm')


if __name__ == '__main__':
    main()
