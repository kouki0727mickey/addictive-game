module.exports = [
  {
    files: ['js/**/*.js', 'tests/**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'script',
      globals: {
        window: 'readonly', document: 'readonly', self: 'readonly', module: 'writable', require: 'readonly',
        performance: 'readonly', requestAnimationFrame: 'readonly', setTimeout: 'readonly', clearTimeout: 'readonly',
        localStorage: 'readonly', navigator: 'readonly', process: 'readonly', __dirname: 'readonly', console: 'readonly',
      },
    },
    rules: {
      'no-unused-vars': ['error', { args: 'none', caughtErrors: 'none' }],
      'no-undef': 'error',
      eqeqeq: 'error',
      'prefer-const': 'error',
    },
  },
];
