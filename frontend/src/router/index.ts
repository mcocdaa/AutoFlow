import { createRouter, createWebHashHistory } from 'vue-router'
import PluginsView from '../views/PluginsView.vue'
import RunFlowView from '../views/RunFlowView.vue'
import RunsView from '../views/RunsView.vue'
import DebugView from '../views/DebugView.vue'

const routes = [
  {
    path: '/',
    name: 'plugins',
    component: PluginsView,
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
