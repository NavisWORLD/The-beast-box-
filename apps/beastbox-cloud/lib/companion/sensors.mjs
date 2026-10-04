/**
 * Sensor readings are numbers only. Missing hardware stays off.
 * A simulated headband is opt-in and labeled; it never stands in for a live Muse.
 */

export function readCameraFrame(previous, current) {
  if (!current || !current.length) {
    return { available: false, motion: 0, brightness: 0, reason: "camera-off" };
  }
  let bright = 0;
  let motion = 0;
  const pixels = current.length / 4;
  for (let i = 0; i < current.length; i += 4) {
    const luma = (current[i] + current[i + 1] + current[i + 2]) / 3;
    bright += luma;
    if (previous && previous.length === current.length) motion += Math.abs(luma - ((previous[i] + previous[i + 1] + previous[i + 2]) / 3));
  }
  const brightness = pixels ? bright / pixels / 255 : 0;
  const motionScore = previous && pixels ? Math.min(1, motion / pixels / 255) : 0;
  return {
    available: true,
    motion: Math.round(motionScore * 1000) / 1000,
    brightness: Math.round(brightness * 1000) / 1000,
    reason: "camera",
  };
}

export function readMicSample(rms, previousRms, onset = 0.08) {
  if (rms === null || rms === undefined || !Number.isFinite(rms)) {
    return { available: false, loudness: 0, onset: false, reason: "mic-off" };
  }
  const loudness = Math.max(0, Math.min(1, rms));
  const before = Number.isFinite(previousRms) ? previousRms : 0;
  return {
    available: true,
    loudness: Math.round(loudness * 1000) / 1000,
    onset: before < onset && loudness >= onset,
    reason: "mic",
  };
}

export function readSignal(input = {}) {
  const museTraits = input.museTraits || null;
  const simulated = input.simulated || null;
  const enabled = input.enabled === true;
  if (!enabled && !museTraits) {
    return { available: false, mode: "off", focus: 0, calm: 0, spark: 0, reason: "signal-off" };
  }
  if (museTraits && Number.isFinite(museTraits.focus) && Number.isFinite(museTraits.calm) && Number.isFinite(museTraits.spark)) {
    return {
      available: true,
      mode: "muse",
      focus: museTraits.focus,
      calm: museTraits.calm,
      spark: museTraits.spark,
      reason: "muse",
    };
  }
  if (enabled && simulated && Number.isFinite(simulated.focus)) {
    return {
      available: true,
      mode: "simulated",
      focus: simulated.focus,
      calm: simulated.calm,
      spark: simulated.spark,
      reason: "simulated-headband",
    };
  }
  return { available: false, mode: "off", focus: 0, calm: 0, spark: 0, reason: museTraits ? "muse-incomplete" : "signal-off" };
}

export function sensorSummary(sensors) {
  const parts = [];
  if (sensors?.camera?.available) parts.push(`camera brightness ${sensors.camera.brightness}, motion ${sensors.camera.motion}`);
  else parts.push("camera off");
  if (sensors?.mic?.available) parts.push(`mic loudness ${sensors.mic.loudness}${sensors.mic.onset ? ", onset" : ""}`);
  else parts.push("mic off");
  if (sensors?.signal?.available) parts.push(`${sensors.signal.mode} focus ${sensors.signal.focus} calm ${sensors.signal.calm} spark ${sensors.signal.spark}`);
  else parts.push("headband off");
  return parts.join("; ");
}
