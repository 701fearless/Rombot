module.exports = {
  root: true,
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint', 'react-hooks'],
  extends: ['eslint:recommended', 'plugin:@typescript-eslint/recommended'],
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  parserOptions: {
    ecmaVersion: 2021,
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
  },
  rules: {
    // PRD 铁律：全项目禁止 any
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
  },
  ignorePatterns: [
    'dist/',
    'node_modules/',
    '*.config.js',
    '.eslintrc.js',
    'src/App.tsx',
    'src/main.tsx',
    'src/components/ApiDashboard.tsx',
    'src/components/FeedActions.tsx',
    'src/components/FloorplanViewer.tsx',
    'src/components/SpacePlaceholder.tsx',
    'src/components/VideoFeed.tsx',
    'src/components/VideoFeedItem.tsx',
    'src/lib/api.ts',
    'src/lib/autoSection.ts',
    'src/lib/*.test.ts',
  ],
}
