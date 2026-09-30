# CST12 Physics Probe 003 Amendment 2

Date: 2026-08-24
Status: pre-hardware implementation correction

## Issue

The implementation plan's synthetic-shot example used `P(1)=(1+m)/2` and reconstructed `m=2*P(1)-1`. That is the negative of the actual Pauli-Z measurement convention used by the Hadamard-test circuits.

## Frozen convention

For either ancilla basis, if the exact expectation is `m` then

`m = P(0) - P(1)`

and therefore

`P(1) = (1 - m) / 2`.

A sampled expectation is reconstructed as

`m_hat = (n0 - n1) / shots = 1 - 2*n1/shots`.

The same convention is used for synthetic shot noise and real IBM counts. The complex measured overlap is

`Z_measured = X_hat + i*Y_hat`.

This correction is sealed before Probe 003 IBM hardware and does not change the hypothesis, thresholds, circuit topology, or two-sided decision rule.
