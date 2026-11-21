"""Export the static product website for another host, optionally rewriting its public origin."""
import argparse
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "sites/superturiya/dist"
CURRENT_ORIGIN = "https://superturiya.piyushunt.chatgpt.site"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default=CURRENT_ORIGIN, help="Actual HTTPS origin of your future website; no path")
    parser.add_argument("--output", default="output/superturiya-website.zip")
    args = parser.parse_args()
    origin = args.origin.rstrip("/")
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment or parsed.port:
        parser.error("origin must be an HTTPS hostname without credentials, port, path or query")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as destination, zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(SITE.rglob("*")):
            if not file.is_file() or file.name.startswith("."):
                continue
            data = file.read_bytes()
            if file.suffix in {".html", ".xml", ".txt", ".js", ".css"}:
                data = data.decode("utf-8").replace(CURRENT_ORIGIN, origin).encode("utf-8")
            archive.writestr(file.relative_to(SITE).as_posix(), data)
    print(str(output.resolve()))
    print("Static website packaged. No files were published or changed in the current Site.")


if __name__ == "__main__": main()
