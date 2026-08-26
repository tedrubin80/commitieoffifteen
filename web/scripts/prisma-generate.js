#!/usr/bin/env node
/** Ensure DATABASE_URL exists for `prisma generate` when Vercel only injects POSTGRES_*. */
if (!process.env.DATABASE_URL) {
  process.env.DATABASE_URL =
    process.env.POSTGRES_PRISMA_URL ||
    process.env.POSTGRES_URL ||
    "postgresql://prisma:prisma@127.0.0.1:5432/prisma?schema=public";
}
require("child_process").execSync("npx prisma generate", {
  stdio: "inherit",
  env: process.env,
});
