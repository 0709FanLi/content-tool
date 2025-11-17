<template>
  <div class="header">
    <div class="header-left">
      <el-button
        link
        @click="toggleSidebar"
        class="menu-btn"
      >
        <el-icon><Menu /></el-icon>
      </el-button>
    </div>

    <div class="header-right">
      <el-dropdown trigger="click" @command="handleCommand">
        <div class="user-btn">
          <el-avatar
            :size="32"
            :src="userStore.avatarUrl"
            class="user-avatar"
          >
            {{ userStore.displayName.charAt(0).toUpperCase() }}
          </el-avatar>
          <span class="user-name">手自澄用户</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">
              <el-icon><SwitchButton /></el-icon>
              <span>退出登录</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  Menu,
  SwitchButton
} from '@element-plus/icons-vue'
import { useUIStore } from '@/stores'
import { useUserStore } from '@/stores'

const router = useRouter()
const uiStore = useUIStore()
const userStore = useUserStore()

// 切换侧边栏
const toggleSidebar = () => {
  uiStore.toggleSidebar()
}

// 处理下拉菜单命令
const handleCommand = async (command: string) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm(
        '确定要退出登录吗？',
        '确认退出',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )

      await userStore.logout()
      uiStore.showSuccess('已退出登录')
      router.push('/login')
    } catch (error) {
      // 用户取消操作
      if (error !== 'cancel') {
        console.error('退出登录失败:', error)
      }
    }
  }
}
</script>

<style scoped>
.header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background-color: #00aaaa;
  border: none;
  position: relative;
}

.header-left {
  display: flex;
  align-items: center;
}

.menu-btn {
  padding: 8px;
  color: #ffffff;
  font-size: 20px;
}

.menu-btn:hover {
  color: #ffffff;
  opacity: 0.8;
}

.menu-btn :deep(.el-icon) {
  font-size: 20px;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 20px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.user-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.user-avatar {
  flex-shrink: 0;
  background-color: #ffffff;
  color: #00aaaa;
  font-weight: 500;
}

.user-name {
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 14px;
  color: #ffffff;
  white-space: nowrap;
}

/* 下拉菜单样式 */
:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
}

:deep(.el-dropdown-menu__item .el-icon) {
  font-size: 16px;
}

/* 响应式 */
@media (max-width: 768px) {
  .header {
    padding: 0 16px;
  }

  .user-name {
    display: none;
  }
}
</style>
