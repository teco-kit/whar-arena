import svelte from "@astrojs/svelte";
import { defineConfig } from "astro/config";

const base = process.env.PUBLIC_BASE_PATH ?? "/";
const site = process.env.PUBLIC_SITE_URL ?? "http://127.0.0.1:4321";

export default defineConfig({
  base,
  integrations: [svelte()],
  output: "static",
  site,
});
