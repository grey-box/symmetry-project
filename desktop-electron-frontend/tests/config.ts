import { readFileSync } from 'fs';
import { resolve } from 'path';

// ponytail: __dirname over import.meta.url — this file loads as CJS and import.meta.url breaks
const _dir = __dirname;

let _cfg: Record<string, string>;

function loadConfig(): Record<string, string> {
  if (_cfg) return _cfg;

  let parsed: Record<string, string>;
  try {
    parsed = JSON.parse(readFileSync(resolve(_dir, 'config.json'), 'utf-8'));
  } catch {
    parsed = JSON.parse(readFileSync(resolve(_dir, 'config.default.json'), 'utf-8'));
  }

  // Validate required keys
  const required = ['src_url', 'src_article', 'tgt_article', 'target_lang', 'api_base'];
  for (const key of required) {
    if (!parsed[key]) {
      console.warn(`[test-config] Missing "${key}" in config, check config.json / config.default.json`);
    }
  }

  _cfg = parsed;
  return _cfg;
}

export const config = loadConfig();
