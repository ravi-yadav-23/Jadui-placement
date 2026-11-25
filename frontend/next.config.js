/** @type {import('next').NextConfig} */
const nextConfig = {
  // Old routes from the previous version of the app.
  async redirects() {
    return [
      { source: '/dashboard/tasks', destination: '/dashboard/planner', permanent: true },
      { source: '/dashboard/progress', destination: '/dashboard/planner?tab=progress', permanent: true },
      { source: '/dashboard/chat', destination: '/dashboard/coach', permanent: true },
      { source: '/admin/:path*', destination: '/dashboard', permanent: true },
    ]
  },
}

module.exports = nextConfig
