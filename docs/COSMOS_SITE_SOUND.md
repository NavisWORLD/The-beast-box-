COSMOS Sound: Unified browser audio

The shared Web Audio master/limiter now handles Next.js music, support, reactions and sprite voices. The site sound dock sets persisted mute, volume and music settings. Audio never plays before a trusted gesture; iPhone Safari may require unlocking again after navigation or background. The standalone Spark generator shares the site mute choice. The existing native GBA audio switch and emulator stay unchanged, with ducking when the game plays.

Acceptance: npm test, npm run typecheck, npm run build, 320/375/390/430 mobile checks, mute and persistent volume, background/resume, speaker and support chirp, native Game Boy continuity. Physical Safari remains unverified without real device testing.
