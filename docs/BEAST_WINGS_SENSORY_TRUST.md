# Beast Wings sensory permission and timestamp integrity fix

The existing browser released device tracks on Stop, but it could still carry unsent camera labels/transcripts under an earlier include-in-chat or persistence selection. The fix now clears the stopped modality's unsent observations and resets context and memory opt-ins when capture stops; hiding the app or selecting Stop all clears all such selections. It clears the parent's selected context immediately, too.

This does not revoke operating-system/browser-level camera/mic permission and does not retroactively erase already persisted records. Those require separate browser settings or owner-memory correction.

The Python sensory freshness check previously accepted future-dated or non-finite times and interpreted now=0 as an absent argument. It now fails closed for those values. The new tests are fixtures, not evidence of live physical hardware capture.

Preserve owner privacy and the unmerged production-backup gate: these edits are not authorization to deploy to Railway before real volume backup and isolated restore validation.

Backend device-memory persistence now has a separate default-deny capability provisioned only by trusted host configuration. Master privacy stop and model handoff revoke it. The owner route reports actual session readiness and checks admission under the same short stop lock used by master stop, but already-admitted writes cannot be undone. The cloud cannot grant the capability; a trusted host operation is required for reapproval. The web master-stop click immediately stops local streams and unsent selected context before waiting for a remote reply. A failed remote call must be shown as unconfirmed, and already copied drafts, sent messages or persisted memory are not retroactively erased.

A separate synthetic runtime regression now verifies exact temporary text reaches the **host-to-provider-delegate** prompt boundary and stores only a bounded receipt, not the raw transient prompt. The UI displays this boundary explicitly without claiming third-party provider delivery or interpretation. Withdrawal of sensor consent during asynchronous context staging blocks *new* chat submission; an already-started call remains nonpreemptible and must be reconciled.

The SECOND owner-device numeric sample panel now subscribes to the same master-stop browser event, stops both streams and drops unsubmitted samples/consent. Both browser camera entry points and the numeric microphone entry point use monotonic request epochs, so a camera/microphone permission prompt that resolves AFTER a stop cannot quietly reattach new tracks. Device-sample stop clears only unsubmitted samples; it cannot recall text the owner already copied to a chat draft. Headless source-contract tests do not establish physical-device acceptance on iPhone.
