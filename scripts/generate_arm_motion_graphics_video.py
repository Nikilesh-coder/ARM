"""
ARM Motion Graphics Video Generator
Renders a 42.5-second cinematic 720p 24fps MP4 video featuring all 13 scenes of the ARM Product Intro
with synthesized ambient and transition sound design, encoded with H.264 / AAC for VLC/WMP compatibility.
Output: apps/web/public/ARM_Motion_Graphics.mp4
"""

import os
import math
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

WIDTH = 1280
HEIGHT = 720
FPS = 24
DURATION = 42.5
TOTAL_FRAMES = int(DURATION * FPS)
SAMPLE_RATE = 44100

OUTPUT_MP4 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "web", "public", "ARM_Motion_Graphics.mp4"))
TEMP_VIDEO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scratch_video_raw.mp4"))
TEMP_AUDIO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scratch_audio.wav"))

# Fonts
WIN_FONTS = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
FONT_REGULAR = os.path.join(WIN_FONTS, "segoeui.ttf")
FONT_BOLD = os.path.join(WIN_FONTS, "segoeuib.ttf")
FONT_MONO = os.path.join(WIN_FONTS, "consola.ttf")

try:
    font_hero = ImageFont.truetype(FONT_BOLD, 68)
    font_title = ImageFont.truetype(FONT_BOLD, 46)
    font_heading = ImageFont.truetype(FONT_BOLD, 32)
    font_body = ImageFont.truetype(FONT_REGULAR, 22)
    font_small = ImageFont.truetype(FONT_REGULAR, 17)
    font_mono = ImageFont.truetype(FONT_MONO, 18)
    font_mono_small = ImageFont.truetype(FONT_MONO, 14)
except Exception:
    font_hero = font_title = font_heading = font_body = font_small = font_mono = font_mono_small = ImageFont.load_default()

# 13 Scenes Definitions & Timings (Matching web component)
SCENES = [
    {"id": 1, "name": "intro", "start": 0.0, "end": 3.2},
    {"id": 2, "name": "model", "start": 3.2, "end": 6.2},
    {"id": 3, "name": "personalized", "start": 6.2, "end": 9.2},
    {"id": 4, "name": "dashboard", "start": 9.2, "end": 12.5},
    {"id": 5, "name": "create_project", "start": 12.5, "end": 15.8},
    {"id": 6, "name": "upload_template", "start": 15.8, "end": 18.8},
    {"id": 7, "name": "analysis", "start": 18.8, "end": 22.2},
    {"id": 8, "name": "evidence", "start": 22.2, "end": 25.2},
    {"id": 9, "name": "thinking", "start": 25.2, "end": 28.4},
    {"id": 10, "name": "replacement", "start": 28.4, "end": 33.0},
    {"id": 11, "name": "comparison", "start": 33.0, "end": 36.2},
    {"id": 12, "name": "generation", "start": 36.2, "end": 39.0},
    {"id": 13, "name": "hero", "start": 39.0, "end": 42.5},
]

def draw_top_bar(draw, current_scene):
    # Minimal sleek header
    draw.rectangle([0, 0, WIDTH, 48], fill=(12, 12, 15))
    draw.line([0, 48, WIDTH, 48], fill=(30, 30, 36), width=1)
    # Badge
    draw.rounded_rectangle([32, 12, 86, 36], radius=6, fill=(24, 24, 30), outline=(55, 55, 65))
    draw.text((45, 14), "ARM", fill=(255, 255, 255), font=font_mono_small)
    draw.text((98, 14), "Academic Report Maker • AI Engine", fill=(160, 160, 175), font=font_small)
    # Right scene status
    scene_text = f"Scene {current_scene['id']}/13 • 720p HD"
    bbox = draw.textbbox((0, 0), scene_text, font=font_mono_small)
    w = bbox[2] - bbox[0]
    draw.text((WIDTH - 32 - w, 14), scene_text, fill=(52, 211, 153), font=font_mono_small)

def draw_bottom_timeline(draw, t):
    # Sleek bottom progress bar
    progress = min(1.0, max(0.0, t / DURATION))
    draw.rectangle([0, HEIGHT - 18, WIDTH, HEIGHT], fill=(10, 10, 12))
    draw.rectangle([0, HEIGHT - 6, int(WIDTH * progress), HEIGHT], fill=(52, 211, 153))

