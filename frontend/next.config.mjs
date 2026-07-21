/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // The frontend is purely a consumer of the FastAPI backend; allow images
  // from any host because source adapters return upstream image URLs.
  images: {
    remotePatterns: [{ protocol: "https", hostname: "**" }],
  },
  // Useful when running behind a reverse proxy or in a container.
  experimental: {
    typedRoutes: false,
  },
};

export default nextConfig;
