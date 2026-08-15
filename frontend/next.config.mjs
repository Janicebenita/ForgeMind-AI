/** @type {import('next').NextConfig} */
const nextConfig = {
  // Azure Container Apps runs the Linux standalone bundle. On Windows,
  // Next's pnpm trace copy requires symlink privileges that are often absent.
  output: process.platform === "win32" ? undefined : "standalone"
};

export default nextConfig;
