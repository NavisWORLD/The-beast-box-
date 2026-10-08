# QBEAST Menagerie — recorded-seed gallery

This change adds a read-only habitat collection to the **existing** Beast Cage at \`/beast-cage#menagerie\`. It is not a second creature system, wallet, marketplace, or instance of the native game.

- \`loadSparkRuns()\` reads the same allowlisted public recorded-count tables already used by the generator.
- \`buildGenome()\` creates deterministic example genomes from explicitly fixed example trait recipes.
- \`buildQbeast()\` derives their deterministic QBEAST1 profile IDs. The gallery labels these **DERIVED PREVIEW · NOT IN YOUR SAVE**. They are not owned/saved creatures, rarity rankings, or earned progress.
- \`PixelBeast publicSpark\` uses the original 64×64 sprite pipeline. Stage 1 archive portraits are static for mobile performance; the active saved Beast is shown separately with its actual ID, stage, energy, bond, and XP.
- Backend strings containing QVM/simulator are marked SIMULATOR. IBM published recorded counts are labeled RECORDED IBM COUNTS, **not** live QPU access or persistent quantum computation.
- The gallery never calls \`change()\`, creates native save data, alters a signed QBEAST record, or gives any scientific/game authority.

Verification: \`npm test\`, \`npm run typecheck\`, \`npm run build\`, and browser/mobile checks. Physical iPhone Safari must be labeled unverified until tested on hardware. V11.3 ROM and Game Boy shell remain unchanged.
