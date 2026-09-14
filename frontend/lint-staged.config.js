module.exports = {
  '*.{ts,tsx}': [
    () => 'tsc --noEmit',
    'eslint --fix',
    'prettier --write',
  ],
  '*.{json,md,css}': [
    'prettier --write',
  ],
};
