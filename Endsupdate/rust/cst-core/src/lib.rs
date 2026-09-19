//! COSMOS/CST Rust reference primitives.
//!
//! This crate mirrors the public reference mechanics packaged in The Beast Box.
//! It is not a byte-for-byte claim about private historical COSMOS source and it
//! does not turn the early CST cosmology language into established physical law.

use std::fmt;

pub const PHI: f64 = 1.618_033_988_749_895;

#[derive(Debug, Clone, PartialEq)]
pub enum CstError {
    EmptyDrive,
    LengthMismatch { left: usize, right: usize },
    NonPositiveSigma,
}

impl fmt::Display for CstError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyDrive => write!(f, "drive must contain at least one scalar"),
            Self::LengthMismatch { left, right } => write!(f, "state-vector length mismatch: {left} != {right}"),
            Self::NonPositiveSigma => write!(f, "sigma must be positive"),
        }
    }
}

impl std::error::Error for CstError {}

/// Auditable 12-scalar reference update used by the public Beast Box package.
///
/// The documented CST idea is an Omega-driven leaky 12D control state. The exact
/// historical/private Omega implementation is not invented here; this function
/// mirrors the public Python reference dynamic so cross-language tests can agree.
pub fn update_dyn12(state: &[f64; 12], drive: &[f64], step: u64) -> Result<[f64; 12], CstError> {
    if drive.is_empty() {
        return Err(CstError::EmptyDrive);
    }
    let mut out = [0.0_f64; 12];
    for i in 0..12 {
        let u = drive[i % drive.len()];
        let forcing = 0.015 * (((step + 1) as f64) * ((i + 1) as f64) * 0.173_205_080_756_887_73).sin();
        out[i] = (0.86 * state[i] + 0.14 * u + forcing).tanh();
    }
    Ok(out)
}

/// Gaussian state affinity H(x_i, x_j) = exp(-||x_i-x_j||^2 / (2 sigma^2)).
pub fn gaussian_affinity(a: &[f64], b: &[f64], sigma: f64) -> Result<f64, CstError> {
    if sigma <= 0.0 {
        return Err(CstError::NonPositiveSigma);
    }
    if a.len() != b.len() {
        return Err(CstError::LengthMismatch { left: a.len(), right: b.len() });
    }
    let d2: f64 = a.iter().zip(b).map(|(x, y)| (x - y).powi(2)).sum();
    Ok((-d2 / (2.0 * sigma * sigma)).exp())
}

/// Blend ordinary attention and state affinity with a gate in [0, 1].
pub fn mix_attention(standard: f64, state_affinity: f64, gate: f64) -> f64 {
    let g = gate.clamp(0.0, 1.0);
    (1.0 - g) * standard + g * state_affinity
}

/// PHOS reference feed-forward width: floor(d_model * phi).
pub fn phos_ffn_width(d_model: usize) -> usize {
    ((d_model as f64) * PHI).floor() as usize
}

/// One explicit Euler step of the classical Lorenz system.
/// This is a mathematical chaos primitive, not a dark-matter physics claim.
pub fn lorenz_step(state: [f64; 3], dt: f64, sigma: f64, rho: f64, beta: f64) -> [f64; 3] {
    let [x, y, z] = state;
    let dx = sigma * (y - x);
    let dy = x * (rho - z) - y;
    let dz = x * y - beta * z;
    [x + dt * dx, y + dt * dy, z + dt * dz]
}

/// Compact liveness metric for a set of affinity values.
pub fn affinity_spread(values: &[f64]) -> Option<(f64, f64, f64, bool)> {
    let (&first, rest) = values.split_first()?;
    let mut lo = first;
    let mut hi = first;
    for &v in rest {
        lo = lo.min(v);
        hi = hi.max(v);
    }
    let spread = hi - lo;
    Some((lo, hi, spread, spread > 1e-6))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn phi_width_matches_definition() {
        assert_eq!(phos_ffn_width(1000), 1618);
    }

    #[test]
    fn affinity_identity_is_one() {
        let a = [0.1, 0.2, 0.3];
        let h = gaussian_affinity(&a, &a, 0.75).unwrap();
        assert!((h - 1.0).abs() < 1e-12);
    }

    #[test]
    fn dyn12_is_finite() {
        let s = [0.0; 12];
        let out = update_dyn12(&s, &[0.2, -0.1], 0).unwrap();
        assert!(out.iter().all(|x| x.is_finite()));
        assert!(out.iter().any(|x| x.abs() > 0.0));
    }

    #[test]
    fn lorenz_moves() {
        let next = lorenz_step([1.0, 1.0, 1.0], 0.01, 10.0, 28.0, 8.0 / 3.0);
        assert_ne!(next, [1.0, 1.0, 1.0]);
    }
}
