# COSMOS Sensory Revival 006 — conditional browser on-device speech

**Status: source-only draft.** This experimental browser feature is additive to browser speech in PR #107 and the stacked numeric/PDF/CST work in PRs #109–#112. No offline ASR model was trained, downloaded by us, or deployed to the Railway host. It remains unsupported wherever the browser does not implement the necessary methods; actual iPhone acceptance is pending.

## Exact behavior

The owner can require **browser-supported on-device-only** speech from the existing Settings > Senses card. Enabling the checkbox by itself does not start the microphone, an ASR session or a download. The owner presses **Check local speech availability** to invoke the experimental `SpeechRecognition.available({langs:['en-US'],processLocally:true})` API. Only a browser-reported `available` response permits a separate **Start speech** click.

If the browser reports `downloadable`, a distinct owner click on **Install browser language pack** invokes the experimental `SpeechRecognition.install` API. The browser may download an English model into device storage, consuming network data, subject to the browser's Permissions-Policy and platform behavior. After installation the user must check availability again. No automatic download, service fallback, cloud API key, hosted inference, new paid resource, mic recording or persistent raw-audio storage is added.

At start, the code requires unprefixed `SpeechRecognition`, browser-reported local availability, a supported `processLocally` instance property, and verifies the property remains true after being set. If any check fails or `language-not-supported` is raised, the app shows an error and stops; it never silently enables remote recognition. The original separately consented browser recognizer remains available only if the owner switches off on-device-only mode, which explicitly warns audio may be processed by the browser provider. Browser behavior is not independently attested; inspect browser network privacy separately before relying on a local-processing claim.

Only short final transcripts enter the existing ephemeral 4-minute observation queue. The owner must independently opt in to temporary text context or to one approved durable text checkpoint. Existing camera, PDF, numeric and provider boundaries do not change. Hiding the tab/page exit stops recognition; no continuous iOS background listening.

## Review gates

- Verify Next.js typecheck, tests and build on exact commit, along with full Product CI; source-contract tests cannot establish mobile recognition capability.
- Test on a real HTTPS iPhone Safari and a browser explicitly supporting local recognition. Exercise unsupported API, denied mic, language unavailable, owner-approved language-pack download, successful recognized transcript, stop/hide, failed restart, expiry and refusal of cloud fallback.
- Verify network and no raw audio sent to Beast Box. Compare transcripts against user-selected test utterances; do not equate available API with observed recognition accuracy.
- Do not modify production, model provider permissions, host environment, memory volume, credentials or budgets for this stage. Leave stacked PR draft until ancestors and real-device acceptance pass.

API references: MDN SpeechRecognition.processLocally, SpeechRecognition.available(), SpeechRecognition.install(); each is experimental and browser-dependent.
