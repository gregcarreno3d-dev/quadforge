"""Replay a debug bundle (Advanced > Save Debug Bundle) on this computer.

    python3 tools/replay_bundle.py BUNDLE.zip [--target N] [--sym x|none] [--out DIR]

Unzips the bundle, prints the user's environment and report, finds the source mesh (the object without '_quads'),
runs `tools/cad_battery.py` on it with the target and symmetry saved in the settings, and prints the user's result
beside the replayed one (faces, triangles) so that differences between computers show at once.
"""
import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def obj_counts(path: Path) -> tuple[int, int]:
    faces = tris = 0
    for line in path.read_text().splitlines():
        if line.startswith("f "):
            faces += 1
            tris += len(line.split()) == 4
    return faces, tris


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle")
    ap.add_argument("--target", type=int, default=None)
    ap.add_argument("--sym", choices=["x", "none"], default=None)
    ap.add_argument("--out", default="/tmp/replay")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.bundle) as z:
        z.extractall(out)
    info = json.loads((out / "info.json").read_text())
    s = info["settings"]
    print(f"add-on {info['addon_version']}  Blender {info['blender']}  {info['platform']}  {info['cpu_count']} CPUs")
    print("engine:", info["engine"])
    print("last result:", {k: v for k, v in info["last_result"].items() if k not in ("last_levels_text",)})
    meshes = sorted((out / "meshes").glob("*.obj"))
    source = next((m for m in meshes if not m.stem.endswith("_quads")), None)
    result = next((m for m in meshes if m.stem.endswith("_quads")), None)
    if source is None:
        print("no source mesh in the bundle (select the original object too)")
        return 1
    target = args.target or s.get("target_quads", 120000)
    sym = args.sym or ("x" if s.get("sym_x") else "none")
    save = out / "replayed"
    print(f"replaying {source.name} target {target} sym {sym} ...")
    subprocess.run([sys.executable, str(HERE / "cad_battery.py"), str(source), "--target", str(target), "--sym", sym,
                    "--save", str(save)], check=False)
    replayed = save / f"{source.stem}_result.obj"
    if result is not None:
        print("user's result :", obj_counts(result), "(faces, triangles)")
    if replayed.exists():
        print("replayed      :", obj_counts(replayed))
        print(f"compare: python3 {HERE / 'zone_report.py'} {source} {replayed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
