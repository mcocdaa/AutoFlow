<template>
  <el-container class="layout-container">
    <el-header class="header" v-if="!isMobile">
      <div class="logo" @click="goHome">
        <span class="logo-text">AutoFlow</span>
        <span class="logo-subtitle">Workflow Automation</span>
      </div>
      <el-menu mode="horizontal" :router="true" :default-active="$route.path" class="nav-menu">
        <el-menu-item index="/" class="nav-item">
          <el-icon><Grid /></el-icon>
          <span>Plugins</span>
        </el-menu-item>
        <el-menu-item index="/run" class="nav-item">
          <el-icon><CaretRight /></el-icon>
          <span>Run Flow</span>
        </el-menu-item>
      </el-menu>
    </el-header>
    <el-header class="mobile-header" v-else>
      <div class="logo" @click="goHome">
        <span class="logo-text">AutoFlow</span>
      </div>
    </el-header>
    <el-main class="main-content">
      <router-view></router-view>
    </el-main>
    <el-footer class="mobile-nav" v-if="isMobile">
      <el-menu mode="horizontal" :router="true" :default-active="$route.path" class="mobile-menu">
        <el-menu-item index="/" class="mobile-nav-item">
          <el-icon><Grid /></el-icon>
          <span>插件</span>
        </el-menu-item>
        <el-menu-item index="/run" class="mobile-nav-item">
          <el-icon><CaretRight /></el-icon>
          <span>流程</span>
        </el-menu-item>
      </el-menu>
    </el-footer>
  </el-container>
</template>

<script setup lang="ts">
import { Grid, CaretRight } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { ref, onMounted, onUnmounted } from 'vue'

const router = useRouter()
const isMobile = ref(false)

const checkMobile = () => {
  isMobile.value = window.innerWidth < 768
}

const goHome = () => {
  router.push('/')
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style>
:root {
  --primary-color: #667eea;
  --secondary-color: #67c23a;
  --danger-color: #f56c6c;
  --warning-color: #e6a23c;
  --info-color: #909399;
  --light-bg: #f5f7fa;
  --card-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  --transition: all 0.3s ease;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  background-color: var(--light-bg);
  color: #303133;
}

.layout-container {
  min-height: 100vh;
  background-color: var(--light-bg);
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 0 30px;
  height: 64px;
  z-index: 100;
}

.mobile-header {
  display: flex;
  align-items: center;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 0 20px;
  height: 56px;
  z-index: 100;
}

.logo {
  margin-right: 60px;
  cursor: pointer;
  transition: var(--transition);
  display: flex;
  align-items: center;
}

.mobile-header .logo {
  margin-right: 0;
}

.logo:hover {
  opacity: 0.8;
}

.logo-text {
  font-weight: bold;
  font-size: 1.5rem;
  color: var(--primary-color);
  margin-right: 10px;
}

.mobile-header .logo-text {
  font-size: 1.2rem;
}

.logo-subtitle {
  font-size: 0.85rem;
  color: var(--info-color);
}

.nav-menu {
  border-bottom: none !important;
  flex: 1;
}

.nav-item {
  font-size: 1rem;
  padding: 0 20px;
  transition: var(--transition);
}

.nav-item:hover {
  background-color: rgba(102, 126, 234, 0.1) !important;
}

.main-content {
  padding: 30px;
  overflow-y: auto;
  flex: 1;
}

/* 移动端导航 */
.mobile-nav {
  background: white;
  box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.1);
  padding: 0;
  height: 56px;
  z-index: 100;
}

.mobile-menu {
  border-top: none !important;
  display: flex;
  justify-content: space-around;
  height: 100%;
}

.mobile-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 15px;
  height: 100%;
  min-width: 80px;
}

.mobile-nav-item .el-icon {
  font-size: 1.2rem;
  margin-bottom: 4px;
}

.mobile-nav-item span {
  font-size: 0.8rem;
}

/* 滚动条样式 */
.main-content::-webkit-scrollbar {
  width: 8px;
}

.main-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.main-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.main-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 响应式样式 */
@media (max-width: 768px) {
  .main-content {
    padding: 20px 10px;
  }
  
  .header {
    padding: 0 20px;
  }
  
  .logo-subtitle {
    display: none;
  }
  
  .nav-menu {
    justify-content: flex-end;
  }
}
</style>
