import { defineConfig } from "vite";

export default defineConfig({
  base: "./",

  server: {
    fs: {
      // Knowledge JSON is a server-side chatbot asset and must not be served
      // by Vite's development file server.
      deny: ["**/knowledge-base/**"],
    },
    proxy: {
      "/api": {
        target: "https://erp.itgenie.online",
        changeOrigin: true,
        secure: true,
      },
    },
  },

  build: {
    outDir: "dist",
    assetsDir: "assets",
  },
});
