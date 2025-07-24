/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000/api';
    const agentsUrl = process.env.NEXT_PUBLIC_AGENTS_URL || '';
    const rewrites = [
      {
        source: '/api/:path*',
        destination: apiUrl + '/api/:path*',
      },
      {
        source: '/admin/:path*',
        destination: apiUrl + '/admin/:path*',
      },
    ];
    
    if (agentsUrl) {
      rewrites.push({
        source: '/ws/:path*',
        destination: 'http://' + agentsUrl + '/ws/:path*',
      });
    }
    
    return rewrites;
  },
};

module.exports = nextConfig;