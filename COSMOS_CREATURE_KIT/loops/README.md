# Creature loops

The common loop is:

`provider -> sanitized BridgeReceipt -> freshness validation -> Spark/Trinity state -> 12D -> 42D -> balanced 54D -> runtime consumer -> evidence`

`ibm_loop.py`, `azure_loop.py`, and `hybrid_loop.py` are small examples that keep provider acquisition separate from state composition.
