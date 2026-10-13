import type { NextConfig } from 'next';
import path from 'node:path';
const repositoryRoot=path.resolve(__dirname,'../..');
const nextConfig: NextConfig = { poweredByHeader: false, reactStrictMode: true,
 turbopack:{root:repositoryRoot},outputFileTracingRoot:repositoryRoot,
 outputFileTracingIncludes:{'/api/cosmos/private/beasts':['./public/spark/runs.json','./public/spark/ibm-*.json','./public/spark/user-seeds-*.json','./public/spark/azure-*.json']},
 async rewrites() { return [{ source: '/spark', destination: '/spark/index.html' }]; } };
export default nextConfig;
