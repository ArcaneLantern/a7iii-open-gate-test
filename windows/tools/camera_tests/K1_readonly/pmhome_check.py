"""Check known files on the A7 III's public PMHOME volume in normal USB Mass Storage mode (M3_PMHOME_v2).

v2, 2026-11-26. The first macOS report said only "pmhome_not_visible" and recorded nothing else. v1 searched
`diskutil list external` for a volume named PMHOME and nothing more. v2 adds three things:
  * It finds the camera the way the first kit did on the same Mac: the I/O Registry gives the Sony USB device,
    its interface classes and the disks under it. It then checks every disk and slice the camera shows.
  * It recognises the built-in volume by its name (PMHOME), by the control file at its root, or by its size.
    The 4.04 mount.conf gives the size: /dev/nflasha23 /PMBP, 2,097,152 bytes. A memory card is far larger.
  * It saves a short inventory and a hint, so a failed run still shows what the computer saw.
The inventory holds the Sony device's USB id and interface classes, and the camera's disks with their size, file
system and mount state. Volume names are kept only when they are PMHOME, NO NAME or Untitled. Other disks give
only a count. No serial number, no other volume name and no file listing is saved.
Read-only: it mounts, unmounts, renames and writes nothing. It opens only the three fixed paths below.
"""
import hashlib
import json
import os
import platform
import plistlib
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


TEST = "M3_PMHOME_v2"
# From update/0650_prfile/PMBP/LICENSE/zlib.txt in the ILCE-7M3 4.04 update.
LICENSE = "LICENSE/zlib.txt"
LICENSE_REFERENCE = (1531, "464352f7afcece608041241e20b28e8006ae170446898e9713fb076323d1487d")
# These are candidate public locations. Sony documents only the LICENSE directory.
XML_PATHS = ("DeviceInfo.xml", "INFO/DeviceInfo.xml")
READ_LIMIT = 64 * 1024

SONY_VID = 0x054C
# sen_desc_tbl in 4.04 libInfraUsbCmn.so. The first kit saw the camera come back as 054c:0336, class 255.
SERVICE_PID = 0x0336
MASS_STORAGE_CLASS, STILL_IMAGE_CLASS = 8, 6
# 4.04 mount.conf: "/dev/nflasha23 /PMBP prfile 2097152". libInfraFsys.so labels it PMHOME when it formats it.
BUILT_IN_BYTES = 2097152
SMALL_DISK = (1 << 20, 8 << 20)
SAFE_NAMES = ("pmhome", "no name", "untitled", "")
DISK_ID = re.compile(r"disk[0-9]+(s[0-9]+)*")
IOREG = "/usr/sbin/ioreg"
DISKUTIL = "/usr/sbin/diskutil"

HINTS = {
    "camera_not_on_usb": [
        "The computer shows no Sony USB device.",
        "Turn the camera off and on again. Then connect the cable straight to the computer, with no hub or dock.",
        "If macOS asks whether to allow the accessory to connect, click Allow.",
    ],
    "camera_in_service_mode": [
        "The camera is still in the service mode the first test used (USB id 054c:0336).",
        "Disconnect the cable, turn the camera off and on again, and connect again.",
    ],
    "camera_in_mtp_or_remote_mode": [
        "The camera is connected as MTP/PTP or PC Remote, not as a disk.",
        "Set MENU > Setup > USB Connection > Mass Storage, then disconnect and reconnect the cable.",
    ],
    "camera_not_in_mass_storage": [
        "The camera is on USB but not as a Mass Storage device.",
        "Set MENU > Setup > USB Connection > Mass Storage, then disconnect and reconnect the cable.",
    ],
    "camera_disks_absent": [
        "The camera is in Mass Storage mode but shows no disks yet.",
        "Wait until the camera screen shows the USB mode, or reconnect the cable, then run the check again.",
    ],
    "pmhome_not_mounted": [
        "The built-in PMHOME disk is attached but not mounted.",
        "Disconnect and reconnect the cable, wait for Finder or File Explorer to show the camera, and run again.",
        "Do not repair or format the camera's disks.",
    ],
    "pmhome_not_visible": [
        "The camera shows disks, but none of them is the built-in PMHOME volume.",
        "Check MENU > Setup > USB LUN Setting > Multi. The saved ZIP lists what the computer saw.",
    ],
}


