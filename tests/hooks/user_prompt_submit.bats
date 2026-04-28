#!/usr/bin/env bats
# Tests for the UserPromptSubmit transcript-persist hook.

setup() {
    TMPDIR=$(mktemp -d)
    export BIGWELD_CONVERSATION_FILE="$TMPDIR/conv.json"
    export BIGWELD_CONVERSATION_ID="test-conv-id"
    HOOK="/datapool/bigweld-portal/.claude/hook-scripts/user-prompt-submit.sh"
}

teardown() {
    rm -rf "$TMPDIR"
}

@test "no-op when BIGWELD_CONVERSATION_ID unset" {
    unset BIGWELD_CONVERSATION_ID
    run bash -c "echo '{\"prompt\":\"hi\"}' | '$HOOK'"
    [ "$status" -eq 0 ]
    [ ! -f "$BIGWELD_CONVERSATION_FILE" ]
}

@test "no-op when BIGWELD_CONVERSATION_FILE unset" {
    unset BIGWELD_CONVERSATION_FILE
    run bash -c "echo '{\"prompt\":\"hi\"}' | '$HOOK'"
    [ "$status" -eq 0 ]
}

@test "appends user event with content + ts + conv_id" {
    echo '{"prompt":"hello bigweld"}' | "$HOOK"
    [ -f "$BIGWELD_CONVERSATION_FILE" ]
    last_line=$(tail -1 "$BIGWELD_CONVERSATION_FILE")
    echo "$last_line" | grep -Eq '"type": ?"user"'
    echo "$last_line" | grep -Eq '"content": ?"hello bigweld"'
    echo "$last_line" | grep -Eq '"conv_id": ?"test-conv-id"'
    echo "$last_line" | grep -Eq '"ts":'
}

@test "concurrent appends do not interleave" {
    for i in $(seq 1 10); do
        echo "{\"prompt\":\"msg$i\"}" | "$HOOK" &
    done
    wait
    line_count=$(wc -l < "$BIGWELD_CONVERSATION_FILE")
    [ "$line_count" -eq 10 ]
    while IFS= read -r line; do
        echo "$line" | python3 -c 'import json,sys; json.loads(sys.stdin.read())'
    done < "$BIGWELD_CONVERSATION_FILE"
}

@test "handles malformed stdin gracefully" {
    run bash -c "echo 'not json' | '$HOOK'"
    [ "$status" -eq 0 ]
    # Hook still appends (with empty content) rather than crashing
    [ -f "$BIGWELD_CONVERSATION_FILE" ]
}
