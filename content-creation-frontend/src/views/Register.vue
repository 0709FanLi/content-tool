<template>
  <div class="register-container">
    <div class="register-card">
      <div class="register-header">
        <h1 class="register-title">注册</h1>
        <p class="register-subtitle">创建您的内容创作账号</p>
      </div>

      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        label-position="top"
        class="register-form"
        @submit.prevent="handleRegister"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="请输入用户名（3-50位字母、数字、下划线）"
            size="large"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="registerForm.email"
            type="email"
            placeholder="请输入邮箱地址"
            size="large"
            :prefix-icon="Message"
            clearable
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码（至少6位，包含字母和数字）"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="register-btn"
            :loading="loading"
            @click="handleRegister"
          >
            注册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="register-footer">
        <span>已有账号？</span>
        <el-link type="primary" @click="goToLogin">立即登录</el-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElForm } from 'element-plus'
import { User, Lock, Message } from '@element-plus/icons-vue'
import { authApi } from '@/api'

const router = useRouter()

const registerFormRef = ref<InstanceType<typeof ElForm>>()
const loading = ref(false)

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

// 密码验证规则
const validatePassword = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入密码'))
    return
  }

  if (value.length < 6) {
    callback(new Error('密码长度不能少于6位'))
    return
  }

  // 检查是否包含字母和数字
  const hasLetter = /[a-zA-Z]/.test(value)
  const hasDigit = /\d/.test(value)

  if (!hasLetter || !hasDigit) {
    callback(new Error('密码必须包含字母和数字'))
    return
  }

  callback()
}

// 确认密码验证规则
const validateConfirmPassword = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请再次输入密码'))
    return
  }

  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
    return
  }

  callback()
}

// 用户名验证规则
const validateUsername = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入用户名'))
    return
  }

  if (value.length < 3 || value.length > 50) {
    callback(new Error('用户名长度必须在3-50位之间'))
    return
  }

  if (!/^[a-zA-Z0-9_]+$/.test(value)) {
    callback(new Error('用户名只能包含字母、数字和下划线'))
    return
  }

  callback()
}

const registerRules = {
  username: [
    { required: true, validator: validateUsername, trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, validator: validatePassword, trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const handleRegister = async () => {
  if (!registerFormRef.value) return

  try {
    await registerFormRef.value.validate()

    loading.value = true

    await authApi.register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password
    })

    ElMessage.success('注册成功，请登录')

    // 跳转到登录页面
    router.push('/login')

  } catch (error: any) {
    console.error('注册失败:', error)
    ElMessage.error(error?.response?.data?.message || '注册失败，请检查输入信息')
  } finally {
    loading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.register-card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  padding: 40px;
  backdrop-filter: blur(10px);
}

.register-header {
  text-align: center;
  margin-bottom: 32px;
}

.register-title {
  font-size: 28px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.register-subtitle {
  color: #666;
  font-size: 14px;
}

.register-form {
  margin-bottom: 24px;
}

.register-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.register-form :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.register-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.register-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.register-btn {
  width: 100%;
  height: 48px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
}

.register-footer {
  text-align: center;
  color: #666;
  font-size: 14px;
}

.register-footer .el-link {
  margin-left: 4px;
  font-weight: 500;
}

/* 响应式 */
@media (max-width: 480px) {
  .register-container {
    padding: 16px;
  }

  .register-card {
    padding: 24px;
  }

  .register-title {
    font-size: 24px;
  }
}
</style>
