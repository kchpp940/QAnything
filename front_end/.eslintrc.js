/*
 * @Author: 祝占朋 wb.zhuzhanpeng01@mesg.corp.netease.com
 * @Date: 2024-01-09 15:28:56
 * @LastEditors: 祝占朋 wb.zhuzhanpeng01@mesg.corp.netease.com
 * @LastEditTime: 2024-01-11 10:48:36
 * @FilePath: /QAnything/front_end/.eslintrc.js
 * @Description:
 */

module.exports = {
  env: {
    node: true,
  },
  parser: 'vue-eslint-parser',
  parserOptions: {
    parser: '@typescript-eslint/parser',
    sourceType: 'module',
  },
  settings: {
    'import/resolver': {
      typescript: {
        alwaysTryTypes: true,
        project: './tsconfig.json',
      },
    },
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
    'prettier',
    'plugin:prettier/recommended',
    './.eslintrc-auto-import',
  ],
  plugins: ['prettier', '@typescript-eslint', 'import'],
  rules: {
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    semi: 'error',
    'max-len': 'off',
    'no-tabs': 'off',
    'linebreak-style': [0, 'error', 'windows'],
    'no-underscore-dangle': ['off', 'always'],
    'no-unused-vars': 'off',
    '@typescript-eslint/no-unused-vars': ['error'],
    'vue/no-v-html': 'off',
    'no-restricted-imports': [
      'error',
      {
        paths: [
          {
            name: '@/services/urlConfig',
            message: '请使用 @/services/api 中的 api.xxx 替代，禁止直接使用 urlResquest',
          },
          {
            name: '@/interface',
            message: '请使用 @/services/api 中的类型定义，禁止直接导入旧 interface.ts',
          },
        ],
        patterns: [
          {
            group: ['@/services/urlConfig', '@/interface'],
            message: '请使用 @/services/api 中的替代方案，禁止直接导入',
          },
        ],
      },
    ],
  },
  overrides: [
    {
      files: ['src/services/api/**/*.ts'],
      rules: {
        'no-restricted-imports': 'off',
      },
    },
  ],
};
