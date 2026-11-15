#!/usr/bin/env bash
# Build the sprint report in the official Apart template structure (iteration 13, D133).
#
#   report/build.sh             report.md -> report.tex (pandoc, template apart.latex, filter apart.lua)
#                               -> check_tex.py -> xelatex (twice) -> report.pdf;  report.md -> report.docx
#   report/build.sh --from-tex  skip the pandoc stage: rebuild report.pdf from a hand-edited report.tex
#                               (check_tex.py must pass: the edited .tex holds exactly the numbers of report.md)
#
# report.md itself is generated: `python report/fill.py` (report.src.md + analysis outputs -> report.md).
set -euo pipefail
cd "$(dirname "$0")"
# Byte-identical rebuilds (iteration 12, D130): fixed document dates for xelatex/xdvipdfmx and the DOCX writer.
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1794722400}" FORCE_SOURCE_DATE=1

from_tex=0
case "${1:-}" in
  --from-tex) from_tex=1 ;;
  "") ;;
  *) echo "usage: report/build.sh [--from-tex]" >&2; exit 2 ;;
esac

if [ "$from_tex" -eq 0 ]; then
  pandoc report.md -s --template=apart.latex --lua-filter=apart.lua -V colorlinks=true -o report.tex
fi
python3 check_tex.py

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
for pass in 1 2; do
  if ! xelatex -interaction=nonstopmode -halt-on-error -output-directory="$work" report.tex > "$work/xelatex.out" 2>&1; then
    tail -40 "$work/xelatex.out" >&2
    echo "build: xelatex failed (pass $pass)" >&2
    exit 1
  fi
done
cp "$work/report.pdf" report.pdf

if [ "$from_tex" -eq 0 ]; then
  pandoc report.md -o report.docx --reference-doc=apart_official_template.docx --resource-path=.:../reports
  echo "built report/report.tex, report/report.pdf and report/report.docx"
else
  echo "built report/report.pdf from report/report.tex (report.docx unchanged: it is built from report.md)"
fi