def run_tool(args):
    return subprocess.run(args, check=True, capture_output=True, timeout=60).stdout


def read_plist(run, *args):
    out = run(list(args))
    return plistlib.loads(out) if out.strip() else None


def safe_text(value, limit=64):
    if not isinstance(value, str):
        return None
    return "".join(ch for ch in value if " " <= ch <= "~")[:limit]


def safe_name(name):
    return name if name.strip().casefold() in SAFE_NAMES else "<other>"


def walk(node):
    """An I/O Registry entry from `ioreg -a` and everything under it."""
    yield node
    for child in node.get("IORegistryEntryChildren", []):
        yield from walk(child)


def sony_usb_devices(run):
    """macOS: Sony USB devices, their interface classes, the drivers on them and the whole disks under them.
    `ioreg -r` lists only the outermost matches, so a camera behind a hub sits inside the hub's entry."""
    tops = read_plist(run, IOREG, "-a", "-r", "-c", "IOUSBHostDevice", "-l") or []
    if isinstance(tops, dict):
        tops = [tops]
    rows = []
    for dev in (node for top in tops for node in walk(top)):
        if dev.get("IOObjectClass") != "IOUSBHostDevice" or dev.get("idVendor") != SONY_VID:
            continue
        interfaces = [n for n in dev.get("IORegistryEntryChildren", []) if n.get("IOObjectClass") == "IOUSBHostInterface"]
        drivers = [d.get("IOObjectClass") for i in interfaces for d in i.get("IORegistryEntryChildren", [])]
        disks = {n.get("BSD Name") for n in walk(dev) if n.get("IOObjectClass") == "IOMedia" and n.get("Whole")}
        rows.append({
            "usb_id": "054c:%04x" % (dev.get("idProduct") or 0),
            "name": safe_text(dev.get("USB Product Name")),
            "interface_classes": [i.get("bInterfaceClass") for i in interfaces],
            "drivers": list(dict.fromkeys(safe_text(d) for d in drivers if d)),
            "disks": sorted(d for d in disks if isinstance(d, str) and DISK_ID.fullmatch(d)),
        })
    return rows


def describe_disk(run, ident):
    """One disk or slice from `diskutil info`. Returns the saved row, the real volume name and the mount point."""
    info = read_plist(run, DISKUTIL, "info", "-plist", ident) or {}
    name = info.get("VolumeName") or ""
    mount = info.get("MountPoint") or None
    row = {
        "id": ident,
        "bytes": info.get("TotalSize", info.get("Size")),
        "content": safe_text(info.get("Content")),
        "fs": safe_text(info.get("FilesystemType")),
        "mounted": bool(mount),
        "writable": info.get("WritableVolume"),
        "name": safe_name(name),
    }
    if info.get("WholeDisk"):
        row["media"] = safe_text(info.get("MediaName"))
    return row, name, mount


def disk_and_slices(run, whole):
    listing = read_plist(run, DISKUTIL, "list", "-plist", whole) or {}
    idents = listing.get("AllDisks")
    if not idents:
        idents = []
        for disk in listing.get("AllDisksAndPartitions", []):
            idents += [disk.get("DeviceIdentifier")] + [p.get("DeviceIdentifier") for p in disk.get("Partitions", [])]
    return [i for i in dict.fromkeys(idents or [whole]) if isinstance(i, str) and DISK_ID.fullmatch(i)]


def named_pmhome_disks(run):
    """v1's route, without the `external` filter: any disk or slice whose volume is named PMHOME."""
    inventory = read_plist(run, DISKUTIL, "list", "-plist") or {}
    found = []
    for disk in inventory.get("AllDisksAndPartitions", []):
        for item in [disk, *disk.get("Partitions", [])]:
            ident = item.get("DeviceIdentifier")
            if (item.get("VolumeName") or "").strip().casefold() == "pmhome" and isinstance(ident, str) \
                    and DISK_ID.fullmatch(ident):
                found.append(ident)
    return found


