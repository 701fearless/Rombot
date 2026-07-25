import { cp, mkdir } from "node:fs/promises"
import path from "node:path"
import { fileURLToPath } from "node:url"

import { build } from "esbuild"

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const repositoryRoot = path.resolve(frontendRoot, "..")
const distRoot = path.join(frontendRoot, "dist")
const clientRoot = path.join(distRoot, "client")
const serverRoot = path.join(distRoot, "server")

await mkdir(clientRoot, { recursive: true })
await mkdir(serverRoot, { recursive: true })

for (const entry of ["index.html", "assets", "covers"]) {
  await cp(path.join(distRoot, entry), path.join(clientRoot, entry), { recursive: true })
}

const videoTarget = path.join(clientRoot, "sample_data", "videos")
await mkdir(videoTarget, { recursive: true })
for (const videoId of ["2", "3", "4", "6", "7"]) {
  await cp(
    path.join(repositoryRoot, "backend", "sample_data", "videos", `${videoId}.mp4`),
    path.join(videoTarget, `${videoId}.mp4`),
  )
}

await build({
  entryPoints: [path.join(frontendRoot, "worker", "index.ts")],
  outfile: path.join(serverRoot, "index.js"),
  bundle: true,
  format: "esm",
  platform: "browser",
  target: "es2022",
  minify: true,
  legalComments: "none",
})
