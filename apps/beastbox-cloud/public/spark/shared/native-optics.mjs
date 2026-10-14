export function gameObservationLine(observation) {
 if (observation?.status !== 'observed' || observation.source !== 'native-emulator-display') return '';
 const numeric = value => Number.isFinite(value) && value >= 0 && value <= 100 ? Math.round(value) : null;
 const brightness=numeric(observation.brightness),contrast=numeric(observation.contrast),change=numeric(observation.frameChange);
 if ([brightness,contrast,change].some(x=>x===null) || !['red','green','blue','mixed'].includes(observation.dominant)) return '';
 return 'Observed native game screen pixels on request: brightness '+brightness+'/100, contrast '+contrast+'/100, dominant colors '+observation.dominant+', frame-change '+change+'/100. This does NOT identify objects, enemies, map location, or actions.';
}

