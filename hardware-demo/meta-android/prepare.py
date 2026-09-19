#!/usr/bin/env python3
"""Fetch a pinned official sample and apply our small integration. Never reads credentials."""
import argparse
import io
import json
from pathlib import Path
import shutil
import tarfile
import urllib.request

COMMIT = "81dfb51b9be26de5cd262bb1dcbb4b8d0d6bd2bc"
ROOT = Path(__file__).resolve().parent
DEST = ROOT / "vendor"
PACKAGE = Path("app/src/main/java/com/meta/wearable/dat/externalsampleapps/cameraaccess")


def replace_once(path, before, after):
    text = path.read_text()
    if text.count(before) != 1:
        raise RuntimeError(f"Pinned sample anchor changed in {path.name}; inspect before patching")
    path.write_text(text.replace(before, after, 1))


def prepare(source=None):
    if DEST.exists():
        raise SystemExit("vendor/ already exists; keeping your local setup. Use it as-is or move it aside to regenerate.")
    DEST.mkdir()
    if source:
        # A local checkout makes preparation testable offline. Verify its revision.
        import subprocess
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
        if revision != COMMIT:
            raise SystemExit(f"Expected upstream commit {COMMIT}")
        shutil.copytree(Path(source) / "samples/CameraAccess", DEST / "CameraAccess")
        shutil.copy2(Path(source) / "LICENSE", DEST / "LICENSE")
    else:
        url = f"https://codeload.github.com/facebook/meta-wearables-dat-android/tar.gz/{COMMIT}"
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
        prefix = f"meta-wearables-dat-android-{COMMIT}/"
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for member in archive:
                if not member.isfile() or not member.name.startswith(prefix):
                    continue
                rel = member.name[len(prefix):]
                if rel == "LICENSE":
                    target = DEST / "LICENSE"
                elif rel.startswith("samples/CameraAccess/"):
                    target = DEST / rel.removeprefix("samples/")
                else:
                    continue
                if not target.resolve().is_relative_to(DEST.resolve()):
                    raise RuntimeError("Unexpected archive path")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
    app = DEST / "CameraAccess"
    (app / "gradlew").chmod(0o755)
    shutil.copy2(ROOT / "DemoBackend.kt", app / PACKAGE / "DemoBackend.kt")
    vm = app / PACKAGE / "camera/CameraViewModel.kt"
    replace_once(vm, "import kotlinx.coroutines.flow.asStateFlow", "import kotlinx.coroutines.flow.first\nimport kotlinx.coroutines.flow.asStateFlow")
    # Keep the instance: the stop path needs it to upload the finished MP4. The property is
    # declared here rather than in the fragment, which lands below init — Kotlin refuses to
    # let init assign a property declared later in the class body.
    replace_once(vm, "  init {\n", "  private var demoBackend: com.meta.wearable.dat.externalsampleapps.cameraaccess.DemoBackend? = null\n\n  init {\n    if (com.meta.wearable.dat.externalsampleapps.cameraaccess.BuildConfig.DEMO_BACKEND_URL.isNotBlank()) {\n      demoBackend = com.meta.wearable.dat.externalsampleapps.cameraaccess.DemoBackend(\n          com.meta.wearable.dat.externalsampleapps.cameraaccess.BuildConfig.DEMO_BACKEND_URL,\n          com.meta.wearable.dat.externalsampleapps.cameraaccess.BuildConfig.DEMO_TOKEN,\n          ::executeDemoCommand,\n      ).also { it.start(viewModelScope) }\n    }\n")
    replace_once(vm, "  // MARK: - Recording\n", (ROOT / "CameraViewModel.fragment.kt").read_text() + "\n  // MARK: - Recording\n")
    gradle = app / "app/build.gradle.kts"
    replace_once(gradle, "  buildTypes {", '''  buildTypes {
    debug {
      buildConfigField("String", "DEMO_BACKEND_URL", "\\\"" + (System.getenv("DEMO_BACKEND_URL") ?: "http://10.0.2.2:8771") + "\\\"")
      buildConfigField("String", "DEMO_TOKEN", "\\\"" + (System.getenv("DEMO_TOKEN") ?: "") + "\\\"")
      manifestPlaceholders["mwdat_application_id"] = "0"
      manifestPlaceholders["mwdat_client_token"] = "0"
    }
''')
    replace_once(gradle, "    release {", '''    release {
      buildConfigField("String", "DEMO_BACKEND_URL", "\\\"\\\"")
      buildConfigField("String", "DEMO_TOKEN", "\\\"\\\"")''')
    debug_manifest = app / "app/src/debug/AndroidManifest.xml"
    debug_manifest.parent.mkdir(parents=True, exist_ok=True)
    debug_manifest.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application android:usesCleartextTraffic="true" /></manifest>\n')
    (DEST / "upstream.json").write_text(json.dumps({"repository": "facebook/meta-wearables-dat-android", "commit": COMMIT}, indent=2))
    print(f"Prepared {app}. Set DEMO_BACKEND_URL and DEMO_TOKEN before building debug.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="existing checkout at the pinned commit")
    prepare(parser.parse_args().source)
