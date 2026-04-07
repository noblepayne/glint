"""
CLI - Command line interface for glint.
"""

import argparse
import sys
from pathlib import Path

from .filters import FILTERS, list_filters, get_filter
from .apply import apply_to_path, load_image
from .lut import save_cube
from . import llm, vision
from .types import FilterParams


def cmd_list(args: argparse.Namespace) -> int:
    """List available filters."""
    filters = list_filters()
    print(f"Available filters ({len(filters)}):\n")
    for name, desc in filters:
        print(f"  {name:20} - {desc}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    """Apply filter to an image."""
    input_path = Path(args.input) if args.input else None
    output_path = args.output

    params: FilterParams = {}

    if args.filter:
        preset = get_filter(args.filter)
        if preset is None:
            print(f"Error: Unknown filter '{args.filter}'", file=sys.stderr)
            return 1
        params = dict(preset)

    if args.contrast is not None:
        params["contrast"] = args.contrast
    if args.brightness is not None:
        params["brightness"] = args.brightness
    if args.saturation is not None:
        params["saturation"] = args.saturation
    if args.fade is not None:
        params["fade"] = args.fade
    if args.grain is not None:
        params["grain"] = args.grain
    if args.temperature is not None:
        params["temperature"] = args.temperature
    if args.vignette is not None:
        params["vignette"] = args.vignette
    if args.highlights is not None:
        params["highlights"] = args.highlights
    if args.shadows is not None:
        params["shadows"] = args.shadows
    if args.tint_r is not None or args.tint_g is not None or args.tint_b is not None:
        tint = {}
        if args.tint_r is not None:
            tint["r"] = args.tint_r
        if args.tint_g is not None:
            tint["g"] = args.tint_g
        if args.tint_b is not None:
            tint["b"] = args.tint_b
        params["tint"] = tint

    # If no input image, just show what would be applied
    if input_path is None:
        print("Filter params:")
        for key, value in sorted(params.items()):
            print(f"  {key}: {value}")
        return 0

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    if output_path is None:
        output_path = (
            input_path.parent / f"{input_path.stem}_filtered{input_path.suffix}"
        )
    else:
        output_path = Path(output_path)

    strength = args.strength if args.strength else 1.0

    print(f"Applying filter to: {input_path}")
    if params.get("name"):
        print(f"  Base filter: {params['name']}")
    if strength != 1.0:
        print(f"  Strength: {strength}")
    print(f"  Output: {output_path}")

    from PIL import Image
    from .apply import apply_to_image

    img = load_image(input_path)
    result = apply_to_image(img, params)

    if strength < 1.0:
        result = Image.blend(img, result, alpha=strength)

    result.save(output_path)
    print("Done!")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate filter from LLM prompt."""
    print(f"Generating filter from: '{args.prompt}'")
    print(f"  Model: {args.model}")

    try:
        params = llm.generate_from_prompt(args.prompt, model=args.model)
    except Exception as e:
        print(f"Error generating filter: {e}", file=sys.stderr)
        return 1

    print("Generated params:")
    for key, value in sorted(params.items()):
        print(f"  {key}: {value}")

    if args.save:
        filter_name = args.save
        params["name"] = filter_name
        FILTERS[filter_name] = params

        config_path = Path(__file__).parent / "filters.py"
        print(f"\nSaved to FILTERS dict (in memory). To persist, add to {config_path}:")
        print(f'    "{filter_name}": {params!r},')

    if args.apply:
        if not args.image:
            print("Error: --image required when using --apply", file=sys.stderr)
            return 1

        input_path = Path(args.image)
        if not input_path.exists():
            print(f"Error: Image not found: {input_path}", file=sys.stderr)
            return 1

        output_path = (
            args.output
            or input_path.parent / f"{input_path.stem}_generated{input_path.suffix}"
        )

        print(f"\nApplying to: {input_path}")
        apply_to_path(input_path, params, Path(output_path))
        print(f"Saved to: {output_path}")

    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export filter to .cube file."""
    filter_name = args.filter
    preset = get_filter(filter_name)

    if preset is None:
        print(f"Error: Unknown filter '{filter_name}'", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else Path(f"{filter_name}.cube")

    size = args.size

    print(f"Exporting '{filter_name}' to {output_path} (size={size})")
    save_cube(dict(preset), output_path, size=size)
    print("Done!")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Start the web server."""
    import uvicorn
    from . import server

    print(f"Starting server on {args.host}:{args.port}")
    print(f"Open http://localhost:{args.port} in your browser")

    uvicorn.run(server.app, host=args.host, port=args.port)
    print("Done!")
    return 0


def cmd_auto_fix(args: argparse.Namespace) -> int:
    """Auto-fix image using Gemma 4 vision model."""

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    output_path = args.output
    if output_path is None:
        output_path = (
            input_path.parent / f"{input_path.stem}_autofix{input_path.suffix}"
        )
    else:
        output_path = Path(output_path)

    print(f"Loading: {input_path}")
    img = load_image(input_path)

    print(f"Running vision auto-fix (rounds={args.rounds}, focus={args.focus})...")

    params = vision.auto_fix(
        img,
        max_rounds=args.rounds,
        focus=args.focus,
    )

    print("Generated params:")
    for key, value in sorted(params.items()):
        print(f"  {key}: {value}")

    from .apply import apply_to_image

    result = apply_to_image(img, params)
    result.save(output_path)

    print(f"Saved to: {output_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="glint - Image filter pipeline with LLM support",
        prog="glint",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    list_parser = subparsers.add_parser("list", help="List available filters")
    list_parser.set_defaults(func=cmd_list)

    apply_parser = subparsers.add_parser("apply", help="Apply filter to image")
    apply_parser.add_argument("filter", nargs="?", help="Preset filter name (optional)")
    apply_parser.add_argument(
        "input", nargs="?", help="Input image path (optional if using --params)"
    )
    apply_parser.add_argument("-o", "--output", help="Output path")
    apply_parser.add_argument("--contrast", type=float, help="Contrast (0.5-1.5)")
    apply_parser.add_argument(
        "--brightness", type=float, help="Brightness (-0.2 to 0.2)"
    )
    apply_parser.add_argument("--saturation", type=float, help="Saturation (0.5-1.5)")
    apply_parser.add_argument("--fade", type=float, help="Fade amount (0-0.5)")
    apply_parser.add_argument("--grain", type=float, help="Grain amount (0-0.5)")
    apply_parser.add_argument(
        "--temperature", type=float, help="Temperature (-0.3 to 0.3)"
    )
    apply_parser.add_argument("--vignette", type=float, help="Vignette (0-0.5)")
    apply_parser.add_argument(
        "--highlights", type=float, help="Highlights (-0.2 to 0.2)"
    )
    apply_parser.add_argument("--shadows", type=float, help="Shadows (-0.2 to 0.2)")
    apply_parser.add_argument("--tint-r", type=float, help="Tint red offset")
    apply_parser.add_argument("--tint-g", type=float, help="Tint green offset")
    apply_parser.add_argument("--tint-b", type=float, help="Tint blue offset")
    apply_parser.add_argument(
        "--strength", type=float, default=1.0, help="Filter strength 0-1 (default 1.0)"
    )
    apply_parser.set_defaults(func=cmd_apply)

    generate_parser = subparsers.add_parser("generate", help="Generate filter from LLM")
    generate_parser.add_argument("prompt", help="Description of desired look")
    generate_parser.add_argument(
        "-m", "--model", default=llm.DEFAULT_MODEL, help="Model to use"
    )
    generate_parser.add_argument(
        "--save", metavar="NAME", help="Save to filters under this name"
    )
    generate_parser.add_argument("--apply", action="store_true", help="Apply to image")
    generate_parser.add_argument("--image", help="Image path for --apply")
    generate_parser.add_argument("-o", "--output", help="Output path for --apply")
    generate_parser.set_defaults(func=cmd_generate)

    export_parser = subparsers.add_parser("export", help="Export filter to .cube")
    export_parser.add_argument("filter", help="Filter name to export")
    export_parser.add_argument("-o", "--output", help="Output .cube file path")
    export_parser.add_argument(
        "--size", type=int, default=33, help="LUT size (default 33)"
    )
    export_parser.set_defaults(func=cmd_export)

    serve_parser = subparsers.add_parser("serve", help="Start web server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    serve_parser.add_argument(
        "--port", type=int, default=8000, help="Port to listen on"
    )
    serve_parser.set_defaults(func=cmd_serve)

    auto_fix_parser = subparsers.add_parser(
        "auto-fix", help="Auto-fix image with Gemma 4 vision"
    )
    auto_fix_parser.add_argument("input", help="Input image path")
    auto_fix_parser.add_argument("-o", "--output", help="Output path")
    auto_fix_parser.add_argument(
        "--rounds", type=int, default=3, help="Refinement rounds (1-5, default 3)"
    )
    auto_fix_parser.add_argument(
        "--focus",
        default="pop",
        choices=["pop", "moody", "warmer", "cooler", "fade", "boost_contrast"],
        help="Enhancement style (default: pop)",
    )
    auto_fix_parser.set_defaults(func=cmd_auto_fix)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
