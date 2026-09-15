import { createRouter, createWebHashHistory } from 'vue-router'
import PluginsView from '../views/PluginsView.vue'
import RunFlowView from '../views/RunFlowView.vue'
import RunsView from '../views/RunsView.vue'

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
