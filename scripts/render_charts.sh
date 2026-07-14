#!/usr/bin/env bash
set -euo pipefail

CHARTS_DIR="docs/charts"

render_with_rsvg() {
  rsvg-convert "${CHARTS_DIR}/lastenheft-prozessuebersicht.svg" \
    -o "${CHARTS_DIR}/lastenheft-prozessuebersicht.png"
  rsvg-convert "${CHARTS_DIR}/pflichtenheft-systemarchitektur.svg" \
    -o "${CHARTS_DIR}/pflichtenheft-systemarchitektur.png"
  rsvg-convert "${CHARTS_DIR}/pflichtenheft-step-engine.svg" \
    -o "${CHARTS_DIR}/pflichtenheft-step-engine.png"
}

if command -v rsvg-convert >/dev/null 2>&1; then
  render_with_rsvg
elif command -v docker >/dev/null 2>&1; then
  docker run --rm --user "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    -e XDG_CACHE_HOME=/tmp \
    -v "$PWD:/data" \
    -v /tmp:/tmp \
    -v /usr/share/fonts:/usr/share/fonts:ro \
    --entrypoint sh pandoc/core \
    -lc 'rsvg-convert /data/docs/charts/lastenheft-prozessuebersicht.svg -o /data/docs/charts/lastenheft-prozessuebersicht.png && rsvg-convert /data/docs/charts/pflichtenheft-systemarchitektur.svg -o /data/docs/charts/pflichtenheft-systemarchitektur.png && rsvg-convert /data/docs/charts/pflichtenheft-step-engine.svg -o /data/docs/charts/pflichtenheft-step-engine.png'
else
  echo "Neither rsvg-convert nor docker is available. Cannot render charts." >&2
  exit 1
fi

echo "Rendered chart PNG files in ${CHARTS_DIR}"
