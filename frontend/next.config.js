/** @type {import('next').NextConfig} */
const nextConfig = {
  // 'standalone' output is for self-hosted Docker deployments (produces
  // a server.js you run yourself) — it's incompatible with Vercel's own
  // serverless build output and causes every route to 404. Now that the
  // frontend only deploys to Vercel, this must stay unset.
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