def render_frame(frame_idx):
    t = frame_idx / FPS
    # Determine scene
    scene = SCENES[-1]
    for s in SCENES:
        if s["start"] <= t < s["end"]:
            scene = s
            break

    scene_t = t - scene["start"]
    scene_dur = scene["end"] - scene["start"]
    prog = min(1.0, max(0.0, scene_t / scene_dur))

    # Base image: Dark gradient
    img = Image.new("RGB", (WIDTH, HEIGHT), (8, 8, 10))
    draw = ImageDraw.Draw(img)

    # Ambient radial spotlight
    spot_radius = int(280 + 20 * math.sin(t * 1.5))
    center_x = WIDTH // 2
    center_y = HEIGHT // 2 - 20
    # Soft concentric circles for ambient glow
    for r in range(spot_radius, 40, -40):
        alpha = int(12 * (1.0 - (r / spot_radius)))
        color = (16 + alpha, 22 + alpha * 2, 28 + alpha)
        draw.ellipse([center_x - r, center_y - r, center_x + r, center_y + r], fill=color)

    draw_top_bar(draw, scene)

    scene_id = scene["id"]

    # =========================================================================
    # SCENE 1: ARM INTRO
    # =========================================================================
    if scene_id == 1:
        if prog < 0.45:
            text = "Hello"
        else:
            text = "Welcome to ARM"
        bbox = draw.textbbox((0, 0), text, font=font_hero)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (WIDTH - tw) // 2
        y = (HEIGHT - th) // 2 - 40
        draw.text((x, y), text, fill=(255, 255, 255), font=font_hero)
        # Blinking cursor
        if int(t * 4) % 2 == 0:
            draw.rectangle([x + tw + 10, y + 8, x + tw + 16, y + 68], fill=(52, 211, 153))
        # Subtitle
        sub = "ACADEMIC REPORT MAKER • AI ENGINE"
        sbbox = draw.textbbox((0, 0), sub, font=font_mono)
        draw.text(((WIDTH - (sbbox[2] - sbbox[0])) // 2, y + 90), sub, fill=(120, 120, 140), font=font_mono)

    # =========================================================================
    # SCENE 2: ARM AI MODEL
    # =========================================================================
    elif scene_id == 2:
        # Neural node circle
        pulse = 1.0 + 0.08 * math.sin(t * 6.0)
        nr = int(48 * pulse)
        draw.ellipse([center_x - nr, center_y - 80 - nr, center_x + nr, center_y - 80 + nr],
                     fill=(20, 32, 28), outline=(52, 211, 153), width=2)
        draw.text((center_x - 18, center_y - 94), "AI", fill=(52, 211, 153), font=font_heading)

        title = "Meet ARM"
        tbbox = draw.textbbox((0, 0), title, font=font_hero)
        draw.text(((WIDTH - (tbbox[2] - tbbox[0])) // 2, center_y - 10), title, fill=(255, 255, 255), font=font_hero)

        sub = "Your AI-powered academic report assistant."
        sbbox = draw.textbbox((0, 0), sub, font=font_body)
        draw.text(((WIDTH - (sbbox[2] - sbbox[0])) // 2, center_y + 70), sub, fill=(200, 200, 215), font=font_body)

        badge = "● Context-Aware Formatting Model 2.0"
        bbbox = draw.textbbox((0, 0), badge, font=font_mono_small)
        draw.text(((WIDTH - (bbbox[2] - bbbox[0])) // 2, center_y + 120), badge, fill=(52, 211, 153), font=font_mono_small)

    # =========================================================================
    # SCENE 3: PERSONALIZED EXPERIENCE
    # =========================================================================
    elif scene_id == 3:
        # SSO Verified Badge
        badge = "✓ Authenticated Session Verified"
        bbbox = draw.textbbox((0, 0), badge, font=font_mono_small)
        bx = (WIDTH - (bbbox[2] - bbbox[0])) // 2
        draw.rounded_rectangle([bx - 14, center_y - 80, bx + (bbbox[2] - bbbox[0]) + 14, center_y - 52],
                               radius=14, fill=(16, 32, 24), outline=(52, 211, 153), width=1)
        draw.text((bx, center_y - 74), badge, fill=(52, 211, 153), font=font_mono_small)

        greeting = "Hello, Engineering Scholar"
        gbbox = draw.textbbox((0, 0), greeting, font=font_hero)
        draw.text(((WIDTH - (gbbox[2] - gbbox[0])) // 2, center_y - 25), greeting, fill=(255, 255, 255), font=font_hero)

        sub = "Preparing your college templates and project evidence..."
        sbbox = draw.textbbox((0, 0), sub, font=font_body)
        draw.text(((WIDTH - (sbbox[2] - sbbox[0])) // 2, center_y + 65), sub, fill=(160, 160, 180), font=font_body)

    # =========================================================================
    # SCENE 4: DASHBOARD TOUR
    # =========================================================================
    elif scene_id == 4:
        # Mock ARM Workspace Window
        win_x = 180
        win_y = 110
        win_w = 920
        win_h = 500
        draw.rounded_rectangle([win_x, win_y, win_x + win_w, win_y + win_h], radius=12, fill=(16, 16, 20), outline=(40, 40, 50))
        # Top titlebar of mock window
        draw.rounded_rectangle([win_x, win_y, win_x + win_w, win_y + 40], radius=12, fill=(24, 24, 30))
        draw.ellipse([win_x + 16, win_y + 14, win_x + 28, win_y + 26], fill=(239, 68, 68))
        draw.ellipse([win_x + 36, win_y + 14, win_x + 48, win_y + 26], fill=(234, 179, 8))
        draw.ellipse([win_x + 56, win_y + 14, win_x + 68, win_y + 26], fill=(34, 197, 94))
        draw.text((win_x + 84, win_y + 12), "arm.app/workspace — Academic Dashboard", fill=(150, 150, 170), font=font_small)

        # Left Nav items with animated glow
        nav_items = ["⚡ New Report", "📄 Templates", "📁 My Projects", "⚙️ Settings"]
        active_idx = min(3, int(prog * 4.0))
        for i, item in enumerate(nav_items):
            iy = win_y + 65 + i * 50
            if i == active_idx:
                draw.rounded_rectangle([win_x + 16, iy, win_x + 200, iy + 40], radius=8, fill=(16, 40, 30), outline=(52, 211, 153), width=2)
                draw.text((win_x + 30, iy + 8), item, fill=(52, 211, 153), font=font_body)
            else:
                draw.rounded_rectangle([win_x + 16, iy, win_x + 200, iy + 40], radius=8, fill=(22, 22, 28))
                draw.text((win_x + 30, iy + 8), item, fill=(140, 140, 160), font=font_body)

        # Right Main Panel
        draw.rounded_rectangle([win_x + 220, win_y + 60, win_x + win_w - 20, win_y + win_h - 20], radius=10, fill=(12, 12, 16))
        draw.text((win_x + 250, win_y + 85), "Engineering Project Hub", fill=(255, 255, 255), font=font_heading)
        draw.text((win_x + 250, win_y + 130), "Deterministic synthesis for major capstone & IEEE conference papers.", fill=(160, 160, 180), font=font_small)

        # Stat cards
        draw.rounded_rectangle([win_x + 250, win_y + 190, win_x + 520, win_y + 280], radius=8, fill=(20, 20, 26), outline=(52, 211, 153))
        draw.text((win_x + 265, win_y + 205), "Active AI Model", fill=(140, 140, 160), font=font_small)
        draw.text((win_x + 265, win_y + 235), "ARM Academic 2.0", fill=(52, 211, 153), font=font_heading)

        draw.rounded_rectangle([win_x + 550, win_y + 190, win_x + 820, win_y + 280], radius=8, fill=(20, 20, 26), outline=(60, 60, 75))
        draw.text((win_x + 565, win_y + 205), "Institutional Template Lock", fill=(140, 140, 160), font=font_small)
        draw.text((win_x + 565, win_y + 235), "Zero Drift Enforced", fill=(255, 255, 255), font=font_heading)

    # =========================================================================
    # SCENE 5: CREATE PROJECT
    # =========================================================================
    elif scene_id == 5:
        # Intake modal card
        card_w = 760
        card_h = 420
        cx = (WIDTH - card_w) // 2
        cy = (HEIGHT - card_h) // 2
        draw.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=14, fill=(18, 18, 24), outline=(50, 50, 65))
        draw.text((cx + 36, cy + 30), "Create New Academic Project", fill=(255, 255, 255), font=font_heading)
        draw.text((cx + card_w - 140, cy + 36), "Step 1 of 3", fill=(120, 120, 140), font=font_mono_small)
        draw.line([cx + 36, cy + 78, cx + card_w - 36, cy + 78], fill=(35, 35, 45))

        # Title Field Typing simulation
        full_title = "AI Based Irrigation System"
        char_count = int(min(len(full_title), len(full_title) * prog * 1.5))
        typed = full_title[:char_count]
        draw.text((cx + 36, cy + 100), "Project / Report Title", fill=(180, 180, 200), font=font_small)
        draw.rounded_rectangle([cx + 36, cy + 130, cx + card_w - 36, cy + 180], radius=8, fill=(10, 10, 14), outline=(52, 211, 153), width=2)
        draw.text((cx + 52, cy + 142), typed + " |", fill=(255, 255, 255), font=font_mono)

        # Description Field
        draw.text((cx + 36, cy + 205), "Project Description & Objectives", fill=(180, 180, 200), font=font_small)
        draw.rounded_rectangle([cx + 36, cy + 235, cx + card_w - 36, cy + 300], radius=8, fill=(10, 10, 14), outline=(40, 40, 50))
        desc_text = "Automated soil moisture sensing, predictive water dispatch, and IoT edge analytics."
        draw.text((cx + 52, cy + 252), desc_text, fill=(160, 160, 180), font=font_small)

        # Pill Selection
        draw.rounded_rectangle([cx + 36, cy + 330, cx + 290, cy + 372], radius=8, fill=(16, 40, 30), outline=(52, 211, 153), width=2)
        draw.text((cx + 52, cy + 342), "✓ IEEE Major Capstone Report", fill=(52, 211, 153), font=font_small)

    # =========================================================================
    # SCENE 6: UPLOAD COLLEGE TEMPLATE
    # =========================================================================
    elif scene_id == 6:
        title = "Upload your college template"
        tbbox = draw.textbbox((0, 0), title, font=font_title)
        draw.text(((WIDTH - (tbbox[2] - tbbox[0])) // 2, 130), title, fill=(255, 255, 255), font=font_title)

        sub = "Any institutional format: IEEE, Anna Univ, VTU, Mumbai Univ, or Autonomous."
        sbbox = draw.textbbox((0, 0), sub, font=font_body)
        draw.text(((WIDTH - (sbbox[2] - sbbox[0])) // 2, 195), sub, fill=(160, 160, 180), font=font_body)

        # Dropzone box
        box_w = 640
        box_h = 240
        bx = (WIDTH - box_w) // 2
        by = 255
        draw.rounded_rectangle([bx, by, bx + box_w, by + box_h], radius=16, fill=(14, 16, 22), outline=(52, 211, 153), width=2)

        if prog < 0.5:
            draw.text((bx + 180, by + 75), "📥 Dropping DOCX File...", fill=(200, 200, 220), font=font_heading)
            draw.text((bx + 150, by + 130), "College_Major_Project_Template_2026.docx", fill=(52, 211, 153), font=font_mono)
        else:
            draw.text((bx + 200, by + 70), "✓ Template Detected", fill=(52, 211, 153), font=font_heading)
            draw.text((bx + 170, by + 130), "ARM understands your template.", fill=(255, 255, 255), font=font_title)

    # =========================================================================
    # SCENE 7: TEMPLATE ANALYSIS & STRUCTURE PRESERVATION
    # =========================================================================
    elif scene_id == 7:
        title = "Analyzing template..."
        tbbox = draw.textbbox((0, 0), title, font=font_title)
        draw.text(((WIDTH - (tbbox[2] - tbbox[0])) // 2, 75), title, fill=(255, 255, 255), font=font_title)

        # Region tags illuminated sequentially
        tags = ["TEXT", "IMAGES", "LOGO", "BORDERS", "HEADER", "FOOTER", "LAYOUT"]
        tag_x = 240
        for i, tag in enumerate(tags):
            active = prog >= (i * 0.12)
            bg = (24, 48, 36) if active else (18, 18, 22)
            outline = (52, 211, 153) if active else (45, 45, 55)
            tc = (52, 211, 153) if active else (120, 120, 140)
            draw.rounded_rectangle([tag_x, 135, tag_x + 95, 165], radius=6, fill=bg, outline=outline)
            draw.text((tag_x + 12, 142), f"[{tag}]", fill=tc, font=font_mono_small)
            tag_x += 114

        # Scanned Document Wireframe
        doc_w = 780
        doc_h = 340
        dx = (WIDTH - doc_w) // 2
        dy = 185
        draw.rounded_rectangle([dx, dy, dx + doc_w, dy + doc_h], radius=12, fill=(14, 14, 18), outline=(50, 50, 65))

        # Laser Scan Line sweeping down
        laser_y = int(dy + (doc_h - 10) * prog)
        draw.line([dx, laser_y, dx + doc_w, laser_y], fill=(52, 211, 153), width=4)

        # Feature locks
        locks = [
            "🔒 College Header & Official Logo: LOCKED",
            "📐 Margins (1.25\" Left, 1.0\" Right) & Page Borders: PRESERVED",
            "🔤 Typography: Times New Roman 12pt / 1.5 Spacing: ENFORCED",
            "📑 Heading Hierarchy & Roman Page Breaks: PRESERVED",
        ]
        for i, lock in enumerate(locks):
            ly = dy + 30 + i * 58
            draw.rounded_rectangle([dx + 40, ly, dx + doc_w - 40, ly + 44], radius=8, fill=(22, 24, 30), outline=(52, 211, 153))
            draw.text((dx + 60, ly + 10), lock, fill=(255, 255, 255), font=font_body)

        if prog > 0.7:
            footer = "Template understood. Structure preserved 100%."
        else:
            footer = "Structure preserved 100%. No redesign."
        fbbox = draw.textbbox((0, 0), footer, font=font_heading)
        draw.text(((WIDTH - (fbbox[2] - fbbox[0])) // 2, dy + doc_h + 20), footer, fill=(52, 211, 153), font=font_heading)

    # =========================================================================
    # SCENE 8: ADD EVIDENCE
    # =========================================================================
    elif scene_id == 8:
        title = "Add your project evidence"
        tbbox = draw.textbbox((0, 0), title, font=font_title)
        draw.text(((WIDTH - (tbbox[2] - tbbox[0])) // 2, 120), title, fill=(255, 255, 255), font=font_title)

        sub = "Attach real student datasets, schematics, source code, and IEEE citations."
        sbbox = draw.textbbox((0, 0), sub, font=font_body)
        draw.text(((WIDTH - (sbbox[2] - sbbox[0])) // 2, 185), sub, fill=(160, 160, 180), font=font_body)

        chips = [
            ("📊 soil_telemetry.csv", "12,400 sensor readings", (34, 211, 238)),
            ("🖼️ irrigation_circuit.png", "Hardware schematic", (52, 211, 153)),
            ("💻 esp32_firmware.ino", "Embedded edge C++", (250, 204, 21)),
            ("📄 ieee_citations.bib", "24 Peer-reviewed papers", (168, 85, 247)),
        ]
        grid_w = 340
        grid_h = 90
        coords = [
            (center_x - 360, 270),
            (center_x + 20, 270),
            (center_x - 360, 390),
            (center_x + 20, 390),
        ]
        for i, (fn, info, col) in enumerate(chips):
            gx, gy = coords[i]
            draw.rounded_rectangle([gx, gy, gx + grid_w, gy + grid_h], radius=10, fill=(18, 18, 24), outline=col, width=2)
            draw.text((gx + 20, gy + 18), fn, fill=(255, 255, 255), font=font_body)
            draw.text((gx + 20, gy + 52), info, fill=(140, 140, 160), font=font_small)

    # =========================================================================
    # SCENE 9: AI THINKING
    # =========================================================================
    elif scene_id == 9:
        # Rotating neural circle with particles
        nr = 42
        angle = t * 3.0
        draw.ellipse([center_x - nr, 130 - nr, center_x + nr, 130 + nr], fill=(18, 36, 26), outline=(52, 211, 153), width=2)
        px = int(center_x + (nr + 12) * math.cos(angle))
        py = int(130 + (nr + 12) * math.sin(angle))
        draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=(52, 211, 153))

        # Multi-step progress cards with exact requested text
        steps = [
            ("Thinking...", prog >= 0.08),
            ("Understanding your project...", prog >= 0.38),
            ("Creating your report...", prog >= 0.70),
        ]
        box_w = 680
        bx = (WIDTH - box_w) // 2
        for i, (msg, active) in enumerate(steps):
            by = 200 + i * 85
            if active:
                draw.rounded_rectangle([bx, by, bx + box_w, by + 65], radius=10, fill=(16, 36, 26), outline=(52, 211, 153), width=2)
                draw.text((bx + 30, by + 18), "✓ " + msg, fill=(52, 211, 153), font=font_heading)
            else:
                draw.rounded_rectangle([bx, by, bx + box_w, by + 65], radius=10, fill=(18, 18, 22), outline=(40, 40, 50))
                draw.text((bx + 30, by + 18), "○ " + msg, fill=(100, 100, 120), font=font_heading)

    # =========================================================================
    # SCENE 10: INTELLIGENT REPLACEMENT (CORE HERO SCENE)
    # =========================================================================
    elif scene_id == 10:
        if prog < 0.35:
            phrase = "Replace content."
        elif prog < 0.70:
            phrase = "Replace content. Preserve design."
        else:
            phrase = "Replace content. Preserve design. Automatically."

        tbbox = draw.textbbox((0, 0), phrase, font=font_title)
        draw.text(((WIDTH - (tbbox[2] - tbbox[0])) // 2, 90), phrase, fill=(255, 255, 255), font=font_title)

        # Tri-stage Flow Cards
        col_w = 340
        col_h = 240
        c1_x = 80
        c2_x = 470
        c3_x = 860
        cy = 190

        # Card 1: Old Content
        draw.rounded_rectangle([c1_x, cy, c1_x + col_w, cy + col_h], radius=12, fill=(20, 14, 16), outline=(239, 68, 68), width=2)
        draw.text((c1_x + 20, cy + 20), "1. PREVIOUS SENIOR CONTENT", fill=(239, 68, 68), font=font_mono_small)
        draw.text((c1_x + 20, cy + 60), "Smart Home Automation", fill=(180, 140, 140), font=font_body)
        draw.text((c1_x + 20, cy + 100), "Chapter 3: Appliance relay control logic\nand legacy code...", fill=(120, 100, 100), font=font_small)
        draw.text((c1_x + 20, cy + 180), "Dissolving out...", fill=(239, 68, 68), font=font_mono_small)

        # Card 2: ARM AI Core
        draw.rounded_rectangle([c2_x, cy, c2_x + col_w, cy + col_h], radius=12, fill=(16, 32, 24), outline=(52, 211, 153), width=2)
        draw.text((c2_x + 60, cy + 30), "ARM AI ENGINE", fill=(52, 211, 153), font=font_heading)
        draw.text((c2_x + 30, cy + 95), "Semantic Alignment Engine", fill=(255, 255, 255), font=font_body)
        draw.text((c2_x + 30, cy + 140), "Deterministic slot replacement\nwith zero layout drift", fill=(160, 200, 180), font=font_small)

        # Card 3: New Content
        draw.rounded_rectangle([c3_x, cy, c3_x + col_w, cy + col_h], radius=12, fill=(16, 26, 22), outline=(52, 211, 153), width=2)
        draw.text((c3_x + 20, cy + 20), "2. NEW PROJECT CONTENT", fill=(52, 211, 153), font=font_mono_small)
        draw.text((c3_x + 20, cy + 60), "AI Based Irrigation System", fill=(255, 255, 255), font=font_body)
        draw.text((c3_x + 20, cy + 100), "Chapter 3: Predictive moisture modeling\nand IoT edge dispatch...", fill=(180, 220, 200), font=font_small)
        draw.text((c3_x + 20, cy + 180), "Inserted in exact font & margin", fill=(52, 211, 153), font=font_mono_small)

        # Preserved items row
        p_text = "✓ Borders  ✓ Logos  ✓ Headers & Footers  ✓ Times New Roman  ✓ Margins: Preserved"
        draw.text((160, 480), p_text, fill=(200, 200, 220), font=font_body)

    # =========================================================================
    # SCENE 11: BEFORE / AFTER (Animated Split Scan Wipe)
    # =========================================================================
    elif scene_id == 11:
        title = "Same template. New project content."
        tbbox = draw.textbbox((0, 0), title, font=font_title)
        draw.text(((WIDTH - (tbbox[2] - tbbox[0])) // 2, 90), title, fill=(255, 255, 255), font=font_title)

        split_w = 520
        split_h = 420
        # Left: Original Template
        draw.rounded_rectangle([90, 170, 90 + split_w, 170 + split_h], radius=12, fill=(18, 18, 22), outline=(60, 60, 75))
        draw.text((120, 200), "ORIGINAL COLLEGE TEMPLATE", fill=(140, 140, 160), font=font_mono_small)
        draw.text((120, 240), "Unmodified College Layout", fill=(200, 200, 210), font=font_heading)
        draw.text((120, 300), "• Official Margins & Geometry\n• Department Seal & Headings\n• Sample / Senior Project Content", fill=(150, 150, 170), font=font_body)

        # Right: ARM Generated Report
        draw.rounded_rectangle([670, 170, 670 + split_w, 170 + split_h], radius=12, fill=(14, 26, 20), outline=(52, 211, 153), width=2)
        draw.text((700, 200), "ARM GENERATED REPORT", fill=(52, 211, 153), font=font_mono_small)
        draw.text((700, 240), "AI Based Irrigation System", fill=(255, 255, 255), font=font_heading)
        draw.text((700, 300), "• 100% Identical College Margins\n• Preserved Official Seal\n• Student's Real Sensor & Code Chapters", fill=(200, 240, 220), font=font_body)

        # Wipe Divider Line Sweeping across
        wipe_x = int(90 + (1100) * prog)
        draw.line([wipe_x, 160, wipe_x, 600], fill=(52, 211, 153), width=3)


    # =========================================================================
    # SCENE 12: REPORT GENERATION
    # =========================================================================
    elif scene_id == 12:
        title = "Report ready."
        tbbox = draw.textbbox((0, 0), title, font=font_hero)
        draw.text(((WIDTH - (tbbox[2] - tbbox[0])) // 2, 130), title, fill=(52, 211, 153), font=font_hero)

        sub = "Zero layout drift. Verification and citations confirmed."
        sbbox = draw.textbbox((0, 0), sub, font=font_body)
        draw.text(((WIDTH - (sbbox[2] - sbbox[0])) // 2, 230), sub, fill=(180, 180, 200), font=font_body)

        # Two compiled output badges
        draw.rounded_rectangle([260, 310, 600, 440], radius=14, fill=(16, 24, 36), outline=(59, 130, 246), width=2)
        draw.text((300, 340), "📄 Project_Report.docx", fill=(255, 255, 255), font=font_heading)
        draw.text((300, 390), "Microsoft Word • Fully Editable", fill=(147, 197, 253), font=font_small)

        draw.rounded_rectangle([680, 310, 1020, 440], radius=14, fill=(32, 16, 18), outline=(239, 68, 68), width=2)
        draw.text((720, 340), "📕 Project_Report.pdf", fill=(255, 255, 255), font=font_heading)
        draw.text((720, 390), "Print Ready • Verified Margins", fill=(252, 165, 165), font=font_small)

    # =========================================================================
    # SCENE 13: HERO FINALE
    # =========================================================================
    elif scene_id == 13:
        tagline = "From college template... to complete project report."
        tbbox = draw.textbbox((0, 0), tagline, font=font_body)
        draw.text(((WIDTH - (tbbox[2] - tbbox[0])) // 2, 140), tagline, fill=(160, 160, 180), font=font_body)

        hero = "ARM"
        hbbox = draw.textbbox((0, 0), hero, font=font_hero)
        draw.text(((WIDTH - (hbbox[2] - hbbox[0])) // 2, 200), hero, fill=(255, 255, 255), font=font_hero)

        sub = "Academic Report Made Intelligent"
        sbbox = draw.textbbox((0, 0), sub, font=font_title)
        draw.text(((WIDTH - (sbbox[2] - sbbox[0])) // 2, 300), sub, fill=(52, 211, 153), font=font_title)

        cta = "Create. Analyze. Generate."
        cbbox = draw.textbbox((0, 0), cta, font=font_heading)
        cx = (WIDTH - (cbbox[2] - cbbox[0])) // 2
        draw.rounded_rectangle([cx - 30, 400, cx + (cbbox[2] - cbbox[0]) + 30, 460], radius=30, fill=(255, 255, 255))
        draw.text((cx, 412), cta, fill=(10, 10, 12), font=font_heading)

    draw_bottom_timeline(draw, t)
    return np.array(img)

def generate_audio():
    """Synthesizes high-fidelity ambient track + whooshes + chime in WAV format."""
    total_samples = int(DURATION * SAMPLE_RATE)
    audio = np.zeros(total_samples, dtype=np.float32)
    t = np.linspace(0, DURATION, total_samples, endpoint=False)

    # 1. Warm ambient low sine drone (65Hz + 130Hz)
    ambient = 0.04 * np.sin(2 * np.pi * 65 * t) + 0.02 * np.sin(2 * np.pi * 130 * t)
    # Slow gentle volume swell
    envelope = np.clip(t / 2.0, 0, 1.0) * np.clip((DURATION - t) / 2.0, 0, 1.0)
    audio += ambient * envelope

    # 2. Add whoosh transitions at scene boundaries
    for s in SCENES:
        st = s["start"]
        if st > 0.5:
            start_idx = int(st * SAMPLE_RATE)
            whoosh_len = int(0.35 * SAMPLE_RATE)
            if start_idx + whoosh_len < total_samples:
                wt = np.linspace(0, 0.35, whoosh_len, endpoint=False)
                noise = np.random.normal(0, 0.06, whoosh_len) * np.exp(-wt * 9)
                freq_sweep = np.sin(2 * np.pi * (400 - 300 * (wt / 0.35)) * wt) * 0.05
                audio[start_idx:start_idx + whoosh_len] += (noise + freq_sweep).astype(np.float32)

    # 3. Add success chime at scene 12 (t=36.2s)
    chime_start = int(36.2 * SAMPLE_RATE)
    chime_len = int(1.2 * SAMPLE_RATE)
    if chime_start + chime_len < total_samples:
        ct = np.linspace(0, 1.2, chime_len, endpoint=False)
        chord = (0.08 * np.sin(2 * np.pi * 523.25 * ct) +   # C5
                 0.08 * np.sin(2 * np.pi * 659.25 * ct) +   # E5
                 0.08 * np.sin(2 * np.pi * 783.99 * ct))    # G5
        chord *= np.exp(-ct * 3.5)
        audio[chime_start:chime_start + chime_len] += chord.astype(np.float32)

    # Normalize and write WAV (16-bit PCM)
    audio = np.clip(audio, -0.95, 0.95)
    audio_int16 = (audio * 32767).astype(np.int16)

    import wave
    with wave.open(TEMP_AUDIO, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_int16.tobytes())
    print(f"Generated audio WAV: {TEMP_AUDIO}")

def main():
    print(f"Rendering ARM Motion Graphics Video ({TOTAL_FRAMES} frames @ {FPS} fps)...")
    os.makedirs(os.path.dirname(OUTPUT_MP4), exist_ok=True)

    # 1. Generate Audio WAV first
    generate_audio()

    # 2. Start FFmpeg process reading rawvideo from stdin and audio from TEMP_AUDIO
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-i", TEMP_AUDIO,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        OUTPUT_MP4
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    for i in range(TOTAL_FRAMES):
        frame = render_frame(i)
        proc.stdin.write(frame.tobytes())
        if i % (FPS * 5) == 0:
            print(f"  Rendered {i}/{TOTAL_FRAMES} frames ({(i/TOTAL_FRAMES)*100:.1f}%)...")

    proc.stdin.close()
    proc.wait()
    print("Video frames encoded and muxed successfully.")

    if os.path.exists(TEMP_AUDIO):
        os.remove(TEMP_AUDIO)

    file_size = os.path.getsize(OUTPUT_MP4)
    print(f"SUCCESS: Rendered official playable MP4 video: {OUTPUT_MP4} ({file_size / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    main()

