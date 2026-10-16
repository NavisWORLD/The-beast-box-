import { isOwner, ownerConfigured, bridgeConfigured } from '@/lib/security';
import { workshopAccess } from '@/lib/accounts';
import Studio from '@/components/studio';
import WorkshopGate from '@/components/workshop-gate';
export const dynamic='force-dynamic';
export default async function Workspace(){
  const [owner,configured,bridge,access] = await Promise.all([isOwner(),Promise.resolve(ownerConfigured()),Promise.resolve(bridgeConfigured()),workshopAccess()]);
  if(!access.allowed) return <WorkshopGate reason={access.reason} configured={configured}/>;
  return <Studio initialOwner={owner} configured={configured} initialBridge={owner&&bridge}/>;
}
