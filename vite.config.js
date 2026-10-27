import { defineConfig } from "vite";

export default defineConfig({
  base: "./",

  server: {
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