def has_control_file(mount):
    try:
        return Path(mount, LICENSE).is_file()
    except OSError:
        return False


def macos_discover(run=run_tool):
    diag = {"os_version": platform.mac_ver()[0] or None}
    try:
        usb = sony_usb_devices(run)
    except (OSError, subprocess.SubprocessError, ValueError, plistlib.InvalidFileException) as exc:
        usb, diag["usb_error"] = None, type(exc).__name__
    diag["usb"] = usb
    camera, seen = [], {}
    for dev in usb or []:
        for whole in dev["disks"]:
            try:
                for ident in disk_and_slices(run, whole):
                    if ident not in seen:
                        seen[ident] = describe_disk(run, ident)
                        camera.append(seen[ident])
            except (OSError, subprocess.SubprocessError, ValueError, plistlib.InvalidFileException) as exc:
                diag.setdefault("disk_errors", []).append({"disk": whole, "error": type(exc).__name__})
    diag["camera_disks"] = [row for row, _, _ in camera]
    try:
        external = read_plist(run, DISKUTIL, "list", "-plist", "external") or {}
        others = [d for d in external.get("WholeDisks", []) if d not in {r["id"] for r, _, _ in camera}]
        diag["other_external_disks"] = len(others)
    except (OSError, subprocess.SubprocessError, ValueError, plistlib.InvalidFileException) as exc:
        diag["external_list_error"] = type(exc).__name__

    # 1. by name: the camera's own disks first, then every disk the Mac lists.
    by_name = [(row["id"], mount) for row, name, mount in camera if name.strip().casefold() == "pmhome"]
    try:
        for ident in named_pmhome_disks(run):
            if ident not in {i for i, _ in by_name}:
                row, name, mount = seen[ident] if ident in seen else describe_disk(run, ident)
                if name.strip().casefold() == "pmhome":
                    by_name.append((ident, mount))
    except (OSError, subprocess.SubprocessError, ValueError, plistlib.InvalidFileException) as exc:
        diag["name_search_error"] = type(exc).__name__
    if by_name:
        return [(Path(m) if m else None, i, "name") for i, m in by_name], diag, usb, camera
    # 2. by the control file at the root of a mounted camera volume (stat only).
    by_file = [(row["id"], mount) for row, _, mount in camera if mount and has_control_file(mount)]
    if by_file:
        return [(Path(m), i, "control_file") for i, m in by_file], diag, usb, camera
    # 3. by size: the built-in disk is about 2 MiB. Prefer a slice with a file system to its whole disk.
    small = [(row, mount) for row, _, mount in camera
             if isinstance(row["bytes"], int) and SMALL_DISK[0] <= row["bytes"] <= SMALL_DISK[1]]
    best = [(r, m) for r, m in small if m or r["fs"]] or small[:1]
    return [(Path(m) if m else None, r["id"], "size") for r, m in best], diag, usb, camera


def no_volume_status(usb, camera):
    if usb is None:
        return "pmhome_not_visible"
    if not usb:
        return "camera_not_on_usb"
    if any(d["usb_id"] == "054c:%04x" % SERVICE_PID for d in usb):
        return "camera_in_service_mode"
    if not any(MASS_STORAGE_CLASS in d["interface_classes"] for d in usb):
        if any(STILL_IMAGE_CLASS in d["interface_classes"] for d in usb):
            return "camera_in_mtp_or_remote_mode"
        return "camera_not_in_mass_storage"
    if not camera:
        return "camera_disks_absent"
    return "pmhome_not_visible"


