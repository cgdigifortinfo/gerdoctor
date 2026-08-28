const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'mutation-shards.json'), 'utf8'));

function sourceFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name);
    return entry.isDirectory() ? sourceFiles(full) : [full];
  });
}

function patternRegex(pattern) {
  const withoutRange = pattern.replace(/:\d.*$/, '');
  let expression = withoutRange.replace(/[.+^$()|[\]\\]/g, '\\$&');
  expression = expression.replace(/\{([^}]+)\}/g, (_, values) => `(${values.split(',').join('|')})`);
  expression = expression
    .replace(/\*\*\//g, '§DIR§')
    .replace(/\*\*/g, '§ANY§')
    .replace(/\*/g, '[^/]*')
    .replace(/§DIR§/g, '(?:.*/)?')
    .replace(/§ANY§/g, '.*');
  return new RegExp(`^${expression}$`);
}

const sources = sourceFiles(path.join(root, 'src'))
  .map((file) => path.relative(root, file).split(path.sep).join('/'))
  .filter((file) => /\.(js|jsx)$/.test(file) && !/\.test\.(js|jsx)$/.test(file) && !file.includes('/__snapshots__/'))
  .sort();
const owners = new Map(sources.map((file) => [file, []]));

for (const shard of manifest.shards) {
  const configPath = path.join(root, shard);
  if (!fs.existsSync(configPath)) throw new Error(`Fehlende Shard-Konfiguration: ${shard}`);
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  const patterns = (config.mutate || [])
    .map((entry) => typeof entry === 'string' ? entry : entry.included)
    .filter((pattern) => pattern && !pattern.startsWith('!'))
    .map(patternRegex);
  for (const source of sources) if (patterns.some((pattern) => pattern.test(source))) owners.get(source).push(shard);
}

const invalid = [...owners].filter(([, assigned]) => assigned.length !== 1);
if (invalid.length) {
  for (const [source, assigned] of invalid) console.error(`${source}: ${assigned.length ? assigned.join(', ') : 'nicht zugeordnet'}`);
  process.exit(1);
}
console.log(`Mutation-Manifest vollständig: ${sources.length} Quelldateien, jeweils exakt ein Shard.`);
