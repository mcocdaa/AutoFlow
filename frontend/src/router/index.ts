import { createRouter, createWebHashHistory } from 'vue-router'
import PluginsView from '../views/PluginsView.vue'
import RunFlowView from '../views/RunFlowView.vue'

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
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
