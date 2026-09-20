import { createRouter, createWebHashHistory } from 'vue-router'
import FlowCanvasView from '../views/FlowCanvasView.vue'
import FlowHubView from '../views/FlowHubView.vue'
import PluginsView from '../views/PluginsView.vue'
import RunFlowView from '../views/RunFlowView.vue'
import RunsView from '../views/RunsView.vue'
import DebugView from '../views/DebugView.vue'
import SecretsView from '../views/SecretsView.vue'

const routes = [
  {
    path: '/',
    redirect: '/canvas',
  },
  {
    path: '/canvas',
    name: 'canvas',
    component: FlowCanvasView,
  },
  {
    path: '/hub',
    name: 'hub',
    component: FlowHubView,
  },
  {
    path: '/plugins',
    name: 'plugins',
    component: PluginsView,
  },
  {
    path: '/secrets',
    name: 'secrets',
    component: SecretsView,
  },
  {
    path: '/run',
    name: 'run',
    component: RunFlowView,
  },
  {
    path: '/debug',
    name: 'debug',
    component: DebugView,
  },
  {
    path: '/runs',
    name: 'runs',
    component: RunsView,
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
