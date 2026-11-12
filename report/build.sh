#!/usr/bin/env bash
# Build the sprint report: report.pdf (pandoc + xelatex) and report.docx in the official Apart template styles.
set -euo pipefail
cd "$(dirname "$0")"
pandoc report.md -o report.pdf --pdf-engine=xelatex --resource-path=.:../reports -V colorlinks=true
pandoc report.md -o report.docx --reference-doc=apart_official_template.docx --resource-path=.:../reports
echo "built report/report.pdf and report/report.docx"
