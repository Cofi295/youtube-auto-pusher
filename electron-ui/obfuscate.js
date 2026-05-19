/**
 * obfuscate.js — Mã hóa JavaScript trước khi build Electron app
 * Dùng javascript-obfuscator để bảo vệ source code
 */
const fs = require('fs');
const path = require('path');
const JavaScriptObfuscator = require('javascript-obfuscator');

const RENDERER_DIR = path.join(__dirname, 'renderer');
const OUTPUT_DIR = path.join(__dirname, 'renderer');

const config = {
  compact: true,
  controlFlowFlattening: false,
  deadCodeInjection: false,
  debugProtection: false,
  debugProtectionInterval: 0,
  disableConsoleOutput: false,
  identifierNamesGenerator: 'mangled',
  log: false,
  numbersToExpressions: false,
  renameGlobals: false,
  selfDefending: false,
  simplify: true,
  splitStrings: false,
  stringArray: true,
  stringArrayCallsTransform: false,
  stringArrayEncoding: [],
  stringArrayIndexShift: true,
  stringArrayRotate: true,
  stringArrayShuffle: true,
  stringArrayWrappersCount: 1,
  stringArrayWrappersChainedCalls: false,
  stringArrayThreshold: 0.2,
  transformObjectKeys: false,
  unicodeEscapeSequence: false,
};

// Light config cho preload.js (tránh break electron IPC)
const lightConfig = {
  compact: true,
  controlFlowFlattening: true,
  controlFlowFlatteningThreshold: 0.5,
  deadCodeInjection: false,
  debugProtection: false,
  disableConsoleOutput: false,
  identifierNamesGenerator: 'hexadecimal',
  renameGlobals: false,
  selfDefending: false,
  splitStrings: true,
  stringArray: true,
  stringArrayEncoding: ['base64'],
  stringArrayThreshold: 0.5,
  transformObjectKeys: false,
};

function obfuscateFile(fileName, cfg) {
  const filePath = path.join(RENDERER_DIR, fileName);
  if (!fs.existsSync(filePath)) {
    console.log(`  SKIP: ${fileName} (not found)`);
    return;
  }

  const code = fs.readFileSync(filePath, 'utf8');
  const result = JavaScriptObfuscator.obfuscate(code, cfg);
  const obfuscated = result.getObfuscatedCode();

  // Backup original
  const backupPath = filePath + '.bak';
  fs.writeFileSync(backupPath, code);

  // Write obfuscated
  fs.writeFileSync(filePath, obfuscated);

  const origSize = (Buffer.byteLength(code) / 1024).toFixed(1);
  const newSize = (Buffer.byteLength(obfuscated) / 1024).toFixed(1);
  console.log(`  ✓ ${fileName}: ${origSize} KB → ${newSize} KB`);
}

function restore() {
  const files = fs.readdirSync(RENDERER_DIR).filter(f => f.endsWith('.bak'));
  files.forEach(f => {
    const orig = f.replace('.bak', '');
    fs.copyFileSync(path.join(RENDERER_DIR, f), path.join(RENDERER_DIR, orig));
    fs.unlinkSync(path.join(RENDERER_DIR, f));
  });
  console.log(`Restored ${files.length} files from backup`);
}

const cmd = process.argv[2] || 'obfuscate';

if (cmd === 'restore') {
  restore();
} else {
  console.log('🔒 Obfuscating renderer JS...');
  obfuscateFile('app.js', config);
  console.log('🔒 Obfuscating preload (light)...');
  // preload is in parent dir
  const preloadPath = path.join(__dirname, 'preload.js');
  if (fs.existsSync(preloadPath)) {
    const code = fs.readFileSync(preloadPath, 'utf8');
    const result = JavaScriptObfuscator.obfuscate(code, lightConfig);
    fs.writeFileSync(preloadPath + '.bak', code);
    fs.writeFileSync(preloadPath, result.getObfuscatedCode());
    console.log('  ✓ preload.js');
  }
  console.log('Done ✅');
}
