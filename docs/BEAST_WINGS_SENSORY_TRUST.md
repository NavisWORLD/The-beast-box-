# Beast Wings sensory permission and timestamp integrity fix

The existing browser released device tracks on Stop, but it could still carry unsent camera labels/transcripts under an earlier include-in-chat or persistence selection. The fix now clears the stopped modality's unsent observations and resets context and memory opt-ins when capture stops; hiding the app or selecting Stop all clears all such selections. It clears the parent's selected context immediately, too.

This does not revoke operating-system/browser-level camera/mic permission and does not retroactively erase already persisted records. Those require separate browser settings or owner-memory correction.

The Python sensory freshness check previously accepted future-dated or non-finite times and interpreted now=0 as an absent argument. It now fails closed for those values. The new tests are fixtures, not evidence of live physical hardware capture.

Preserve owner privacy and the unmerged production-backup gate: these edits are not authorization to deploy to Railway before real volume backup and isolated restore validation.
