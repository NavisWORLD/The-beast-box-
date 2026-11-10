import type { NextConfig } from 'next';
import path from 'node:path';
const repositoryRoot=path.resolve(__dirname,'../..');
const nextConfig: NextConfig = { poweredByHeader: false, reactStrictMode: true,
 // Stage 6. The five flags default on in the Next bundle. ?oneUniverse=off still clears them.
 env:{NEXT_PUBLIC_ONE_UNIVERSE:process.env.NEXT_PUBLIC_ONE_UNIVERSE||'state,light,population,tick,cameras'},
 turbopack:{root:repositoryRoot},outputFileTracingRoot:repositoryRoot,
 outputFileTracingIncludes:{'/api/cosmos/private/beasts':['./public/spark/runs.json','./public/spark/ibm-*.json','./public/spark/user-seeds-*.json','./public/spark/azure-*.json']},
 async redirects() { return [{ source: '/guest', destination: '/beast-cage/guest', permanent: false }]; },
 async rewrites() { return [{ source: '/spark', destination: '/spark/index.html' }]; } };
export default nextConfig;
