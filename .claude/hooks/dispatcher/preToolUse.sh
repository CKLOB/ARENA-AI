#!/bin/bash
INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULES_DIR="$SCRIPT_DIR/modules"

[[ -d "$MODULES_DIR" ]] || exit 0

for hook in "$MODULES_DIR"/*/preToolUse.sh; do
    [[ -f "$hook" ]] || continue
    printf '%s\n' "$INPUT" | bash "$hook"
    STATUS=$?
    if [[ $STATUS -eq 2 ]]; then
        exit 2
    elif [[ $STATUS -ne 0 ]]; then
        exit $STATUS
    fi
done

exit 0
