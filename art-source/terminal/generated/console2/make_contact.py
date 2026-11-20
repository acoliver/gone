import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a photo, generated keyboard and design top-view contact sheet."
    )
    parser.add_argument("photo", type=Path, help="Original product photo")
    parser.add_argument("generated", type=Path, help="Generated keyboard image")
    parser.add_argument("design", type=Path, help="Keyboard design top view")
    parser.add_argument("output", type=Path, help="Contact-sheet output PNG")
    args = parser.parse_args()
    inputs = [args.photo, args.generated, args.design]
    missing = [path for path in inputs if not path.is_file()]
    if missing:
        parser.error(
            "missing input(s): " + ", ".join(str(path) for path in missing)
        )

    items = [
        ("Photo", args.photo),
        ("Generated keyboard", args.generated),
        ("Design top view", args.design),
    ]
    width, height = 900, 540
    canvas = Image.new("RGB", (width * 3, height + 50), (238, 238, 232))
    draw = ImageDraw.Draw(canvas)
    for index, (title, path) in enumerate(items):
        image = Image.open(path).convert("RGB")
        image.thumbnail((width - 24, height - 20))
        x = index * width + (width - image.width) // 2
        y = 50 + (height - image.height) // 2
        canvas.paste(image, (x, y))
        draw.text((index * width + 18, 15), title, fill=(25, 25, 25))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output)


if __name__ == "__main__":
    main()
