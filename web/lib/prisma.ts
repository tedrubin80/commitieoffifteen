import { PrismaClient } from "@prisma/client";

/**
 * Vercel Storage / Prisma / Neon inject different names.
 * Prefer pooled Prisma URL when present.
 */
export function resolveDatabaseUrl(): string | undefined {
  return (
    process.env.DATABASE_URL ||
    process.env.POSTGRES_PRISMA_URL ||
    process.env.PRISMA_DATABASE_URL ||
    process.env.POSTGRES_URL ||
    process.env.DATABASE_URL_UNPOOLED
  );
}

export function databaseEnvKeysPresent(): string[] {
  const keys = [
    "DATABASE_URL",
    "POSTGRES_PRISMA_URL",
    "PRISMA_DATABASE_URL",
    "POSTGRES_URL",
    "POSTGRES_URL_NON_POOLING",
    "DIRECT_URL",
  ];
  return keys.filter((k) => Boolean(process.env[k]));
}

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient | undefined };

function createClient(): PrismaClient {
  const url = resolveDatabaseUrl();
  return new PrismaClient({
    log: process.env.NODE_ENV === "development" ? ["error", "warn"] : ["error"],
    ...(url
      ? {
          datasources: {
            db: { url },
          },
        }
      : {}),
  });
}

export const prisma = globalForPrisma.prisma ?? createClient();

if (process.env.NODE_ENV !== "production") {
  globalForPrisma.prisma = prisma;
}
