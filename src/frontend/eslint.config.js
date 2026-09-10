import eslint from "@eslint/js";
import eslintPluginVue from "eslint-plugin-vue";
import tseslint from "typescript-eslint";
import globals from "globals";

export default tseslint.config(
  {
    ignores: ["dist/", "node_modules/"],
  },

  eslint.configs.recommended,

  ...tseslint.configs.recommended,

  ...eslintPluginVue.configs["flat/essential"],

  {
    files: ["**/*.vue"],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
      },
      globals: globals.browser,
    },
  },

  {
    files: ["**/*.{js,mjs,cjs,ts}"],
    languageOptions: {
      globals: globals.browser,
    },
  },

  {
    // top-level route views, not reusable components — named after the
    // page they render (Login, Settings, Inbox...), so a single word is
    // the natural name here, unlike a component dropped into arbitrary
    // markup where a multi-word name avoids colliding with a native tag
    files: ["src/views/**/*.vue"],
    rules: {
      "vue/multi-word-component-names": "off",
    },
  },
);
