"""Download only original n-back members using HTTP ranges; verify ZIP CRCs."""
import argparse
import concurrent.futures
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import urllib.request
import zipfile
import zlib


def fetch(url, start=None, end=None):
    value = "bytes=-65536" if start is None else f"bytes={start}-{end}"
    req = urllib.request.Request(url, headers={"Range": value})
    with urllib.request.urlopen(req, timeout=120) as response:
        if response.status != 206:
            raise RuntimeError("Server did not honor byte range; refusing full archive in memory.")
        return response.read(), dict(response.headers)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", type=int, default=1)
    parser.add_argument("--out", type=Path, default=Path("data/shin2018/VP001"))
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    url = f"https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/EEG/VP{args.subject:03d}.zip"
    tail, headers = fetch(url)
    content_range = next(v for k, v in headers.items() if k.lower() == "content-range")
    total = int(content_range.split("/")[-1])
    index = zipfile.ZipFile(io.BytesIO(tail))
    args.out.mkdir(parents=True, exist_ok=True)
    metadata = {"url": url, "archive_bytes": total, "http_headers": headers, "members": []}
    for member in index.infolist():
        if not re.fullmatch(r"nback[123]\.(eeg|vhdr|vmrk)", member.filename):
            continue
        if args.metadata_only and member.filename.endswith(".eeg"):
            continue
        path = args.out / member.filename
        if path.exists() and path.stat().st_size == member.file_size:
            data = path.read_bytes()
            if zlib.crc32(data) != member.CRC:
                raise RuntimeError(f"Cached file failed CRC: {path}")
        else:
            offset = member.header_offset + total - len(tail)
            local, _ = fetch(url, offset, offset + 29)
            if local[:4] != b"PK\x03\x04":
                raise RuntimeError("ZIP member offset invalid.")
            name_length, extra_length = struct.unpack_from("<HH", local, 26)
            start = offset + 30 + name_length + extra_length
            end = start + member.compress_size
            print(f"Downloading {member.filename}: {member.compress_size / 1e6:.1f} MB", flush=True)
            chunks = [(s, min(s + 4 * 1024 * 1024, end) - 1) for s in range(start, end, 4 * 1024 * 1024)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                pieces = list(executor.map(lambda pair: fetch(url, *pair)[0], chunks))
            compressed = b"".join(pieces)
            if len(compressed) != member.compress_size:
                raise RuntimeError("Truncated compressed member.")
            if member.compress_type != zipfile.ZIP_DEFLATED:
                raise RuntimeError("Unexpected ZIP compression.")
            data = zlib.decompress(compressed, -15)
            if len(data) != member.file_size or zlib.crc32(data) != member.CRC:
                raise RuntimeError(f"Integrity failure: {member.filename}")
            path.write_bytes(data)
        metadata["members"].append({"name": member.filename, "bytes": len(data),
                                    "crc32": f"{member.CRC:08x}", "sha256": hashlib.sha256(data).hexdigest()})
    name = "metadata_download.json" if args.metadata_only else "download_manifest.json"
    (args.out / name).write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
