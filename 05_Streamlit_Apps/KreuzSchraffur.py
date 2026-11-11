"""Export a photo as millimetre-scale pen-plotter hatching."""
from io import BytesIO
import math
from pathlib import Path

from PIL import Image, ImageOps

BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


def line_bounds(offset, cosine, sine, width, height):
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
                cutoff = (BAYER[row % 4][column % 4] + 0.5) / 16
                if length / minimum < cutoff:
                    continue
                length = minimum
            inset = (end - start - length) / 2
            a, b = start + inset, end - inset
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


def render_svg(image, width, spacing, cell, pen, minimum, shadow):
    height = width * image.height / image.width
    margin = pen / 2
    page_w, page_h = width + pen, height + pen
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{page_w:.6f}mm" '
        f'height="{page_h:.6f}mm" viewBox="{-margin} {-margin} {page_w:.6f} {page_h:.6f}">'
    ]
    counts = []
    for name, angle, threshold, ink in (
        ("horizontal", 0, 0, "#243e68"),
        ("diagonal", 32, shadow, "#a85242"),
    ):
        paths = hatch(image, width, height, spacing, cell, minimum, angle, threshold)
        counts.append(len(paths))
        svg.append(f'<g id="{name}" fill="none" stroke="{ink}" '
                   f'stroke-width="{pen}" stroke-linecap="round">')
        svg.extend(f'<path d="{path}"/>' for path in paths)
        svg.append('</g>')
    svg.append('</svg>')
    return '\n'.join(svg), height, counts


def main():

