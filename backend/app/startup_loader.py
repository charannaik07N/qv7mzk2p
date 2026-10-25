"""
Startup snapshot loader for ephemeral hosting (e.g. Render free tier).

On startup, if DATA_DIR has no valid current.json, this module downloads the
pre-validated January 2026 snapshot from the GitHub release. This is the
free-tier durability strategy: the snapshot is stored in a GitHub Release
asset and fetched at container boot time, avoiding the need for a paid
persistent disk.

Environment variables:
  SNAPSHOT_URL_ACTUALS   - Direct URL to actuals.csv release asset
  SNAPSHOT_URL_FORECASTS - Direct URL to forecasts.csv release asset
  SNAPSHOT_URL_METADATA  - Direct URL to metadata.json release asset
  DATA_DIR               - Where to write the snapshot (default: /tmp/data)

If any URL is missing or download fails, the module logs the error and exits
without crashing the server. The server will start with 'unavailable' data
status, which is correct and visible in the UI.
"""
import json
import logging
import os
import uuid
from pathlib import Path

log = logging.getLogger(__name__)


def _download(url: str, dest: Path, label: str) -> bool:
    """Download url to dest. Returns True on success."""
    import urllib.request
    import urllib.error
    try:
        log.info("Downloading %s from %s", label, url)
        with urllib.request.urlopen(url, timeout=120) as resp:
            dest.write_bytes(resp.read())
        log.info("Downloaded %s (%d bytes)", label, dest.stat().st_size)
        return True
    except urllib.error.URLError as exc:
        log.error("Failed to download %s: %s", label, exc)
        return False
    except OSError as exc:
        log.error("Failed to write %s: %s", label, exc)
        return False


def load_snapshot_if_missing() -> None:
    """
    If DATA_DIR has no valid snapshot, attempt to download one from
    SNAPSHOT_URL_* environment variables. Safe to call multiple times.
    """
    from .config import DATA_DIR

    current_pointer = DATA_DIR / "current.json"

    # Check whether a valid snapshot already exists
    if current_pointer.exists():
        try:
            v = json.loads(current_pointer.read_text()).get("version", "")
            if v and (DATA_DIR / v / "actuals.csv").exists() and (DATA_DIR / v / "forecasts.csv").exists():
                log.info("Startup loader: valid snapshot %s already present; skipping download.", v)
                return
        except Exception:
            pass  # Corrupt pointer — proceed to download

    actuals_url = os.getenv("SNAPSHOT_URL_ACTUALS", "")
    forecasts_url = os.getenv("SNAPSHOT_URL_FORECASTS", "")
    metadata_url = os.getenv("SNAPSHOT_URL_METADATA", "")

    if not actuals_url or not forecasts_url:
        log.info(
            "Startup loader: SNAPSHOT_URL_ACTUALS / SNAPSHOT_URL_FORECASTS not set. "
            "Skipping pre-seeded snapshot download. "
            "Set AUTO_REFRESH_ON_STARTUP=1 or run python -m app.storage to acquire data."
        )
        return

    log.info("Startup loader: no valid snapshot found; downloading from GitHub release assets...")

    version = uuid.uuid4().hex
    snap_dir = DATA_DIR / version
    try:
        snap_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log.error("Startup loader: cannot create snapshot directory %s: %s", snap_dir, exc)
        return

    ok_a = _download(actuals_url, snap_dir / "actuals.csv", "actuals.csv")
    ok_f = _download(forecasts_url, snap_dir / "forecasts.csv", "forecasts.csv")

    if not ok_a or not ok_f:
        log.error(
            "Startup loader: download failed; server starts without data. "
            "Check SNAPSHOT_URL_ACTUALS / SNAPSHOT_URL_FORECASTS and network access."
        )
        try:
            import shutil
            shutil.rmtree(snap_dir, ignore_errors=True)
        except Exception:
            pass
        return

    # Validate the downloaded files are non-empty CSVs before pointing to them
    try:
        import pandas as pd
        a = pd.read_csv(snap_dir / "actuals.csv")
        f = pd.read_csv(snap_dir / "forecasts.csv")
        if a.empty or f.empty:
            raise ValueError("Downloaded CSV is empty")
        for frame in [a, f]:
            for col in ["startTime", "publishTime"]:
                frame[col] = pd.to_datetime(frame[col], utc=True)
            if frame["generation"].isna().any() or not frame["generation"].ge(0).all():
                raise ValueError("Invalid generation values in downloaded snapshot")
        log.info(
            "Startup loader: validation passed — %d actual rows, %d forecast rows",
            len(a), len(f)
        )
    except Exception as exc:
        log.error("Startup loader: downloaded snapshot failed validation: %s", exc)
        try:
            import shutil
            shutil.rmtree(snap_dir, ignore_errors=True)
        except Exception:
            pass
        return

    # Download optional metadata
    meta_dest = snap_dir / "metadata.json"
    if metadata_url:
        if not _download(metadata_url, meta_dest, "metadata.json"):
            # Write a minimal metadata so the Store can load the snapshot
            meta_dest.write_text(json.dumps({
                "status": "cached",
                "lastSuccessfulRefresh": None,
                "source": "pre-seeded GitHub release snapshot",
                "warning": "Metadata unavailable; snapshot downloaded from release asset."
            }))
    else:
        meta_dest.write_text(json.dumps({
            "status": "cached",
            "lastSuccessfulRefresh": None,
            "source": "pre-seeded GitHub release snapshot",
        }))

    # Atomically write the pointer
    tmp_pointer = DATA_DIR / f"pointer-{version}.tmp"
    try:
        tmp_pointer.write_text(json.dumps({"version": version}))
        os.replace(tmp_pointer, current_pointer)
        log.info("Startup loader: snapshot %s installed and activated.", version)
    except OSError as exc:
        log.error("Startup loader: failed to write current.json: %s", exc)
        try:
            import shutil
            shutil.rmtree(snap_dir, ignore_errors=True)
            tmp_pointer.unlink(missing_ok=True)
        except Exception:
            pass
