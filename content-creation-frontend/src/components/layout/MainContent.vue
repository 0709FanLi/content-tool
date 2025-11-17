<template>
  <div class="main-content">
    <!-- 侧边栏 -->
    <Sidebar />

    <!-- 右侧内容区域 -->
    <div class="right-content">
      <!-- 头部 -->
      <Header />

      <!-- 内容区域 -->
      <div class="content-area">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'
</script>

<style scoped>
.main-content {
  display: flex;
  flex-direction: row;
  height: 100vh;
  width: 100%;
  background: #3f3f3f;
  gap: 0;
  padding: 0;
  overflow: hidden;
}

.right-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  width: calc(100% - 214px);
  overflow: hidden;
}

.content-area {
  flex: 1;
  padding: 0;
  overflow-y: auto;
  background-color: #3f3f3f;
}

/* 响应式 */
@media (max-width: 768px) {
  .right-content {
    width: 100%;
  }
  
  .content-area {
    padding: 16px;
  }
}
</style>