def windows_sony_devices():
    """Windows: Sony USB functions with USB id and interface number only. The serial part is not kept."""
    query = (
        "$ErrorActionPreference='Stop'; "
        "Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPDeviceID -match 'VID_054C' } | "
        "Select-Object PNPDeviceID, PNPClass, Service | ConvertTo-Json -Compress"
    )
    try:
        out = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", query],
                             capture_output=True, check=True, timeout=60).stdout.decode("utf-8", "replace").strip()
        rows = json.loads(out) if out else []
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return None, type(exc).__name__
    rows = [rows] if isinstance(rows, dict) else rows
    devices = []
    for r in rows:
        m = re.search(r"VID_054C&PID_([0-9A-Fa-f]{4})(&MI_[0-9A-Fa-f]{2})?", r.get("PNPDeviceID") or "")
        if m:
            devices.append({"usb_id": "054c:%s" % m.group(1).lower(), "interface": (m.group(2) or "")[1:] or None,
                            "class": safe_text(r.get("PNPClass")), "service": safe_text(r.get("Service"))})
    return devices, None


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


def windows_discover():
    devices, error = windows_sony_devices()
    diag = {"os_version": platform.version() or None, "usb": devices}
    if error:
        diag["usb_error"] = error
    roots = windows_mounts()
    return [(root, root.drive, "name") for root in roots], diag, devices, None


def windows_no_volume_status(devices):
    if devices == []:
        return "camera_not_on_usb"
    if devices and any(d["usb_id"] == "054c:%04x" % SERVICE_PID for d in devices):
        return "camera_in_service_mode"
    return "pmhome_not_visible"


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


def collect(discover, xml_reference, no_volume):
    try:
        found, diag, usb, camera = discover()
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, plistlib.InvalidFileException) as exc:
        return {"status": "discovery_error", "error": type(exc).__name__}
    report = {"diagnostics": diag}
    if not found:
        return dict(report, status=no_volume(usb, camera) if camera is not None else no_volume(usb))
    if len(found) != 1:
        return dict(report, status="multiple_pmhome_volumes", count=len(found),
                    candidates=[{"id": i, "by": by} for _, i, by in found])
    root, ident, by = found[0]
    report["selected"] = {"id": ident, "by": by}
    if root is None:
        return dict(report, status="pmhome_not_mounted")
    control = check_file(root, LICENSE, LICENSE_REFERENCE)
    files = [control] + [check_file(root, name, xml_reference) for name in XML_PATHS]
    try:
        mounted = root.is_dir()
    except OSError:
        mounted = False
    if not mounted:
        return dict(report, status="volume_disconnected", files=files)
    return dict(report, status="control_" + control["status"], files=files)


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


def print_report(report):
    print("Public volume check:", report["status"])
    if report.get("selected"):
        print("  volume %s (found by %s)" % (report["selected"]["id"], report["selected"]["by"]))
    for row in report.get("files", []):
        print("  %s: %s" % (row["path"], row["status"]))
    diag = report.get("diagnostics", {})
    for dev in diag.get("usb") or []:
        print("  Sony USB device %s %s" % (dev["usb_id"], dev.get("name") or dev.get("class") or ""))
    for disk in diag.get("camera_disks", []):
        print("  camera disk %s: %s bytes, %s, %s" % (disk["id"], disk["bytes"], disk["fs"] or disk["content"],
                                                       "mounted" if disk["mounted"] else "not mounted"))
    for line in HINTS.get(report["status"], []):
        print("  " + line)


def main():
    if "--selftest" in sys.argv[1:]:
        return selftest()
    if sys.platform not in ("win32", "darwin"):
        raise SystemExit("Run this check on Windows or macOS.")
    references = json.loads(Path(__file__).with_name("expected_404.json").read_text(encoding="utf-8"))
    xml = references["files"]["/usr/share/pmbp/DeviceInfo.xml"]
    if sys.platform == "win32":
        report = collect(windows_discover, (xml["bytes"], xml["sha256"]), windows_no_volume_status)
    else:
        report = collect(macos_discover, (xml["bytes"], xml["sha256"]), no_volume_status)
    report.update(test=TEST, platform=sys.platform, firmware_image_verified=False)
    print_report(report)
    print("Send this ZIP back even if the volume or a file was unavailable:")
    print(save_report(report, Path.home()))
    return 0 if report["status"] == "control_match" else 1


