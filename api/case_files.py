import importlib.util
import json
import os
import random
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "out"
NIGHT_DATA = {"attack": ROOT / "data", "quiet": ROOT / "data_dos"}
GENERATED_SCENARIOS = {
    "stopped": "stopped",
    "gap": "gap",
    "spray": "spray",
    "late_work": "late_work",
    "random": "chain",
}
SAMPLES_DIR = ROOT / "tests" / "fixtures"
STRESS_LEVELS = [0, 5, 10, 15, 20, 25, 30, 35, 40]
ENGINE_TIMEOUT_SECONDS = 120
SECRET_ENV_NAMES = {"JWT_SECRET", "RESEND_API_KEY", "SEED_PASSWORD"}

# Reentrant, so approve can check the case and insert while holding it. Reads take it too,
# so nobody reads a file the engine is halfway through writing.
lock = threading.RLock()


class UnreadableCaseFile(Exception):
    pass


def load(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UnreadableCaseFile(f"{path.name}: {exc}") from None


def read(path):
    with lock:
        return load(path)


def intake():
    return read(OUT_DIR / "intake.json") or read(SAMPLES_DIR / "intake.sample.json")


def case():
    return read(OUT_DIR / "case.json")


def stress(level):
    with lock:
        if load(OUT_DIR / "case.json") is None:
            return None
        return load(OUT_DIR / "stress" / f"{level:02d}.json")


def engine_available():
    try:
        return importlib.util.find_spec("engine.run") is not None
    except ModuleNotFoundError:
        return False


def run_engine(night="attack"):
    if not engine_available():
        write_samples()
        return
    if night in NIGHT_DATA:
        run_module(["engine.run", str(NIGHT_DATA[night]), str(OUT_DIR)])
        return
    seed = str(random.randint(1, 99999)) if night == "random" else "7"
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp) / "data"
        scenario = GENERATED_SCENARIOS[night]
        run_module(["generator", "--seed", seed, "--scenario", scenario, "--out", str(data_dir)])
        run_module(["engine.run", str(data_dir), str(OUT_DIR)])


def run_module(args):
    env = {k: v for k, v in os.environ.items() if k not in SECRET_ENV_NAMES}
    result = subprocess.run(
        [sys.executable, "-m", *args],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=ENGINE_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[-2000:] or f"exit code {result.returncode}")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(temp, path)


def write_samples():
    sample_case = load(SAMPLES_DIR / "case.sample.json")
    sample_intake = load(SAMPLES_DIR / "intake.sample.json")
    if sample_case is None or sample_intake is None:
        raise RuntimeError("engine.run is not merged yet and the sample files are missing")
    write_json(OUT_DIR / "intake.json", sample_intake)
    for level in STRESS_LEVELS:
        write_json(OUT_DIR / "stress" / f"{level:02d}.json", {**sample_case, "level": level})
    write_json(OUT_DIR / "case.json", sample_case)


def run_investigation(on_success, night="attack"):
    with lock:
        run_engine(night)
        data = load(OUT_DIR / "case.json")
        if data is not None:
            on_success()
        return data
