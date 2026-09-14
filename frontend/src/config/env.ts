import { z } from 'zod';

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  NEXT_PUBLIC_API_URL: z.string().url().default('http://localhost:8000/api'),
});

const parseEnv = () => {
  const isBrowser = typeof window !== 'undefined';
  const rawEnv = {
    NODE_ENV: process.env.NODE_ENV || (import.meta as any).env?.MODE,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api',
  };

  const parsed = envSchema.safeParse(rawEnv);
  if (!parsed.success) {
    console.error('❌ Invalid environment variables:', parsed.error.flatten().fieldErrors);
    if (!isBrowser) {
      throw new Error('Invalid environment variables. Check .env');
    }
  }
  return parsed.success ? parsed.data : (rawEnv as any);
};

export const env = parseEnv();
