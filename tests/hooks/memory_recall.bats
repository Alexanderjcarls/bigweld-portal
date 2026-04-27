#!/usr/bin/env bats
# Tests for the UserPromptSubmit memory-recall hook.
# Live tests against the running Neo4j substrate; if substrate is down,
# the hook should soft-fail with empty stdout (those tests would skip).

setup() {
    TMPDIR=$(mktemp -d)
    export BIGWELD_PORTAL_ROOT="$TMPDIR"
    export BIGWELD_CONVERSATION_ID="bats-test"
    HOOK="/datapool/bigweld-portal/.claude/hook-scripts/memory-recall.sh"
}

teardown() { rm -rf "$TMPDIR"; }

@test "no-op when BIGWELD_CONVERSATION_ID unset" {
    unset BIGWELD_CONVERSATION_ID
    run bash -c "echo '{\"prompt\":\"asset_stage\"}' | '$HOOK'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "no-op when prompt is empty" {
    run bash -c "echo '{\"prompt\":\"\"}' | '$HOOK'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "no-op when prompt is too short (< 8 chars)" {
    run bash -c "echo '{\"prompt\":\"hi\"}' | '$HOOK'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "soft-fails when stdin is malformed JSON" {
    run bash -c "echo 'not-json-at-all' | '$HOOK'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "produces additionalContext for substantive KB-relevant prompt" {
    # Live test: requires Neo4j running + DEEPINFRA_API_KEY available.
    # If either is unavailable the hook soft-fails (empty stdout) and we skip.
    output=$(echo '{"prompt":"What is SFDC asset_stage promotion logic?"}' | "$HOOK" 2>/dev/null)
    if [ -z "$output" ]; then
        skip "substrate unreachable (Neo4j or embed API down)"
    fi
    echo "$output" | grep -q "hookSpecificOutput"
    echo "$output" | grep -q "additionalContext"
}

@test "second fire of same prompt is deduped within 30 min" {
    # Fire once
    out1=$(echo '{"prompt":"Bigweld dedup test prompt about asset_stage"}' | "$HOOK" 2>/dev/null)
    if [ -z "$out1" ]; then
        skip "substrate unreachable"
    fi
    # Fire again immediately — should be silent
    out2=$(echo '{"prompt":"Bigweld dedup test prompt about asset_stage"}' | "$HOOK" 2>/dev/null)
    [ -z "$out2" ]
}
