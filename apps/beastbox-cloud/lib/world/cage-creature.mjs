// The "Creature" switch for the cage (Cory, Oct 26 2026). ON (default) shows the beast in the open scene; OFF shows the universe alone.
// One saved choice, shared by the dock's "Show {beast}" row, the cage's "Creature" switch and the scene itself. Display only: it never
// removes, pauses or changes the beast, its identity, its growth or its saves.
export const CAGE_CREATURE_KEY = 'beastbox.cage.creature.v1';
export const CAGE_CREATURE_EVENT = 'beastbox:cage-creature';
/** Missing, unreadable or anything but an explicit "off" means ON, so today's behavior is unchanged until a visitor flips it. */
export function readCageCreature(storage) {
  try { return storage?.getItem(CAGE_CREATURE_KEY) !== 'off'; } catch { return true; }
}
export function writeCageCreature(storage, on) {
  try { storage?.setItem(CAGE_CREATURE_KEY, on ? 'on' : 'off'); } catch { /* private mode: the switch still works for this visit */ }
  return Boolean(on);
}
/** The words shared by every place the switch appears (Emeth's labels, 44 characters or fewer). */
export function cageCreatureWords(name) {
  const n = String(name || '').trim() || 'Your beast';
  const N = n.charAt(0).toUpperCase() + n.slice(1);
  return {
    switchLabel: 'Creature',
    dockLabel: `Show ${n}`,
    stateOn: `${N} is out front`,
    stateOff: `${N} is resting out of view`,
    ariaOn: `Hide ${n} from the front of the cage`,
    ariaOff: `Show ${n} at the front of the cage`,
    note: `Turn this off to see the whole cage with nothing in front. ${N} is still there and still alive.`,
  };
}
