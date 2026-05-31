import os
import math
import random
import io
import logging

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# --- Constants ---
SIZE = 600           # Canvas size (square)
CENTRE = SIZE // 2
RADIUS = 260         # Wheel radius
NEEDLE_DIST = RADIUS + 20   # Distance from centre to needle tip
FONT_SIZE = 16  # base — overridden dynamically per render based on game count
FRAME_DURATION_MS = 40  # ~25fps

# Visually distinct palette — warm/cool alternating to avoid adjacent clashes
_PALETTE = [
    (99,  102, 241),  # indigo
    (234, 88,  12),   # orange
    (16,  185, 129),  # emerald
    (239, 68,  68),   # red
    (59,  130, 246),  # blue
    (245, 158, 11),   # amber
    (168, 85,  247),  # purple
    (20,  184, 166),  # teal
    (236, 72,  153),  # pink
    (132, 204, 22),   # lime
    (251, 191, 36),   # yellow
    (14,  165, 233),  # sky
]


def _assign_colours(n: int) -> list[tuple[int, int, int]]:
    """
    Assign colours to n slices so no two adjacent slices (including
    wrap-around) share the same colour. Uses a greedy approach over
    a shuffled palette copy so results vary slightly each run.
    """
    palette = _PALETTE[:]
    # Extend palette if we somehow have more games than colours
    while len(palette) < n:
        palette += _PALETTE

    assigned: list[tuple | None] = [None] * n
    for i in range(n):
        forbidden = set()
        if i > 0 and assigned[i - 1]:
            forbidden.add(assigned[i - 1])
        if i == n - 1 and assigned[0]:   # wrap-around: last is adjacent to first
            forbidden.add(assigned[0])

        candidates = [c for c in palette if c not in forbidden]
        # Prefer colours not used recently
        if not candidates:
            candidates = palette  # fallback (shouldn't happen with ≥3 colours)
        assigned[i] = candidates[i % len(candidates)]
    return assigned


def _render_frame(
    games: list[str],
    colours: list[tuple[int, int, int]],
    angle_offset_deg: float,
    size: int,
    radius: int,
    font: ImageFont.FreeTypeFont,
) -> Image.Image:
    """Render a single wheel frame using PIL only (no matplotlib)."""
    img = Image.new("RGBA", (size, size), (32, 32, 36, 255))
    draw = ImageDraw.Draw(img)

    n = len(games)
    slice_deg = 360.0 / n
    cx, cy = size // 2, size // 2

    # --- Rings drawn first so text and needle render on top ---
    shadow_r = radius + 4
    draw.ellipse(
        [cx - shadow_r, cy - shadow_r, cx + shadow_r, cy + shadow_r],
        outline=(0, 0, 0, 60),
        width=6,
    )

    # Outer ring drawn before slices so text renders on top of it
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        outline=(80, 80, 88),
        width=3,
    )

    for i, (game, colour) in enumerate(zip(games, colours)):
        start = angle_offset_deg + i * slice_deg
        end = start + slice_deg

        # Draw filled arc (wedge)
        draw.pieslice(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            start=start,
            end=end,
            fill=colour,
            outline=(32, 32, 36),
            width=2,
        )

        # --- Text label ---
        mid_deg = start + slice_deg / 2
        mid_rad = math.radians(mid_deg)

        # Text sits at 68% of the radius from centre
        text_r = radius * 0.68
        tx = cx + text_r * math.cos(mid_rad)
        ty = cy + text_r * math.sin(mid_rad)

        label = game
        fit_font = font
        bbox = fit_font.getbbox(label)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        # Rotation: always point outward from centre, clamped so text
        # never flips upside-down regardless of wheel position.
        # We rotate a small surface then paste it — this avoids the
        # in-place rotation that caused the mid-animation flip bug.
        rotation = mid_deg  # degrees, PIL rotates anti-clockwise
        # Keep text right-side up: if the outward direction is in the
        # left half (90–270°), flip 180° so letters face outward.
        if 90 < (mid_deg % 360) <= 270:
            rotation += 180

        # Draw label on a transparent surface, then rotate and paste.
        # Shadow is drawn first (offset 1px in each direction) to give
        # strong legibility against any segment colour.
        pad = 12
        surf = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(surf)
        shadow = (0, 0, 0, 180)
        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1), (0, 2), (2, 0)]:
            sdraw.text((pad + dx, pad + dy), label, font=fit_font, fill=shadow)
        sdraw.text((pad, pad), label, font=fit_font, fill=(255, 255, 255, 255))
        rotated = surf.rotate(-rotation, expand=True, resample=Image.BICUBIC)

        # Paste centred on the text position
        px = int(tx - rotated.width / 2)
        py = int(ty - rotated.height / 2)
        img.paste(rotated, (px, py), rotated)


    # --- Needle on top of everything ---
    # Tip penetrates 20px inside the wheel edge so it clearly points at a segment.
    # The base sits outside the wheel so the body is always visible.
    tip_x = cx + radius - 20       # 20px inside the wheel edge
    tip_y = cy
    base_x = cx + radius + 30      # base sits outside the rim
    needle_pts = [
        (base_x, tip_y - 14),   # back top
        (base_x, tip_y + 14),   # back bottom
        (tip_x,  tip_y),        # tip (inside wheel)
    ]
    draw.polygon(needle_pts, fill=(220, 30, 30), outline=(200, 200, 200), width=2)

    return img


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Try to load a TrueType font; fall back to PIL default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        "arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def calculate_gif_duration(file_name: str) -> float:
    """Return total GIF duration in seconds."""
    with Image.open(file_name) as gif:
        total_ms = sum(
            frame.info.get("duration", FRAME_DURATION_MS)
            for frame in _iter_frames(gif)
        )
    return total_ms / 1000.0


