import js from "@eslint/js"
import tseslint from "typescript-eslint"
import reactHooks from "eslint-plugin-react-hooks"

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    ignores: [
      "dist/**",
      "out/**",
      ".next/**",
      "node_modules/**",
      "src-tauri/**",
      "scripts/**",
      "src/routeTree.gen.ts",
      "*.d.ts",
    ],
  },
  {
    files: ["src/**/*.{ts,tsx,js,jsx,mjs}"],
    plugins: {
      "react-hooks": reactHooks,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "@typescript-eslint/no-unused-vars": "off",
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/ban-ts-comment": "off",
      "@typescript-eslint/no-unused-expressions": "off",
      "no-unused-vars": "off",
      "no-empty": "off",
      "no-control-regex": "off",
      "no-undef": "off",
      "no-useless-assignment": "off",
      "prefer-const": "off",
      "react-hooks/set-state-in-effect": "warn",
    },
  },
)