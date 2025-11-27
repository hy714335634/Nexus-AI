/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // Disable typedRoutes to avoid build errors with dynamic routes
  // experimental: {
  //   typedRoutes: true
  // }
  // Disable static optimization for pages with useSearchParams
  // This allows client components with useSearchParams to build without Suspense
  generateBuildId: async () => {
    // Use timestamp to ensure dynamic builds
    return 'build-' + Date.now().toString()
  },
  experimental: {
    // Disable the Suspense requirement for useSearchParams in client components
    missingSuspenseWithCSRBailout: false
  }
};

export default nextConfig;
