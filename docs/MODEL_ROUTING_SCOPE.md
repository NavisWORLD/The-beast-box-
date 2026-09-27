# Finisher F — explicit host-selected model capability routing

The optional `beastbox.model_router.ModelRouter` operates on ONE existing
`DurableRuntime` and an owner-configured list of
`ModelSlot(key, provider, frozenset({declared capabilities}))`.
The embedding host must authenticate the owner independently and provide
`authorize_by_host(slot, capability)`: model text is not authentication.
Unlisted providers, undeclared capabilities and unapproved selections fail
closed; a provider exception never triggers an implicit fallback.

Approved `activate(...)` calls inspect the unchanged product
`system_id`, checkpoint digest, sequence, memory digest and state digest
before and after switching, revoke prior runtime tool grants and invalidate
older single-use maintenance permissions. The host receives a bounded
configured-slot receipt; the receipt explicitly says
`weight_hash_attested: false`. A new provider does not own or inherit
memory, software state or authority. Once another component swaps the
provider directly, any old router selection becomes invalid.

The offline [A→B→A acceptance test](../tests/test_finisher_model_router.py)
uses multiple separately configured **deterministic reference providers**
over the same runtime. This is a genuine integration test of the replaceable
software route and owner boundary; it is **not** new A/B trained-model
inference or proof that one model is more capable, no weights are attested,
and the historical published A→B→A experiment is not altered.

Before completing broad Phase F, require independently sourced, version-
and hash-pinned *real* Model A and Model B weights, actual inference on
supported CPU/GPU and provider permissions, capability-specific held-out
evaluation, measured A→B→A over the full durable substrate and tool
revocation tests. Optional cloud access or model downloads must be
separately provisioned, license-reviewed and cost-authorized. Do not infer
performance or identity from configured provider labels.
