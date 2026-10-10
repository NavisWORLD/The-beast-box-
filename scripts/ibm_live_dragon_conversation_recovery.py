"""One deliberate recovery job after a verified no-QPU UI conversation preflight.

Keeps the original completed hardware attempt and uses its own stable tag.
Retries recover this tag; they do not submit another quantum job.
"""
import ibm_live_dragon_conversation as probe

probe.OUT=probe.ROOT/'_zeref_live_production_recovery_20261010'
probe.TAG='navisworld-zeref-production-chat-recovery-20261010-onejob-v2'

if __name__=='__main__':
    try:
        probe.main()
    except Exception as error:
        probe.record('failure.json',{'utc':probe.stamp(),'type':type(error).__name__,'credential_recorded':False})
        print('LIVE_PRODUCTION_RECOVERY_FAILURE='+type(error).__name__,flush=True)
        raise SystemExit(1)
