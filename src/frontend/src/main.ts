import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./style.css";
import "./consistency.css";
import "./styles/ui.css";

document.documentElement.classList.toggle(
  "compact",
  localStorage.getItem("compactMode") === "true",
);
document.documentElement.classList.toggle(
  "high-contrast",
  localStorage.getItem("highContrastMode") === "true",
);

createApp(App).use(router).mount("#app");
