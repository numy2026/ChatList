"""Создание иконки приложения: зелёный четырёхлистник."""

from PIL import Image, ImageDraw


def draw_icon(size: int) -> Image.Image:
    """Рисует зелёный четырёхлистник (4 круга-листа) на светлом фоне."""
    img = Image.new("RGB", (size, size), (245, 252, 245))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    leaf_radius = int(size * 0.32)
    offset = int(size * 0.12)
    green = (34, 139, 34)

    # Четыре листа: правый, верхний, левый, нижний
    positions = [
        (cx + offset, cy),           # правый
        (cx, cy - offset),           # верхний
        (cx - offset, cy),           # левый
        (cx, cy + offset),           # нижний
    ]
    for lx, ly in positions:
        box = (
            lx - leaf_radius,
            ly - leaf_radius,
            lx + leaf_radius,
            ly + leaf_radius,
        )
        draw.ellipse(box, fill=green)

    return img


def main() -> None:
    sizes = [256, 128, 64, 48, 32, 16]
    icons = [draw_icon(s) for s in sizes]
    rgb_icons = []
    for icon in icons:
        rgb_icons.append(icon if icon.mode == "RGB" else icon.convert("RGB"))

    ico_sizes = [(s, s) for s in sizes]
    try:
        rgb_icons[0].save(
            "app.ico",
            format="ICO",
            sizes=ico_sizes,
            append_images=rgb_icons[1:],
        )
        print("✅ app.ico создана")
    except Exception as e:
        print(f"❌ ICO: {e}")
        rgb_icons[0].save("app.ico", format="ICO")
    rgb_icons[0].save("app_icon.png", format="PNG")
    print("✅ app_icon.png создана (для окна и Dock)")


if __name__ == "__main__":
    main()
