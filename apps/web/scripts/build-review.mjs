import { execFileSync } from "node:child_process";
import { cp, mkdir, readdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = fileURLToPath(new URL("../", import.meta.url));
const output = path.resolve(webRoot, "../../docs");
const buildOutput = path.join(webRoot, "dist");

// Build without an identifying hostname or a deployment-specific URL prefix.
execFileSync(process.platform === "win32" ? "npm.cmd" : "npm", ["run", "build"], {
  cwd: webRoot,
  stdio: "inherit",
  env: {
    ...process.env,
    ASTRO_TELEMETRY_DISABLED: "1",
    PUBLIC_BASE_PATH: "/",
    PUBLIC_SITE_URL: "https://example.invalid",
  },
});

// This directory contains generated review pages only.
await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
await cp(buildOutput, output, { recursive: true });

async function makePortable(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      await makePortable(filename);
    } else if (entry.name.endsWith(".html")) {
      const original = await readFile(filename, "utf8");
      const references = [...original.matchAll(/\b(?:href|src|component-url|renderer-url)="(\/(?!\/)[^"]*)"/g)];
      const replacements = new Map();
      for (const [, url] of references) {
        const { pathname, search, hash } = new URL(url, "https://example.invalid");
        const target = path.join(output, decodeURIComponent(pathname));
        const targetInfo = await stat(target);
        let relative = path.relative(path.dirname(filename), target).split(path.sep).join("/");
        if (!relative.startsWith(".")) relative = `./${relative}`;
        if (targetInfo.isDirectory() && !relative.endsWith("/")) relative += "/";
        replacements.set(url, relative + search + hash);
      }
      const portable = original.replace(
        /\b(href|src|component-url|renderer-url)="(\/(?!\/)[^"]*)"/g,
        (_, attribute, url) => `${attribute}="${replacements.get(url)}"`,
      );
      await writeFile(filename, portable);
    }
  }
}

await makePortable(output);
// Preserve Astro's _astro directory when GitHub publishes from a branch.
await writeFile(path.join(output, ".nojekyll"), "");
console.log("Review website generated in docs/ with relative links.");
