import json
import urllib.error
import urllib.request


def request(url, path, body=None, token=""):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url.rstrip("/") + path,
                                 data=None if body is None else json.dumps(body, allow_nan=False).encode(),
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        message = exc.read().decode()
        exc.close()
        raise RuntimeError(f"HTTP {exc.code}: {message}") from exc
