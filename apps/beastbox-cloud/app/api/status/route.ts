import { bridgeConfigured, isOwner, ownerConfigured, safeJson } from '@/lib/security';
export const dynamic = 'force-dynamic';
export async function GET() {
  const owner=await isOwner();
  return safeJson(200,{ application:'BEAST BOX // COSMIC CHAOS', owner, ownerConfigured:ownerConfigured(),
    bridgeConfigured:owner && bridgeConfigured(),
    inference:owner && bridgeConfigured() ? 'BRIDGE_CONFIGURED_NOT_ATTESTED' : 'UNAVAILABLE',
    attachments:'LOCAL_STAGING_ONLY', persistence:owner && bridgeConfigured() ? 'BRIDGE_CONFIGURED_NOT_ATTESTED' : 'UNAVAILABLE',
    surface:'PRIVATE_PREVIEW', backendKind:'SEPARATE_DURABLE_RUNTIME_REQUIRED' });
}
