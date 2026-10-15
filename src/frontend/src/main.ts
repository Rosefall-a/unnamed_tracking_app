import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./style.css";
import "./styles/ui.css";
import { applyThemeColors, readCachedThemeColors } from "./state/themeColors";

document.documentElement.classList.toggle(
  "compact",
  localStorage.getItem("compactMode") === "true",
);
document.documentElement.classList.toggle(
  "high-contrast",
  localStorage.getItem("highContrastMode") === "true",
);

// the colours someone has changed, before anything is drawn
applyThemeColors(readCachedThemeColors());

createApp(App).use(router).mount("#app");
