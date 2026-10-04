import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { openPluginDialog } from "./state/pluginExtensions";
import { configureNativePluginHost } from "./state/pluginNative";
import { startPwa } from "./services/pwa";
import "./style.css";
import "./styles/ui.css";
import "./styles/tokens.css";
import { initializeUiAppearance } from "./state/uiAppearance";

initializeUiAppearance();

configureNativePluginHost(router, openPluginDialog);
startPwa();
createApp(App).use(router).mount("#app");
