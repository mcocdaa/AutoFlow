import { createApp } from "vue";
import { createPinia } from "pinia";
import Antd from "ant-design-vue";
// @ts-ignore
import "ant-design-vue/dist/reset.css";
import App from "./App.vue";
import router from "./router";
import { FDS_CSS_VARS } from "./theme/flow-design-theme";

const style = document.createElement("style");
style.textContent = FDS_CSS_VARS + `
html, body {
  overflow: hidden;
  height: 100%;
}
#app {
  height: 100%;
}
`;
document.head.appendChild(style);

const app = createApp(App);

app.use(createPinia());
app.use(router);
app.use(Antd);

app.mount("#app");
