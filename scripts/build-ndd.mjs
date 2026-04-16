// Bundles the @minbzk/storybook web components + styles + fonts
// from node_modules into wies/core/static/vendor/ndd/.
//
// The npm package ships ESM modules with bare specifiers (`from "lit"`),
// so we use esbuild to bundle them into a single browser-loadable file
// that registers all custom elements (ndd-button, ndd-sheet, etc.).
//
// Run via: just build-ndd  (or: npm run build-ndd)

import {
  readFileSync,
  writeFileSync,
  mkdirSync,
  rmSync,
  copyFileSync,
  existsSync,
  readdirSync,
} from "node:fs";
import { dirname, join, resolve, relative, basename } from "node:path";
import { fileURLToPath } from "node:url";
import * as esbuild from "esbuild";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..");
const outDir = join(repoRoot, "wies/core/static/vendor/ndd");
const assetsDir = join(outDir, "assets");

// 1. Locate package
const pkgRoot = resolve(repoRoot, "node_modules/@minbzk/storybook");
const pkgJsonPath = join(pkgRoot, "package.json");
if (!existsSync(pkgJsonPath)) {
  throw new Error(`@minbzk/storybook not installed. Run: npm install`);
}
const pkg = JSON.parse(readFileSync(pkgJsonPath, "utf8"));

// Entry file that re-exports all components — esbuild zal de side-effects
// (customElements.define) van elk geïmporteerd component meenemen.
const jsEntry = join(pkgRoot, "dist/components/index.js");
const cssSrc = join(pkgRoot, "dist/css/settings.css");
const richTextCssSrc = join(pkgRoot, "dist/css/ndd-rich-text.css");
const fontsDir = join(pkgRoot, "dist/fonts");

for (const f of [jsEntry, cssSrc, richTextCssSrc, fontsDir]) {
  if (!existsSync(f))
    throw new Error(`Missing expected file: ${relative(pkgRoot, f)}`);
}

console.log(`@minbzk/storybook ${pkg.version}`);
console.log(`  bundling: ${relative(pkgRoot, jsEntry)}`);

// 2. Wipe + recreate output
rmSync(outDir, { recursive: true, force: true });
mkdirSync(assetsDir, { recursive: true });

// 3. Bundle JS via esbuild — IIFE format zodat het direct in browser werkt
//    zonder type=module imports (geen bare-specifier resolutie nodig).
await esbuild.build({
  entryPoints: [jsEntry],
  bundle: true,
  format: "iife",
  target: "es2022",
  minify: false, // dev: leesbaar; flip naar true voor prod
  outfile: join(outDir, "ndd.bundle.js"),
  loader: { ".css": "text" }, // lit imports CSS as string
  logLevel: "warning",
});

// 4. Copy fonts to assets/
for (const fname of readdirSync(fontsDir)) {
  copyFileSync(join(fontsDir, fname), join(assetsDir, fname));
}

// 5. Concatenate CSS files, rewriting font url(../fonts/...) to assets/...
function loadAndRewrite(src) {
  const css = readFileSync(src, "utf8");
  return css.replace(
    /url\(\s*(['"]?)([^'")]+)\1\s*\)/g,
    (match, quote, ref) => {
      if (/^(data:|https?:|\/)/.test(ref)) return match;
      const fname = basename(ref.split("?")[0].split("#")[0]);
      if (existsSync(join(assetsDir, fname))) {
        return `url(${quote}assets/${fname}${quote})`;
      }
      console.warn(
        `  warn: unresolved url() reference '${ref}' in ${relative(pkgRoot, src)}`,
      );
      return match;
    },
  );
}

const combined = [
  `/* @minbzk/storybook ${pkg.version} — settings.css */`,
  loadAndRewrite(cssSrc),
  `/* @minbzk/storybook ${pkg.version} — ndd-rich-text.css */`,
  loadAndRewrite(richTextCssSrc),
].join("\n\n");

writeFileSync(join(outDir, "ndd.styles.css"), combined);

// 6. Marker
writeFileSync(
  join(outDir, "VERSION.txt"),
  `@minbzk/storybook ${pkg.version}\nbuilt ${new Date().toISOString()}\n`,
);

console.log(`\nBuilt NDD vendor assets into ${relative(repoRoot, outDir)}`);
