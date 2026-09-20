import { isOwner, ownerConfigured, bridgeConfigured } from '@/lib/security';
import Studio from '@/components/studio';
export const dynamic='force-dynamic';
export default async function Workspace(){
  const [owner,configured,bridge] = await Promise.all([isOwner(),Promise.resolve(ownerConfigured()),Promise.resolve(bridgeConfigured())]);
  return <Studio initialOwner={owner} configured={configured} initialBridge={owner&&bridge}/>;
}