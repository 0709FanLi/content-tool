<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1 class="login-title">登录</h1>
        <p class="login-subtitle">欢迎使用内容创作平台</p>
      </div>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        label-position="top"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="用户名或邮箱" prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名或邮箱"
            size="large"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <span>还没有账号？</span>
        <el-link type="primary" @click="goToRegister">立即注册</el-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElForm } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores'
import { authApi } from '@/api'
import type { LoginRequest } from '@/types'

const router = useRouter()
const userStore = useUserStore()

const loginFormRef = ref<InstanceType<typeof ElForm>>()
const loading = ref(false)

const loginForm = reactive<LoginRequest>({
  username: '',
  password: ''
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return

  try {
    await loginFormRef.value.validate()

    loading.value = true

    const response = await authApi.login(loginForm)

    // 保存token到本地存储
    localStorage.setItem('accessToken', response.access_token)
    localStorage.setItem('refreshToken', response.refresh_token)

    // 更新用户状态
    userStore.setUser(response.user)

    ElMessage.success('登录成功')

    // 跳转到输入灵感页面
    router.push('/inspiration')

  } catch (error: any) {
    console.error('登录失败:', error)
    console.error('错误详情:', {
      message: error?.message,
      response: error?.response,
      responseData: error?.response?.data,
      code: error?.code
    })
    // 后端可能返回 detail 或 message 字段
    const errorMessage = error?.message || 
                        error?.response?.data?.detail || 
                        error?.response?.data?.message || 
                        '登录失败，请检查用户名和密码'
    ElMessage.error(errorMessage)
  } finally {
    loading.value = false
  }
}

const goToRegister = () => {
  router.push('/register')
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  padding: 40px;
  backdrop-filter: blur(10px);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-title {
  font-size: 28px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.login-subtitle {
  color: #666;
  font-size: 14px;
}

.login-form {
  margin-bottom: 24px;
}

.login-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.login-btn {
  width: 100%;
  height: 48px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
}

.login-footer {
  text-align: center;
  color: #666;
  font-size: 14px;
}

.login-footer .el-link {
  margin-left: 4px;
  font-weight: 500;
}

/* 响应式 */
@media (max-width: 480px) {
  .login-container {
    padding: 16px;
  }

  .login-card {
    padding: 24px;
  }

  .login-title {
    font-size: 24px;
  }
}
</style>