# --------------------------------------------------------------------------
# Self-test: simulated ioreg and diskutil replies. No camera or Mac needed.
# --------------------------------------------------------------------------
def fake_mac(devices, disks, external=None, ioreg_error=False):
    """devices: [(pid, [interface classes], [whole disks])]. disks: {whole: [(ident, name, mount, bytes, fs)]}."""
    entries = {e[0]: (whole, e) for whole, rows in disks.items() for e in rows}

    def node(pid, classes, wholes):
        media = [{"IOObjectClass": "IOMedia", "Whole": True, "BSD Name": w} for w in wholes]
        nub = {"IOObjectClass": "IOUSBMassStorageInterfaceNub", "IORegistryEntryChildren": media}
        return {"IOObjectClass": "IOUSBHostDevice", "idVendor": SONY_VID, "idProduct": pid, "USB Product Name": "ILCE-7M3",
                "locationID": 0x01100000, "USB Serial Number": "SERIAL123456",
                "IORegistryEntryChildren": [{"IOObjectClass": "IOUSBHostInterface", "bInterfaceClass": c,
                                             "IORegistryEntryChildren": [nub] if c == MASS_STORAGE_CLASS else []}
                                            for c in classes]}

    def listing(wholes):
        rows = []
        for w in wholes:
            row = {"DeviceIdentifier": w, "Partitions": [{"DeviceIdentifier": e[0], "VolumeName": e[1]}
                                                         for e in disks.get(w, []) if e[0] != w]}
            row.update({"VolumeName": e[1] for e in disks.get(w, []) if e[0] == w and e[1]})
            rows.append(row)
        return {"WholeDisks": list(wholes), "AllDisksAndPartitions": rows}

    def run(args):
        if args[0] == IOREG:
            if ioreg_error:
                raise subprocess.CalledProcessError(1, args)
            hub = {"IOObjectClass": "IOUSBHostDevice", "idVendor": 0x05AC, "idProduct": 0x1234,
                   "IORegistryEntryChildren": [node(*d) for d in devices]}
            return plistlib.dumps([hub])
        if args[1:3] == ["list", "-plist"] and len(args) == 3:
            return plistlib.dumps(listing(list(disks) + ["disk0", "disk7"]))
        if args[1:] == ["list", "-plist", "external"]:
            return plistlib.dumps(external if external is not None else listing(list(disks) + ["disk7"]))
        if args[1:3] == ["list", "-plist"]:
            w = args[3]
            return plistlib.dumps({"AllDisks": [w] + [e[0] for e in disks.get(w, []) if e[0] != w]})
        if args[1:3] == ["info", "-plist"]:
            ident = args[3]
            if ident == "disk7":
                return plistlib.dumps({"VolumeName": "Holiday Backup 2026", "MountPoint": "/Volumes/Holiday",
                                       "TotalSize": 2 << 40, "WholeDisk": True})
            whole, e = entries.get(ident, (ident, (ident, "", "", 64 << 30, "")))
            return plistlib.dumps({"VolumeName": e[1], "MountPoint": e[2] or "", "TotalSize": e[3],
                                   "FilesystemType": e[4], "Content": "DOS_FAT_12" if e[4] else "",
                                   "WholeDisk": ident == whole, "MediaName": "Sony DSC Media",
                                   "WritableVolume": False})
        raise AssertionError("unexpected command %r" % (args,))
    return run


