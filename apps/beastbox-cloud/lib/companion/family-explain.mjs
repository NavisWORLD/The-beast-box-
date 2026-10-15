/**
 * Family explanation of a creature from evidence already on the record.
 * Reads seed, memory, and growth. Does not invent jobs, receipts, training, or a mind.
 */

const SCHEMA = 'beastbox-family-explain-v1';

const NEXT = {
  talk: 'Talk sends your words to the voice you picked.',
  rest: 'Rest lowers activity and raises energy in the local rules.',
  play: 'Play is a tap here, on this device.',
  save: 'Save keeps this creature on this device.',
  explore: 'Explore uses the local behavior rules to pick a next action.',
};

function record(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function clean(value, max = 80) {
  if (typeof value !== 'string') return '';
  const text = value.replace(/[\u0000-\u001f]+/g, ' ').replace(/\s+/g, ' ').trim();
  return text.length > max ? text.slice(0, max).trim() : text;
}

function nonEmpty(value) {
  return typeof value === 'string' && value.trim() ? value : null;
}

function finite(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function quantumOf(input) {
  const genome = record(input.genome);
  const quantum = genome.quantum;
  return quantum && typeof quantum === 'object' && !Array.isArray(quantum) ? quantum : null;
}

function growthOf(input) {
  const growth = input.growth;
  return growth && typeof growth === 'object' && !Array.isArray(growth) ? growth : null;
}

function behaviorOf(input) {
  const behavior = input.behavior;
  return behavior && typeof behavior === 'object' && !Array.isArray(behavior) ? behavior : null;
}

function isArtist(input) {
  const origin = typeof input.origin === 'string' ? input.origin : '';
  if (input.artist === true) return true;
  if (typeof input.artist === 'string' && input.artist.trim()) return true;
  return origin.includes('ARTIST-DRAWN');
}

function recordedIbm(input) {
  const quantum = quantumOf(input);
  if (!quantum) return false;
  const backend = typeof quantum.backend === 'string' ? quantum.backend : '';
  return quantum.source_class === 'RECORDED_IBM_HARDWARE' || backend.startsWith('ibm_');
}

function rigettiJobId(input) {
  const growth = growthOf(input);
  if (!growth || growth.status !== 'RIGETTI_QVM_REMOTE') return null;
  return nonEmpty(growth.job_id);
}

function localClassical(input) {
  const growth = growthOf(input);
  const behavior = behaviorOf(input);
  return growth?.source === 'LOCAL_CLASSICAL_QVM_INSPIRED' || behavior?.idleOrigin === 'ARTIST_CLASSICAL_LOCAL';
}

function seedText(input) {
  const name = clean(input.name, 60);
  if (isArtist(input)) {
    return `${name ? `${name} is` : 'This creature is'} artist-drawn · no quantum seed.`;
  }
  if (recordedIbm(input)) {
    const lead = name
      ? `${name}'s starting seed is a recorded measurement already saved with this creature.`
      : 'The starting seed is a recorded measurement already saved with this creature.';
    return `${lead} It is not a new run.`;
  }
  if (typeof input.quantumSeed === 'string' && input.quantumSeed.trim()) {
    return `${name ? `${name} has` : 'This creature has'} a starting seed saved with it. It is not a new run.`;
  }
  if (input.quantumSeed === null) {
    return `${name ? `${name} has` : 'This creature has'} no quantum seed on this view.`;
  }
  const genome = record(input.genome);
  if (typeof genome.seed === 'string' && genome.seed.trim()) {
    return `${name ? `${name} has` : 'This creature has'} a starting seed saved with it.`;
  }
  const origin = clean(input.origin, 80);
  if (origin) return `${name ? `${name} started from` : 'This creature started from'} ${origin}.`;
  return 'No starting seed is saved for this view.';
}

function answerText(input) {
  const answered = record(input.answeredBy);
  const provider = nonEmpty(answered.provider);
  if (!provider) return '';
  const key = provider.trim().toLowerCase();
  if (key === 'rawrphos' || key === 'guest-rawrphos') return 'RAWRPHØS answered.';
  return `The reply came from ${clean(provider, 60)}.`;
}

function teacherText(input) {
  const teacher = input.teacher;
  if (!teacher || typeof teacher !== 'object' || Array.isArray(teacher)) return '';
  const picked = clean(teacher.name, 40);
  const who = picked ? ` You picked ${picked}.` : '';
  return `A teacher is the voice you picked.${who} It is not training. This creature was not trained and did not absorb that model's knowledge.`;
}

function memoryText(input) {
  const count = input.memoryCount;
  let line;
  if (Number.isInteger(count) && count >= 0 && count < 1e7) {
    if (count === 0) line = 'It has no saved talks yet.';
    else if (count === 1) line = 'It remembers 1 saved talk on this device.';
    else line = `It remembers ${count} saved talks on this device.`;
  } else {
    line = 'No saved talk count is on this view.';
  }
  const parts = [`${line} Saved memory is a note, not an optimizer update.`];
  const teacher = teacherText(input);
  if (teacher) parts.push(teacher);
  const answer = answerText(input);
  if (answer) parts.push(answer);
  return parts.join(' ');
}

function behaviorText(input) {
  const behavior = behaviorOf(input);
  const parts = [];
  if (!behavior) {
    parts.push('No current move is saved for this view.');
  } else {
    const label = clean(behavior.idleLabel, 60);
    const action = clean(behavior.lastAction, 40);
    if (label) parts.push(`Right now it is ${label}.`);
    if (action) parts.push(`The last move was ${action}.`);
    if (!label && !action) parts.push('No current move is saved for this view.');
    const energy = finite(behavior.energy);
    const curiosity = finite(behavior.curiosity);
    if (energy !== null) parts.push(`Energy is ${energy}.`);
    if (curiosity !== null) parts.push(`Curiosity is ${curiosity}.`);
  }
  parts.push('These scores are a pretend mood, not a real mind.');
  return parts.join(' ');
}

function growthText(input) {
  const growth = growthOf(input);
  const local = localClassical(input);
  if (!isArtist(input) && rigettiJobId(input)) {
    return 'A remote Rigetti QVM simulator receipt is saved. It is a simulator, not a quantum chip.';
  }
  if (local) {
    const base = 'Growth uses a local rule on this device. It is not hardware and not a remote simulator job.';
    return growth ? base : `${base} No growth job has been run for this view.`;
  }
  return 'No growth job has been run for this view.';
}

function nextText(input) {
  const action = input.nextAction;
  if (typeof action === 'string' && Object.prototype.hasOwnProperty.call(NEXT, action)) return NEXT[action];
  return 'No next action is picked yet.';
}

function copyCounts(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const counts = {};
  for (const key of Object.keys(value)) {
    const shot = value[key];
    if (typeof shot === 'number' && Number.isFinite(shot)) counts[key] = shot;
  }
  return Object.keys(counts).length ? counts : null;
}

function classify(input) {
  if (isArtist(input)) return { hardwareClass: 'none', jobId: null, provider: null };
  if (recordedIbm(input)) {
    const quantum = quantumOf(input);
    return {
      hardwareClass: 'recorded-ibm-hardware',
      jobId: nonEmpty(quantum.job_id),
      provider: nonEmpty(quantum.backend),
    };
  }
  const jobId = rigettiJobId(input);
  if (jobId) {
    return {
      hardwareClass: 'rigetti-qvm-simulator',
      jobId,
      provider: nonEmpty(growthOf(input).backend),
    };
  }
  if (localClassical(input)) return { hardwareClass: 'local-classical', jobId: null, provider: null };
  return { hardwareClass: null, jobId: null, provider: null };
}

function advancedOf(input) {
  const kind = classify(input);
  const growth = growthOf(input);
  const quantum = quantumOf(input);
  const digest = !isArtist(input) && recordedIbm(input) ? nonEmpty(quantum?.counts_sha256) : null;
  return {
    provider: kind.provider,
    hardwareClass: kind.hardwareClass,
    jobId: kind.jobId,
    timestamp: null,
    shots: growth ? finite(growth.shots) : null,
    counts: growth ? copyCounts(growth.counts) : null,
    circuitHash: null,
    receiptDigest: digest,
    creatureId: nonEmpty(input.id),
    growthEventId: growth ? nonEmpty(growth.event_id) : null,
    validation: null,
    quota: null,
    error: null,
    checkpoint: null,
  };
}

export function explainCreature(input, options) {
  const src = record(input);
  const mode = options && options.mode === 'advanced' ? 'advanced' : 'friendly';
  return {
    schema: SCHEMA,
    mode,
    friendly: {
      seed: seedText(src),
      memory: memoryText(src),
      behavior: behaviorText(src),
      growth: growthText(src),
      next: nextText(src),
    },
    advanced: mode === 'advanced' ? advancedOf(src) : null,
  };
}
