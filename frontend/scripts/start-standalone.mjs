import { cpSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const standaloneDirectory = resolve(".next/standalone");
cpSync(resolve(".next/static"), resolve(standaloneDirectory, ".next/static"), {
  recursive: true,
});
process.chdir(standaloneDirectory);
await import(pathToFileURL(resolve(standaloneDirectory, "server.js")).href);