def selftest():
    global LICENSE_REFERENCE
    failures = []

    def check(label, ok):
        print("  %s %s" % ("ok  " if ok else "FAIL", label))
        if not ok:
            failures.append(label)

    saved_reference = LICENSE_REFERENCE
    with tempfile.TemporaryDirectory() as tmp:
        standin = b"stand-in for LICENSE/zlib.txt\n"
        LICENSE_REFERENCE = (len(standin), hashlib.sha256(standin).hexdigest())
        pm = Path(tmp, "PMHOME")
        (pm / "LICENSE").mkdir(parents=True)
        (pm / "LICENSE" / "zlib.txt").write_bytes(standin)
        card = Path(tmp, "Untitled")
        (card / "DCIM").mkdir(parents=True)
        xml = (517, "0" * 64)

        def run_case(devices, disks, **kw):
            fake = fake_mac(devices, disks, **kw)
            report = collect(lambda: macos_discover(fake), xml, no_volume_status)
            return report

        card_disk = ("disk4", [("disk4", "", "", 64 << 30, ""), ("disk4s1", "Untitled", str(card), 64 << 30, "exfat")])
        pm_disk = ("disk5", [("disk5", "PMHOME", str(pm), BUILT_IN_BYTES, "msdos")])
        k1 = [(0x0C02, [MASS_STORAGE_CLASS], ["disk4", "disk5"])]

        r = run_case(k1, dict([card_disk, pm_disk]))
        check("camera's PMHOME disk found and control matches", r["status"] == "control_match"
              and r["selected"] == {"id": "disk5", "by": "name"})
        r = run_case(k1, dict([card_disk, pm_disk]), external={"WholeDisks": [], "AllDisksAndPartitions": []})
        check("found when `diskutil list external` omits the camera (v1 missed this)", r["status"] == "control_match")
        renamed = ("disk5", [("disk5", "NO NAME", str(pm), BUILT_IN_BYTES, "msdos")])
        r = run_case(k1, dict([card_disk, renamed]))
        check("found by the control file when the label is not PMHOME", r["status"] == "control_match"
              and r["selected"]["by"] == "control_file")
        unmounted = ("disk5", [("disk5", "", "", BUILT_IN_BYTES, "")])
        r = run_case(k1, dict([card_disk, unmounted]))
        check("unmounted 2 MiB camera disk -> pmhome_not_mounted (by size)", r["status"] == "pmhome_not_mounted"
              and r["selected"] == {"id": "disk5", "by": "size"})
        r = run_case([(0x0C02, [MASS_STORAGE_CLASS], ["disk4"])], dict([card_disk]))
        check("card only -> pmhome_not_visible with the card listed", r["status"] == "pmhome_not_visible"
              and [d["id"] for d in r["diagnostics"]["camera_disks"]] == ["disk4", "disk4s1"])
        r = run_case([(0x0C02, [MASS_STORAGE_CLASS], [])], {})
        check("mass storage with no disks -> camera_disks_absent", r["status"] == "camera_disks_absent")
        r = run_case([(SERVICE_PID, [255], [])], {})
        check("054c:0336 class 255 -> camera_in_service_mode", r["status"] == "camera_in_service_mode")
        r = run_case([(0x0C03, [STILL_IMAGE_CLASS], [])], {})
        check("still-image class only -> camera_in_mtp_or_remote_mode", r["status"] == "camera_in_mtp_or_remote_mode")
        r = run_case([], {})
        check("no Sony device -> camera_not_on_usb", r["status"] == "camera_not_on_usb")
        two = ("disk6", [("disk6", "PMHOME", str(pm), BUILT_IN_BYTES, "msdos")])
        r = run_case([(0x0C02, [MASS_STORAGE_CLASS], ["disk5", "disk6"])], dict([pm_disk, two]))
        check("two PMHOME volumes -> multiple_pmhome_volumes", r["status"] == "multiple_pmhome_volumes")
        r = run_case(k1, dict([card_disk, pm_disk]), ioreg_error=True)
        check("I/O Registry error -> still found by name, error recorded", r["status"] == "control_match"
              and r["diagnostics"].get("usb_error") == "CalledProcessError")
        private = ("disk4", [("disk4", "", "", 64 << 30, ""), ("disk4s1", "Holiday Card", str(card), 64 << 30, "exfat")])
        r = run_case(k1, dict([private, pm_disk]))
        text = json.dumps(r)
        check("report keeps no other volume name, serial or path", "Holiday" not in text and "SERIAL" not in text
              and tmp not in text and str(Path.home()) not in text and r["diagnostics"]["other_external_disks"] == 1)
        check("every no-volume status has a hint", all(s in HINTS for s in (
            "camera_not_on_usb", "camera_in_service_mode", "camera_in_mtp_or_remote_mode",
            "camera_not_in_mass_storage", "camera_disks_absent", "pmhome_not_mounted", "pmhome_not_visible")))
    LICENSE_REFERENCE = saved_reference
    print("Self-test: %d failed" % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
