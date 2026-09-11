import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./style.css";

document.documentElement.classList.toggle(
  "compact",
  localStorage.getItem("compactMode") === "true",
);
document.documentElement.classList.toggle(
  "high-contrast",
  localStorage.getItem("highContrastMode") === "true",
);

createApp(App).use(router).mount("#app");
