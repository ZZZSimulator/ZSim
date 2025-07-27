import defineConfig from '@antfu/eslint-config'

export default defineConfig({
  ignores: [
    'node_modules',
    'dist',
    'out',
  ],
  stylistic: {
    indent: 2,
    quotes: 'single',
  },
  rules: {
    // 顶层函数允许使用箭头函数
    'antfu/top-level-function': 'off',
    // 断行符号使用 LF
    'style/linebreak-style': ['error', 'unix'],
    // 文件末尾保留空行
    'style/eol-last': 'error',
  },
  jsonc: {
    overrides: {
      // json key 排序
      'jsonc/sort-keys': ['warn', 'asc'],
    },
  },
  typescript: {
    overrides: {
      // 记得清理 console
      'no-console': 'warn',
      // 默认参数必须放在最后
      'default-param-last': 'error',
      // 一般情况下不允许使用 any
      'ts/no-explicit-any': 'warn',
      // 命名规范
      'ts/naming-convention': [
        'error',
        // TS interface 只允许大驼峰
        {
          selector: 'interface',
          format: ['PascalCase'],
          leadingUnderscore: 'forbid',
        },
        // TS Type 只允许大驼峰
        {
          selector: 'typeLike',
          format: ['PascalCase'],
          leadingUnderscore: 'forbid',
        },
        // 变量只允许大小驼峰、全大写下划线、全小写下划线
        {
          selector: 'variable',
          format: ['PascalCase', 'camelCase', 'UPPER_CASE', 'snake_case'],
          leadingUnderscore: 'allow',
          trailingUnderscore: 'allow',
        },
      ],
    },
  },
  vue: {
    overrides: {
      // 组件名称至少由 2 个单词组成
      'vue/multi-word-component-names': 'error',
      // 组件定义名称只允许连字符风格
      'vue/component-definition-name-casing': ['error', 'kebab-case'],
      // 组件属性名称只允许小驼峰风格
      'vue/prop-name-casing': ['error', 'camelCase'],
      // 允许在相同作用域范围从对象获取响应值
      'vue/no-ref-object-reactivity-loss': 'off',
      // 未使用的值必须使用下划线开头
      'vue/no-unused-vars': [
        'error',
        {
          ignorePattern: '^_',
        },
      ],
    },
  },
})
