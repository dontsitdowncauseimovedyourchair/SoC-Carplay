"""Application-wide GTK styles."""

from gi.repository import Gdk, Gtk
from colorthief import ColorThief


def load_all_css():
    try:
        color_thief = ColorThief("album.jpg")
        r, g, b = color_thief.get_color(quality=1)
    except:
        r, g, b = 105, 17, 173  # Morado #6911AD
    dark_r, dark_g, dark_b = max(r - 70, 0), max(g - 70, 0), max(b - 70, 0)
    css = f"""
    * {{
        font-family: "Pixel Operator";
    }}
    .music-background {{
        background-image: linear-gradient(135deg, rgba({r},{g},{b},0.95),
        rgba({dark_r},{dark_g},{dark_b},0.95));
    }}
    .sidebar-music {{ background: transparent; border-radius: 0px; padding: 20px; }}
    .dashboard-music {{ background: rgba(255,255,255,0.1); border-radius: 0px; padding: 30px; }}
    .clock-label {{ color: white; font-size: 80px; font-weight: 900; }}

    .dock-button {{
        background: transparent;
        border: none;
        box-shadow: none;
        font-size: 35px;
        color: white;
        min-width: 80px;
        min-height: 80px;
    }}
    .circle-button {{
        background: rgba(255,255,255,0.1);
        border-radius: 0px;
        min-width: 80px; min-height: 80px;
        font-size: 30px; color: white; border: none;
    }}
    .date-label {{
        color: rgba(255,255,255,0.75);
        font-size: 50px;
        font-weight: 500;
    }}
    .clock-label {{
        color: white;
        font-family: "Pixel Operator HB 8";
        font-size: 120px;
        font-weight: 900;
    }}
    .hero-song {{
        font-size: 70px;
        font-weight: 900;
        color: white;
    }}
    .hero-artist {{
        font-size: 50px;
        color: rgba(255,255,255,0.75);
    }}
    .home-song {{
        font-size: 40px;
        font-weight: 700;
        color: white;
    }}

    .home-artist {{
        font-size: 30px;
        color: rgba(255,255,255,0.7);
    }}
    .transport-button {{
        background: transparent;
        border: none;
        box-shadow: none;
        font-size: 20px;
        color: white;
        min-height: 80px;
        min-width: 80px;
    }}
    .floating-dock {{
        background: rgba(255,255,255,0.20);
        border-radius: 0px;
        padding: 14px 28px;
    }}
    .dock-button {{
        background: transparent;
        border: none;
        box-shadow: none;
        padding: 12px;
    }}
    .dock-button:hover {{
        background: rgba(255,255,255,0.25);
        border-radius: 0px;
    }}

    /* Temperature widget */
    .temp-card {{
        background: rgba(255,255,255,0.12);
        border-radius: 0px;
        padding: 16px 22px;
    }}
    .temp-value {{
        color: white;
        font-size: 60px;
        font-weight: 900;
    }}
    .temp-label {{
        color: rgba(255,255,255,0.70);
        font-size: 30px;
        font-weight: 500;
    }}
    .temp-city {{
        color: rgba(255,255,255,0.85);
        font-size: 30px;
        font-weight: 600;
    }}

    .ai-status-bubble {{
        background: rgba(11, 12, 16, 0.85);
        color: #66FCF1;
        border-radius: 20px;
        padding: 15px 30px;
        font-size: 35px;
        font-weight: bold;
    }}
    
    .temp-cabin {{
        color: white;
        font-size: 28px;
        font-weight: 700;
    }}
    .gps-chip {{
        background: rgba(11, 12, 16, 0.75);
        color: rgba(255,255,255,0.55);
        padding: 8px 18px;
        font-size: 24px;
        font-weight: bold;
    }}
    .gps-ok {{ color: #00ff88; }}
    .distance-chip {{
        background: rgba(11, 12, 16, 0.75);
        padding: 10px 30px;
        font-size: 56px;
        font-weight: 900;
    }}
    .dist-far  {{ color: #00ff88; }}
    .dist-mid  {{ color: #ffe14d; }}
    .dist-near {{ color: #ff5555; }}
    """
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode())
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, 800
    )
