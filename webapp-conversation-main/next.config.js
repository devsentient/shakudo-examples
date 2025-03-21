/** @type {import('next').NextConfig} */
const nextConfig = {
  productionBrowserSourceMaps: false, // enable browser source map generation during the production build
  // Configure pageExtensions to include md and mdx
  pageExtensions: ['ts', 'tsx', 'js', 'jsx', 'md', 'mdx'],
  experimental: {
    // appDir: true,
  },
  // fix all before production. Now it slow the develop speed.
  eslint: {
    // Warning: This allows production builds to successfully complete even if
    // your project has ESLint errors.
    ignoreDuringBuilds: true,
  },
  typescript: {
    // https://nextjs.org/docs/api-reference/next.config.js/ignoring-typescript-errors
    ignoreBuildErrors: true,
  },
  env: {
    NEXT_PUBLIC_APP_ID: process.env.APP_ID,
    NEXT_PUBLIC_APP_KEY: process.env.APP_KEY,
    NEXT_PUBLIC_API_URL: process.env.API_URL,
    NEXT_PUBLIC_APP_CHAT_TITLE: process.env.APP_CHAT_TITLE,
    NEXT_PUBLIC_FRONTEND_UI_DOMAIN: process.env.FRONTEND_UI_DOMAIN,
  },
}

module.exports = nextConfig
