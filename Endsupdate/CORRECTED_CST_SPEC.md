# Corrected CST research specification (hypothesis)

For entity `i`: mass `m_i [kg]`, twelve *simulation velocity components* `v_ik [m/s]`, three-dimensional measured/synthetic position `x_i [m]`, Lyapunov exponent `λ_i [s^-1]`, and nonnegative information count `I_i [bits]`. The twelve velocity components are a simulation convention; they do **not** establish physical 12D space. Explicit scales: `τ [s]`, `r0 [m]`, softening `ε [m]`, `Eref [J]`, `T [K]`. `β, η, φ` are dimensionless; β and η are free research coefficients, not fitted laws; G, kB, c are established physics constants where used.

Define `K_i = 0.5 m_i Σ_k v_ik² [J]`; `d_ij = sqrt(||x_i-x_j||² + ε²) [m]`, `w_ij = exp(-||x_i-x_j||/r0)`, `f(I) = I/(1+I)`. The last is an explicitly chosen bounded computational proxy, **not** black-hole entropy.

```text
K*_i = (φ + τ λ_i) K_i                         [J]
U_i  = -Σ_{j≠i} G m_i m_j / d_ij               [J]
C_i  = β Σ_{j≠i} w_ij G m_i m_j / d_ij         [J]
Q_i  = -η kB T Σ_{j≠i} f(I_i) f(I_j) w_ij (r0/d_ij)  [J]
score_i = (K*_i + U_i + C_i + Q_i) / Eref       [dimensionless]
```

All additions now have units J. `η = 0` ablation removes Q. The classical control uses `(K+U)/Eref`. The shuffled control rotates the `I_i` assignments. The literal historical equation is exposed **only** by `legacy_raw` and is never relabeled as this score. It may yield a result with formally inconsistent units.

The candidate is phenomenological: the information interaction has no established physical derivation or observed energy transfer, and the free coefficients, positive softening, 12 simulation velocity channels, fixed temperature, scales and normalization are experimental assumptions. It does not imply a conserved Hamiltonian, quantum entanglement, a new force or a performance advantage. The default `Eref=10^41 J`, `r0=10^11 m`, `ε=10^7 m`, `τ=1 s`, `β=η=1` are **illustrative synthetic settings**, not data-fitted optimum values. They should not be carried into model state or security policy.
