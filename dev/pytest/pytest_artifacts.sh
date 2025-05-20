#!/bin/bash
set -x

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
cd "$SCRIPT_DIR/../.."

pytest microcoin/tests/artifact_tests/