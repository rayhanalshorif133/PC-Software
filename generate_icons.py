from PIL import Image, ImageDraw
import os

os.makedirs('icons', exist_ok=True)

sizes = [16, 48, 128]

for size in sizes:
    # High-res canvas for antialiased downsampling
    scale = 4
    canvas_size = size * scale
    img = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Outer rounded rectangle (Red recording theme with modern gradient feel)
    pad = int(canvas_size * 0.08)
    corner_radius = int(canvas_size * 0.22)
    draw.rounded_rectangle(
        [pad, pad, canvas_size - pad, canvas_size - pad],
        radius=corner_radius,
        fill='#E53935'
    )
    
    # Inner white tab/browser window outline
    tab_pad_x = int(canvas_size * 0.22)
    tab_top = int(canvas_size * 0.22)
    tab_bottom = int(canvas_size * 0.78)
    tab_radius = int(canvas_size * 0.1)
    
    # Draw a stylized camera / tab record icon
    # White circle in center (record symbol)
    center = canvas_size // 2
    rec_radius = int(canvas_size * 0.26)
    draw.ellipse(
        [center - rec_radius, center - rec_radius, center + rec_radius, center + rec_radius],
        fill='#FFFFFF'
    )
    
    # Inner red dot
    inner_radius = int(canvas_size * 0.15)
    draw.ellipse(
        [center - inner_radius, center - inner_radius, center + inner_radius, center + inner_radius],
        fill='#E53935'
    )
    
    # Downsample with Lanczos for smooth crisp edges
    resampled = img.resize((size, size), Image.Resampling.LANCZOS)
    resampled.save(f'icons/icon-{size}.png', 'PNG')
    print(f'Generated icons/icon-{size}.png ({size}x{size})')

print('All icons generated successfully!')

