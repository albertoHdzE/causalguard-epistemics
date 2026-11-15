#!/usr/bin/env bash
# Build the sprint report: report.pdf (pandoc + xelatex) and report.docx in the official Apart template styles.
set -euo pipefail
cd "$(dirname "$0")"
# Byte-identical rebuilds (iteration 12, D130): fixed document dates for xelatex/xdvipdfmx and the DOCX writer.
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1794722400}" FORCE_SOURCE_DATE=1
pandoc report.md -o report.pdf --pdf-engine=xelatex --resource-path=.:../reports -V colorlinks=true
pandoc report.md -o report.docx --reference-doc=apart_official_template.docx --resource-path=.:../reports
echo "built report/report.pdf and report/report.docx"
