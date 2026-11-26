"""Check known files on the A7 III's public PMHOME volume in normal USB Mass Storage mode."""
import hashlib
import json
import os
import plistlib
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


# From update/0650_prfile/PMBP/LICENSE/zlib.txt in the ILCE-7M3 4.04 update.
LICENSE = "LICENSE/zlib.txt"
LICENSE_REFERENCE = (1531, "464352f7afcece608041241e20b28e8006ae170446898e9713fb076323d1487d")
# These are candidate public locations. Sony documents only the LICENSE directory.
XML_PATHS = ("DeviceInfo.xml", "INFO/DeviceInfo.xml")
READ_LIMIT = 64 * 1024


def windows_mounts():
    # Get only drive letters. The camera can present the volume as an optical drive.
    query = (
        "$ErrorActionPreference='Stop'; "
        "Get-CimInstance Win32_LogicalDisk -Filter \"VolumeName='PMHOME'\" | "
        "Where-Object { $_.DriveType -in 2,3,5 } | ForEach-Object { $_.DeviceID }"
    )
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", query],
                            capture_output=True, check=True, timeout=30)
    letters = result.stdout.decode("ascii").split()
    if any(not re.fullmatch(r"[A-Za-z]:", letter) for letter in letters):
        raise ValueError("unexpected drive identifier")
    return [Path(letter + "/") for letter in letters]


def macos_mounts():
    def diskutil(*args):
        reply = subprocess.run(["/usr/sbin/diskutil", *args], check=True, capture_output=True, timeout=30)
        return plistlib.loads(reply.stdout)

    inventory = diskutil("list", "-plist", "external")
    volumes = []
    for disk in inventory["AllDisksAndPartitions"]:
        for item in [disk, *disk.get("Partitions", [])]:
            if item.get("VolumeName", "").casefold() != "pmhome":
                continue
            info = diskutil("info", "-plist", item["DeviceIdentifier"])
            if info.get("VolumeName", "").casefold() != "pmhome":
                raise OSError("volume changed during discovery")
            mount = info.get("MountPoint")
            volumes.append(Path(mount) if mount else None)
    return volumes


def check_file(root, relative, reference):
    row = {"path": relative}
    try:
        # Stay within the selected volume even if a candidate is a symbolic link.
        target = (root / relative).resolve(strict=True)
        target.relative_to(root.resolve(strict=True))
        if not stat.S_ISREG(target.stat().st_mode):
            return dict(row, status="not_a_regular_file")
        with target.open("rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                return dict(row, status="not_a_regular_file")
            row["bytes"] = info.st_size
            if info.st_size > READ_LIMIT:
                return dict(row, status="differs", detail="size exceeds read limit")
            data = stream.read(READ_LIMIT + 1)
        if len(data) != info.st_size:
            return dict(row, status="read_error", detail="size changed during read")
    except FileNotFoundError:
        return dict(row, status="missing")
    except PermissionError:
        return dict(row, status="permission_denied")
    except (OSError, RuntimeError, ValueError) as exc:
        return dict(row, status="read_error", detail=type(exc).__name__)
    digest = hashlib.sha256(data).hexdigest()
    return dict(row, sha256=digest, status="match" if (len(data), digest) == reference else "differs")


def collect(discover, xml_reference):
    try:
        roots = discover()
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, plistlib.InvalidFileException) as exc:
        return {"status": "discovery_error", "error": type(exc).__name__}
    if not roots:
        return {"status": "pmhome_not_visible"}
    if len(roots) != 1:
        return {"status": "multiple_pmhome_volumes", "count": len(roots)}
    root = roots[0]
    if root is None:
        return {"status": "pmhome_not_mounted"}
    control = check_file(root, LICENSE, LICENSE_REFERENCE)
    files = [control] + [check_file(root, name, xml_reference) for name in XML_PATHS]
    try:
        mounted = root.is_dir()
    except OSError:
        mounted = False
    if not mounted:
        return {"status": "volume_disconnected", "files": files}
    return {"status": "control_" + control["status"], "files": files}


def save_report(report, folder):
    # The report goes on the computer. A unique filename preserves earlier attempts.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with tempfile.NamedTemporaryFile(dir=folder, prefix="M3_PMHOME_" + stamp + "_",
                                     suffix=".zip", delete=False) as output:
        path = Path(output.name)
    try:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("report.json", json.dumps(report, indent=2) + "\n")
    except BaseException:
        path.unlink()
        raise
    return path


def main():
    if sys.platform not in ("win32", "darwin"):
        raise SystemExit("Run this check on Windows or macOS.")
    references = json.loads(Path(__file__).with_name("expected_404.json").read_text(encoding="utf-8"))
    xml = references["files"]["/usr/share/pmbp/DeviceInfo.xml"]
    report = collect(windows_mounts if sys.platform == "win32" else macos_mounts, (xml["bytes"], xml["sha256"]))
    report.update(test="M3_PMHOME_v1", platform=sys.platform, firmware_image_verified=False)
    print("Public volume check:", report["status"])
    for row in report.get("files", []):
        print("  %s: %s" % (row["path"], row["status"]))
    print("Send this ZIP back even if the volume or a file was unavailable:")
    print(save_report(report, Path.home()))
    return 0 if report["status"] == "control_match" else 1


if __name__ == "__main__":
    sys.exit(main())
