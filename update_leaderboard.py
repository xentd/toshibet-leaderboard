#!/usr/bin/env python3
"""XENTED x ToshiBet leaderboard updater.

Reads player wagers from a source, masks the names, writes leaderboard.json
and (optionally) pushes it to GitHub so the GitHub Pages site updates itself.

Python 3.8+, standard library only.

  python update_leaderboard.py                 # run once
  python update_leaderboard.py --loop 600      # run every 10 minutes
  python update_leaderboard.py --no-git        # write the file only (testing)
  python update_leaderboard.py --force         # skip the safety checks once
"""
import argparse, csv, io, json, os, subprocess, sys, tempfile, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIN_LOOP = 300  # GitHub Pages rebuilds on every push; keep well under its build limits


def log(msg):
    print(datetime.now().strftime("%H:%M:%S"), msg, flush=True)


# ---- privacy: must match the hash in index.html exactly ----
def fnv(s):
    h = 0x811C9DC5
    for ch in s.strip().lower():
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return format(h, "08x")


def mask(n):
    n = n.strip()
    if len(n) <= 3:
        return n[0] + "••"
    return n[:2] + "•" * min(5, len(n) - 3) + n[-1]


# ---- sources ----
def rows_from_csv(path):
    text = Path(path).expanduser().read_text(encoding="utf-8-sig")
    return rows_from_csv_text(text)


def rows_from_csv_text(text):
    rd = csv.DictReader(io.StringIO(text))
    cols = {c.strip().lower(): c for c in (rd.fieldnames or [])}
    nk = next((cols[k] for k in ("name", "username", "user") if k in cols), None)
    wk = next((cols[k] for k in ("wagered", "wager", "total_wagered", "amount") if k in cols), None)
    if not nk or not wk:
        raise ValueError("CSV needs a name column and a wagered column")
    return [(r[nk], r[wk]) for r in rd]


def rows_from_json(obj, name_key, wager_key, list_key):
    if list_key:
        for part in list_key.split("."):
            obj = obj[part]
    return [(r[name_key], r[wager_key]) for r in obj]


def fetch_json_url(src):
    headers = {"User-Agent": "xented-leaderboard/1.0"}
    tok = os.environ.get(src.get("token_env", ""), "")
    if tok:
        headers[src.get("token_header", "Authorization")] = src.get("token_prefix", "Bearer ") + tok
    req = urllib.request.Request(src["url"], headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def read_source(cfg):
    src = cfg["source"]
    kind = src["type"]
    if kind == "csv":
        return rows_from_csv(src["path"])
    if kind == "json_url":
        return rows_from_json(fetch_json_url(src), src.get("name_key", "name"), src.get("wager_key", "wagered"), src.get("list_key", ""))
    if kind == "command":
        # any script of yours that prints CSV (name,wagered) or a JSON list to stdout
        out = subprocess.run(src["command"], shell=True, capture_output=True, text=True, timeout=src.get("timeout", 120), cwd=HERE)
        if out.returncode != 0:
            raise RuntimeError("command failed: " + out.stderr.strip()[:300])
        txt = out.stdout.strip()
        if txt.startswith(("[", "{")):
            return rows_from_json(json.loads(txt), src.get("name_key", "name"), src.get("wager_key", "wagered"), src.get("list_key", ""))
        return rows_from_csv_text(txt)
    raise ValueError("unknown source type: " + kind)


def to_number(v):
    return float(str(v).replace("$", "").replace(",", "").strip())


def build(cfg, rows):
    totals, shown = {}, {}
    for name, w in rows:
        name = str(name).strip()
        if not name:
            continue
        try:
            amt = to_number(w)
        except ValueError:
            continue
        if amt <= 0 or amt != amt:
            continue
        k = name.lower()
        totals[k] = totals.get(k, 0) + amt
        shown.setdefault(k, name)
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])[: int(cfg.get("top_n", 50))]
    players = [{"m": mask(shown[k]), "h": fnv(shown[k]), "w": round(v, 2)} for k, v in ranked]
    return {
        "demo": bool(cfg.get("demo", False)),
        "name": "Toshi Wager Race",
        "period": cfg["period"],
        "endsAt": cfg["ends_at"],
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "joinUrl": cfg["join_url"],
        "prizes": cfg["prizes"],
        "players": players,
    }


def atomic_write(path, text):
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def git(*args):
    return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True)


def push(msg):
    git("add", "leaderboard.json")
    if git("diff", "--cached", "--quiet").returncode == 0:
        return
    c = git("commit", "-m", msg)
    if c.returncode != 0:
        raise RuntimeError("git commit: " + (c.stderr or c.stdout).strip()[:300])
    for attempt in range(2):
        p = git("push")
        if p.returncode == 0:
            log("pushed")
            return
        git("pull", "--rebase", "--autostash")
    raise RuntimeError("git push failed: " + p.stderr.strip()[:300])


def run_once(cfg, args):
    out_path = HERE / "leaderboard.json"
    rows = read_source(cfg)
    new = build(cfg, rows)
    old = None
    if out_path.exists():
        try:
            old = json.loads(out_path.read_text(encoding="utf-8"))
        except ValueError:
            old = None

    # safety checks so a broken export never wipes the live board
    if not args.force:
        if not new["players"]:
            raise RuntimeError("source returned no valid players, keeping the old file (use --force to override)")
        if old and old.get("players") and not old.get("demo"):
            if new["players"][0]["w"] < old["players"][0]["w"] * 0.5:
                raise RuntimeError("top wager dropped by more than half, looks like bad data. Keeping the old file (use --force to override)")

    same = old and old.get("players") == new["players"] and all(old.get(k) == new[k] for k in ("period", "endsAt", "prizes", "joinUrl", "demo"))
    heartbeat = int(cfg.get("heartbeat_minutes", 30)) * 60
    fresh = False
    if old and old.get("updated"):
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(old["updated"].replace("Z", "+00:00"))).total_seconds()
        fresh = age < heartbeat
    if same and fresh:
        log("no change")
        return
    atomic_write(out_path, json.dumps(new, ensure_ascii=False, separators=(",", ":")))
    log(f"wrote leaderboard.json ({len(new['players'])} players, top {new['players'][0]['w'] if new['players'] else 0})")
    if not args.no_git:
        push("Update leaderboard " + new["updated"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--loop", type=int, default=0, help="repeat every N seconds (minimum %d)" % MIN_LOOP)
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    cfg_path = Path(args.config)
    if not cfg_path.exists():
        sys.exit("No config.json found. Copy config.example.json to config.json and edit it.")
    while True:
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            run_once(cfg, args)
        except Exception as e:
            log("ERROR: " + str(e))
            if not args.loop:
                sys.exit(1)
        if not args.loop:
            return
        time.sleep(max(MIN_LOOP, args.loop))


if __name__ == "__main__":
    main()