def _iter_frames(image: Image.Image):
    """Yield every frame of a GIF."""
    try:
        while True:
            yield image.copy()
            image.seek(image.tell() + 1)
    except EOFError:
        pass


def _generate_rotations(
    start_rotation: float,
    complete_rotations: int,
    end_rotation: float,
) -> list[float]:
    """
    Generate per-frame rotation angles with smooth ease-in/ease-out.
    Returns a list of absolute angle values (degrees).
    """
    max_speed = 30
    accel_frames = 20
    decel_frames = 220

    total_rotation = (complete_rotations * 360) + (360 - end_rotation) + start_rotation

    accel = [round(max_speed * (i / accel_frames) ** 2) for i in range(accel_frames)]

    # Single continuous curve: parameterised to start partway along a fractional-
    # power curve so the initial decel rate is gentle (no perceptible jerk at the
    # handoff from constant speed), and the tail naturally slows to near-zero over
    # ~1.5s for suspense on close calls. Max decel-rate change is <0.001 deg/frame².
    _t0 = 0.55
    _exp = 0.35
    def _t(i): return _t0 + (1 - _t0) * i / decel_frames
    decel = [
        max_speed * (1 - _t(i) ** _exp) / (1 - _t0 ** _exp)
        for i in range(decel_frames)
    ]

    degrees_left = total_rotation - sum(accel) - sum(decel)
    if degrees_left < 0:
        logger.debug("Rotation too small for easing phases — adding extra rotations.")
        return _generate_rotations(start_rotation, complete_rotations + 2, end_rotation)

    constant = [max_speed] * int(degrees_left / max_speed)
    speed_profile = accel + constant + decel

    frames = []
    current = start_rotation
    for speed in speed_profile:
        current -= speed  # negative = clockwise in PIL (angles increase clockwise)
        frames.append(current)

    # Correction distributed over the decel tail so the landing is exact.
    correction = total_rotation - sum(accel) - len(constant) * max_speed - sum(decel)
    decel_start = len(frames) - len(decel)
    for i in range(len(decel)):
        ratio = (i + 1) / len(decel)
        frames[decel_start + i] -= correction * ratio

    return frames


def generate_wheel_of_games(games: list[str], winning_index: int, file_name: str) -> None:
    """
    Generate an animated GIF of a spinning wheel landing on `winning_index`.
    All rendering is done with PIL (no matplotlib), which is significantly faster.
    """
    # Scale font size to the number of games: fewer games = bigger slices = bigger text.
    # Clamp between 13 (many games) and 22 (few games).
    # Apply FONT_SCALE from environment to adjust for DPI differences across systems.
    font_scale = float(os.environ.get("FONT_SCALE", "1.0"))
    dynamic_font_size = max(13, min(22, int((34 - len(games) * 0.8) * font_scale)))
    font = _load_font(dynamic_font_size)
    colours = _assign_colours(len(games))

    start_angle = random.uniform(0, 360)
    complete_rotations = int(random.uniform(4, 8))
    slice_deg = 360.0 / len(games)

    # Target angle: needle (at the 3 o'clock position) points at winning slice
    winning_max = 360 - (winning_index * slice_deg + 1)
    winning_min = winning_max - (slice_deg - 2)
    winning_rotation = random.uniform(winning_min, winning_max)

    rotations = _generate_rotations(start_angle, complete_rotations, winning_rotation)

    logger.debug(f"start={start_angle:.1f} rotations={complete_rotations} "
                 f"target={winning_rotation:.1f}")

    # --- Render frames ---
    # Re-using a single render call per frame is the core speed improvement.
    # The RGBA frame is explicitly closed after palette conversion so the full-colour
    # buffer doesn't stay resident for the entire list before save.
    frames: list[Image.Image] = []
    for angle in rotations:
        frame = _render_frame(games, colours, angle, SIZE, RADIUS, font)
        pal_frame = frame.convert("P", palette=Image.ADAPTIVE, colors=128)
        frame.close()
        frames.append(pal_frame)

    # Hold on the final frame
    for _ in range(20):
        frames.append(frames[-1])

    # --- Save GIF ---
    # Use optimize=False and lzw compression for speed; adaptive palette per-frame
    durations = [FRAME_DURATION_MS] * len(rotations) + [120] * 20  # last frames linger longer

    frames[0].save(
        file_name,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
    )