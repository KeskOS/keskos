#!/usr/bin/env bash
set -euo pipefail

theme_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/keskos-vscode-theme" && pwd)"
extensions_dir="${HOME}/.vscode/extensions"
target_dir="${extensions_dir}/local.keskos-crt-theme-0.0.1"

if [[ ! -f "${theme_root}/package.json" ]]; then
  echo "Theme root is missing package.json: ${theme_root}" >&2
  exit 1
fi

mkdir -p "${extensions_dir}"

if [[ -L "${target_dir}" || -d "${target_dir}" ]]; then
  rm -rf "${target_dir}"
fi

ln -s "${theme_root}" "${target_dir}"

echo "Installed KeskOS CRT theme as:"
echo "  ${target_dir}"
echo
echo "Next:"
echo "  1. Reload VS Code"
echo "  2. Open Preferences: Color Theme"
echo "  3. Select 'KeskOS CRT'"
