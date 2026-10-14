import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";
import { defineConfig, globalIgnores } from "eslint/config";

export default defineConfig([
  globalIgnores(["dist", "test-results", "playwright-report"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
  },
  {
    files: ["src/features/**/model/**/*.ts"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "react",
              message:
                "O modelo deve conter regras e tipos independentes de React.",
            },
          ],
          patterns: [
            {
              group: [
                "@/app/**",
                "**/components/**",
                "**/pages/**",
                "**/hooks/**",
                "**/api/**",
              ],
              message: "O modelo não deve depender de interface ou transporte.",
            },
          ],
        },
      ],
    },
  },
  {
    files: ["src/features/**/api/**/*.ts"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "react",
              message: "A comunicação deve ser independente de React.",
            },
          ],
          patterns: [
            {
              group: [
                "@/app/**",
                "**/components/**",
                "**/pages/**",
                "**/hooks/**",
              ],
              message: "O transporte não deve importar a interface.",
            },
          ],
        },
      ],
    },
  },
  {
    files: ["src/shared/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: [
                "@/features/**",
                "@/app/**",
                "**/features/**",
                "**/app/**",
              ],
              message:
                "Módulos compartilhados não devem depender das funcionalidades.",
            },
          ],
        },
      ],
    },
  },
  {
    files: ["src/features/**/{components,pages}/**/*.tsx"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["../api/**", "**/api/**"],
              message:
                "Componentes recebem dados por propriedades; acesso ao transporte fica nos hooks.",
            },
          ],
        },
      ],
    },
  },
]);
