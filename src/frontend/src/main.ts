import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./style.css";
import { waitForServer } from "./state/serverStartup";
import { checkAuth } from "./state/auth";
document.documentElement.classList.toggle("compact", localStorage.getItem("compactMode") === "true");
document.documentElement.classList.toggle("high-contrast", localStorage.getItem("highContrastMode") === "true");
// Do not run authentication until the backend is reachable; startup failures are
// a normal container lifecycle state, not a logged-out session.
void waitForServer().then(() => checkAuth()).catch(() => checkAuth());
createApp(App).use(router).mount("#app");
