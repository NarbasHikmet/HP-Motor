#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# venv (varsa)
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export PYTHONPATH="$PWD/tools${PYTHONPATH:+:$PYTHONPATH}"

echo "[1/5] reports pipeline"
python tools/run_reports_pipeline.py

echo "[2/5] summaries"
python tools/make_summaries.py
python tools/make_goal_timing_profiles.py
python tools/make_manifest.py

echo "[3/5] export"
# hp_export bashrc fonksiyonu değilse fallback: manuel export
TS="$(date +%Y%m%d_%H%M%S)"
SRC="artifacts/reports/normalized"
OUT="out/exports/$TS"
mkdir -p "$OUT"

need=(
  "$SRC/standings__normalized.csv"
  "$SRC/goal_timing__normalized.csv"
  "$SRC/passes_players_split__normalized.csv"
)

for f in "${need[@]}"; do
  [ -f "$f" ] || { echo "[ERR] missing: $f"; exit 2; }
done

cp -f "${need[@]}" "$OUT/"

# optional normalized
[ -f "$SRC/passes_aggregate__normalized.csv" ] && cp -f "$SRC/passes_aggregate__normalized.csv" "$OUT/"
[ -f "$SRC/passes_clean__normalized.csv" ] && cp -f "$SRC/passes_clean__normalized.csv" "$OUT/"
[ -f "$SRC/tables_catalog.txt" ] && cp -f "$SRC/tables_catalog.txt" "$OUT/"

# summaries + manifest
[ -d out/summaries ] && cp -f out/summaries/*.csv out/summaries/*.json "$OUT/" 2>/dev/null || true

# zip
mkdir -p out/exports
( cd out/exports && zip -r "$TS.zip" "$TS" >/dev/null )

echo "[4/5] copy zip to Downloads"
LATEST_ZIP="out/exports/$TS.zip"
mkdir -p ~/storage/downloads
cp -f "$LATEST_ZIP" ~/storage/downloads/

echo "[OK] zip -> $LATEST_ZIP"
echo "[OK] copied -> ~/storage/downloads/$(basename "$LATEST_ZIP")"
echo "[OK] contents:"
zipinfo -1 "$LATEST_ZIP" | sed -n '1,200p'
