"""Build the submission zip: only the allowed bundle-root entries, forward-slash paths.
Usage (from the task root):  python authoring/provenance/make_zip.py ../_dist/stiction-loop-retune.zip"""
import os, sys, zipfile
ALLOW = ["instruction.md", "task.toml", "README.md", "environment", "solution", "tests", "authoring"]
SKIP_DIRS = {"__pycache__", "scratch"}
out = sys.argv[1]
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
if os.path.exists(out):
    os.remove(out)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for name in ALLOW:
        if os.path.isfile(name):
            z.write(name, name)
            continue
        for dp, dn, fn in os.walk(name):
            dn[:] = [d for d in dn if d not in SKIP_DIRS and not (len(d) > 1 and d[0] == "v" and d[1].isdigit())]
            for f in fn:
                if f.endswith(".pyc"):
                    continue
                full = os.path.join(dp, f)
                z.write(full, os.path.relpath(full, ".").replace(os.sep, "/"))
print("built", out)
