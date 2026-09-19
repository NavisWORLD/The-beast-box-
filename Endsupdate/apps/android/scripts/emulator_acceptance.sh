#!/usr/bin/env bash
set -euo pipefail
output="${1:-acceptance}"
mkdir -p "$output"
package=dev.beastbox.mobile
phase=0
for method in phase1InitializeAndWriteA phase2ReopenAndWriteB phase3ReopenAndWriteA; do
  phase=$((phase + 1))
  adb shell am force-stop "$package"
  adb shell am instrument -w -r \
    -e class "dev.beastbox.mobile.RuntimeAcceptanceTest#$method" \
    "$package.test/androidx.test.runner.AndroidJUnitRunner" | tee "$output/phase-$phase.log"
  grep -Eq 'OK \(1 test\)' "$output/phase-$phase.log"
  if grep -Eq 'FAILURES|INSTRUMENTATION_FAILED|Process crashed' "$output/phase-$phase.log"; then exit 1; fi
  adb exec-out run-as "$package" cat "files/android-phase-$phase.json" > "$output/android-phase-$phase.json"
done
