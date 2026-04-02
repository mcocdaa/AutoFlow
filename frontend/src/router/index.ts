import { createRouter, createWebHashHistory } from "vue-router";
import PluginsView from "../views/PluginsView.vue";
import RunFlowView from "../views/RunFlowView.vue";
import WorkflowEditor from "../views/WorkflowEditor.vue";

const routes = [
  {
    path: "/",
    name: "plugins",
    component: PluginsView,
  },
  {
    path: "/run",
    name: "run",
    component: RunFlowView,
  },
  {
    path: "/editor",
    name: "editor",
    component: WorkflowEditor,
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;
