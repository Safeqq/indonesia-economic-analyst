/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  deploymentId: process.env.DEPLOYMENT_VERSION,
  experimental: {
    // Node 26 dapat menutup pipe CLI tsc sebelum stdout selesai dibaca Next.
    // Compiler API menjalankan pemeriksaan TypeScript yang sama tanpa subprocess.
    useTypeScriptCli: false,
  },
  async rewrites() {
    const apiBaseUrl = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

    return [
      {
        source: "/backend/:path*",
        destination: `${apiBaseUrl}/:path*`,
      },
    ];
  },
};
module.exports = nextConfig;
