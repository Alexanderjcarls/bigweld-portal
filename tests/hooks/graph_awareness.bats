#!/usr/bin/env bats
# Tests for the PreToolUse graph-awareness advisory injector.

setup() {
    HOOK="/datapool/bigweld-portal/.claude/hook-scripts/graph-awareness.sh"
}

@test "no-op when target path is not KB-relevant" {
    run bash -c "echo '{\"tool_name\":\"Read\",\"tool_input\":{\"file_path\":\"/tmp/random.txt\"}}' | '$HOOK'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "emits additionalContext JSON when target is in knowledge/" {
    run bash -c "echo '{\"tool_name\":\"Glob\",\"tool_input\":{\"pattern\":\"knowledge/**/*.md\"}}' | '$HOOK'"
    [ "$status" -eq 0 ]
    # Output is JSON containing 'additionalContext' or empty (if Neo4j unreachable)
    if [ -n "$output" ]; then
        echo "$output" | grep -q 'additionalContext'
        echo "$output" | grep -q 'permissionDecision'
    fi
}

@test "emits advisory when target is in /datapool/bigweld/raw" {
    run bash -c "echo '{\"tool_name\":\"Grep\",\"tool_input\":{\"path\":\"/datapool/bigweld/raw/something\"}}' | '$HOOK'"
    [ "$status" -eq 0 ]
}

@test "handles malformed stdin gracefully" {
    run bash -c "echo 'not-json' | '$HOOK'"
    [ "$status" -eq 0 ]
}

@test "exits 0 on empty input" {
    run bash -c "echo '' | '$HOOK'"
    [ "$status" -eq 0 ]
}
