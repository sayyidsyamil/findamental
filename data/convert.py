import sys
from pathlib import Path
from markitdown import MarkItDown


def convert_to_markdown(input_path: str, output_path: str | None = None) -> str:
    md = MarkItDown()
    result = md.convert(input_path)

    if output_path:
        Path(output_path).write_text(result.text_content)
        print(f"Saved to {output_path}")
    else:
        print(result.text_content)

    return result.text_content


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert.py <input-file> [-o output.md]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "-o" else None
    convert_to_markdown(input_path, output_path)
