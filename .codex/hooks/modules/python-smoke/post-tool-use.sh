#!/bin/bash
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')

[[ "$TOOL_NAME" == "Edit" || "$TOOL_NAME" == "Write" || "$TOOL_NAME" == "write_file" ]] || exit 0

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

[[ "$FILE_PATH" == *.py ]] || exit 0

if [[ "$FILE_PATH" == /* ]]; then
    FILE_ABS="$FILE_PATH"
elif [[ -n "$CWD" ]]; then
    FILE_ABS="$CWD/$FILE_PATH"
else
    exit 0
fi

PROJECT_ROOT=$(git -C "$(dirname "$FILE_ABS")" rev-parse --show-toplevel 2>/dev/null)
[[ -z "$PROJECT_ROOT" ]] && PROJECT_ROOT="$CWD"
[[ -z "$PROJECT_ROOT" ]] && exit 0

if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON="python"
fi

echo "[Hook] Running py_compile for $(basename "$FILE_ABS") ..." >&2
exec "$PYTHON" -m py_compile "$FILE_ABS"
