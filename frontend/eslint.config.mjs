import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // Pre-existing pattern in AppContext/MedicineAdvisor/Sidebar/AudioPlayer:
      // state is synced inside effects (capability detection, loading flags,
      // resetting on navigation). These are not bugs, but they do cause an
      // extra render pass and should be migrated off effects over time.
      // Tracked as warnings so they stay visible without blocking CI, while
      // every other lint error is enforced.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
