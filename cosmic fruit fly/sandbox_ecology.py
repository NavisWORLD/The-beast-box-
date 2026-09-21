"""Virtual-only ecology and perception for the fruit-fly research sandbox.

The 96x64 virtual camera sees synthetic coloured object sprites, not the decorative
forest picture. Navigation must use decoded pixels and simulated odor, NOT access
object coordinates. Reproduction is a software spawn, not a biological lifecycle.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from sandbox_sensors import camera as stone_camera, in_view, FOV, WIDTH, HEIGHT, RANGE, odor, collision

PALETTE = {
    'stick': (184, 108, 61), 'leaf': (86, 229, 110),
    'seed': (235, 104, 191), 'nest': (139, 111, 236),
    'patch': (103, 191, 240), 'food': (255, 195, 47),
}
POSITIONS = {
    'stick': (-1.65, -1.91), 'leaf': (.15, -1.91),
    'seed': (1.35, -1.91), 'nest': (-2.8, -1.91),
    'patch': (2.48, -1.91), 'food': (2.10, -2.43),
}
ACTIONS = ('scan','inspect','move','turn','pickup','carry','place','build','plant','grow','feed','reproduce','offspring_feed','rest','explore','type_token')


def present(state: dict) -> dict:
    """Visible world objects only: held/consumed items disappear from camera."""
    taken = state['removed']
    return {name: pos for name, pos in POSITIONS.items() if name not in taken}


def retinal_image(pos, heading, shown: dict):
    """Returns egocentric pixels. The semantic label is recoverable by color ONLY."""
    im = stone_camera(pos, heading, ())
    yy, xx = np.ogrid[:HEIGHT, :WIDTH]
    for name, target in shown.items():
        visible, bearing, distance = in_view(pos, heading, target)
        if not visible:
            continue
        cx = round((.5 + bearing / FOV) * WIDTH)
        cy = round(HEIGHT * (.52 + .2 * (1. - distance / RANGE)))
        radius = max(2, round(11 / max(1., distance)))
        # Semantic colors encode object type, never future success or reward.
        im[(xx-cx)**2 + (yy-cy)**2 <= radius**2] = PALETTE[name]
    return im


def interpret_retina(rgb):
    observations = {}
    for name, color in PALETTE.items():
        mask = np.all(rgb == color, axis=2)
        ys, xs = np.where(mask)
        observations[name] = {'seen': bool(len(xs)), 'pixel_count': int(len(xs)),
            'bearing': round((float(xs.mean())/WIDTH-.5)*FOV, 5) if len(xs) else None,
            'confidence': round(min(1.,len(xs)/40.),4)}
    return observations


def sense(pos, heading, shown, goal, last_touch=False):
    pixels = retinal_image(pos, heading, shown)
    objects = interpret_retina(pixels)
    # The task manager provides only a goal *label*. Environment renders scent
    # from the object's actual location; coordinates are never returned to policy.
    scent = odor(pos, heading, (shown[goal],))[0] if goal in shown else (0.,0.,0.)
    return {'objects': objects, 'odor': scent, 'touch': bool(last_touch),
            'heading': round(heading, 5)}


def allowed(requested, enabled):
    return requested in ACTIONS and requested in enabled


def apply_action(state: dict, kind: str, pos, enabled: frozenset, tick: int):
    """Default-deny, proximity-checked state transitions; no host capabilities."""
    if not allowed(kind, enabled):
        return 'DENIED:'+kind
    inv = state['inventory']
    near = lambda name: math.dist(pos, POSITIONS[name]) < .35
    if kind == 'pickup':
        for name in ('stick','leaf','seed'):
            if near(name) and name not in state['removed'] and len(inv) == 0:
                inv.append(name)
                state['removed'].add(name)
                return 'PICKUP:'+name
        return 'FAILED:pickup'
    if kind == 'place':
        if inv and near('nest') and inv[0] in ('stick','leaf'):
            name = inv.pop()
            state['deposited'].add(name)
            return 'PLACE:'+name
        return 'FAILED:place'
    if kind == 'build':
        if near('nest') and {'stick','leaf'} <= state['deposited'] and not state['nest_built']:
            state['nest_built'] = True
            return 'BUILD:NEST'
        return 'FAILED:build'
    if kind == 'plant':
        if near('patch') and inv == ['seed'] and not state['planted']:
            inv.clear()
            state['planted'] = True
            state['plant_tick'] = tick
            return 'PLANT:SEED'
        return 'FAILED:plant'
    if kind == 'grow':
        if near('patch') and state['planted'] and tick-state['plant_tick']>=12 and not state['grown']:
            state['grown'] = True
            return 'GROW:PATCH'
        return 'FAILED:grow'
    if kind == 'feed':
        if near('food') and state['grown'] and 'food' not in state['removed']:
            state['energy'] += 1
            state['removed'].add('food')
            return 'FEED:FOOD'
        return 'FAILED:feed'
    if kind == 'reproduce':
        if near('nest') and state['nest_built'] and state['grown'] and state['energy'] >= 1 and not state['offspring']:
            state['energy'] -= 1
            state['offspring'] = {'id':'offspring-1','pos': list(pos), 'inherited_prior': .125, 'age': 0, 'fed': False}
            state['removed'].discard('food') # explicit virtual replenishment for offspring test
            return 'REPRODUCE:SIMULATED_OFFSPRING'
        return 'FAILED:reproduce'
    if kind == 'offspring_feed':
        if state['offspring'] is not None and near('food') and 'food' not in state['removed']:
            state['removed'].add('food')
            state['offspring']['fed'] = True
            return 'OFFSPRING:FOOD_FOUND'
        return 'FAILED:offspring_feed'
    if kind in ('scan','inspect','move','turn','carry','rest','explore','type_token'):
        return kind.upper()
    return 'DENIED:'+kind
