"""
caption_styles.py — Font and color palette definitions

Each font entry:
  ffmpeg_name   : font family name for FFmpeg's drawtext filter
  css_fallback  : CSS font-family fallback for Streamlit UI preview
  path          : (optional) absolute path to a bundled .ttf file

Each color entry:
  hex     : text color in #RRGGBB
  ffmpeg  : hex color in FFmpeg format (0xRRGGBB or with alpha 0xRRGGBBAA)
  bg      : background box color for UI preview
  bg_ffmpeg: FFmpeg box color (with transparency)
"""

FONT_OPTIONS = {
    # 1. Clean modern sans-serif
    "Bold & Clean (Arial Bold)": {
        "ffmpeg_name": "Arial-Bold",
        "css_fallback": "Arial Black, Arial, sans-serif",
        "path": None,  # system font
    },
    # 2. Classic subtitle look
    "Classic Subtitle (DejaVu Sans)": {
        "ffmpeg_name": "DejaVu-Sans-Bold",
        "css_fallback": "DejaVu Sans, Verdana, sans-serif",
        "path": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    },
    # 3. Monospace / tech look
    "Mono Code (Courier Bold)": {
        "ffmpeg_name": "Courier-Bold",
        "css_fallback": "'Courier New', Courier, monospace",
        "path": None,
    },
    # 4. Elegant serif
    "Elegant Serif (Liberation Serif)": {
        "ffmpeg_name": "LiberationSerif-Bold",
        "css_fallback": "Georgia, 'Times New Roman', serif",
        "path": "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    },
    # 5. Rounded friendly
    "Friendly Rounded (Ubuntu Bold)": {
        "ffmpeg_name": "Ubuntu-Bold",
        "css_fallback": "Ubuntu, Tahoma, sans-serif",
        "path": "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    },
}

COLOR_OPTIONS = {
    # 1. Classic white on black box
    "White on Black": {
        "hex":       "#FFFFFF",
        "ffmpeg":    "white",
        "bg":        "#000000",
        "bg_ffmpeg": "black@0.65",
    },
    # 2. Bright yellow (news / documentary style)
    "Yellow on Black": {
        "hex":       "#FFE600",
        "ffmpeg":    "yellow",
        "bg":        "#000000",
        "bg_ffmpeg": "black@0.65",
    },
    # 3. Cyan on dark (Netflix-style)
    "Cyan on Dark": {
        "hex":       "#00E5FF",
        "ffmpeg":    "0x00E5FF",
        "bg":        "#111111",
        "bg_ffmpeg": "0x111111@0.70",
    },
    # 4. Orange pop
    "Orange on Black": {
        "hex":       "#FF6B35",
        "ffmpeg":    "0xFF6B35",
        "bg":        "#000000",
        "bg_ffmpeg": "black@0.65",
    },
    # 5. Lime green (gaming / energetic)
    "Lime on Dark": {
        "hex":       "#ADFF2F",
        "ffmpeg":    "0xADFF2F",
        "bg":        "#0D1117",
        "bg_ffmpeg": "0x0D1117@0.75",
    },
}

# Caption vertical positions mapped to FFmpeg y expressions
POSITION_MAP = {
    "Top":    "h*0.05",
    "Middle": "(h-text_h)/2",
    "Bottom": "h-text_h-h*0.05",
}
