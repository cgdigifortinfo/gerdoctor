const { spawnSync } = require('child_process');
const path = require('path');
const { shards } = require('../mutation-shards.json');

const root = path.resolve(__dirname, '..');
const check = spawnSync(process.execPath, ['scripts/check-mutation-shards.cjs'], { cwd: root, stdio: 'inherit' });
if (check.status !== 0) process.exit(check.status || 1);

for (const shard of shards) {
  console.log(`\n=== ${shard} ===`);
  const result = spawnSync('npx', ['stryker', 'run', shard], { cwd: root, stdio: 'inherit', shell: process.platform === 'win32' });
  if (result.status !== 0) process.exit(result.status || 1);
}
console.log(`\nAlle ${shards.length} Mutation-Shards erfolgreich.`);
