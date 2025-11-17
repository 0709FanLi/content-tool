import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { title: '注册', requiresAuth: false }
  },
  {
    path: '/',
    redirect: '/inspiration'
  },
  {
    path: '/inspiration',
    name: 'InspirationInput',
    component: () => import('@/views/InspirationInput.vue'),
    meta: { title: '输入灵感', requiresAuth: true }
  },
  {
    path: '/script-start',
    name: 'ScriptStart',
    component: () => import('@/views/ScriptStart.vue'),
    meta: { title: '从脚本开始', requiresAuth: true }
  },
  {
    path: '/script-generation/:projectId?',
    name: 'ScriptGeneration',
    component: () => import('@/views/ScriptGeneration.vue'),
    meta: { title: '生成脚本', requiresAuth: true },
    props: true
  },
  {
    path: '/video-generation',
    name: 'VideoGeneration',
    component: () => import('@/views/VideoGeneration.vue'),
    meta: { title: '生成视频', requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - 内容创作`
  }

  // 检查认证状态
  const requiresAuth = to.meta.requiresAuth !== false // 默认需要认证
  const isAuthenticated = !!localStorage.getItem('accessToken')


  if (requiresAuth && !isAuthenticated) {
    // 需要认证但未登录，跳转到登录页面
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (!requiresAuth && isAuthenticated && (to.name === 'Login' || to.name === 'Register')) {
    // 已登录用户访问登录/注册页面，跳转到输入灵感页面
    next({ name: 'InspirationInput' })
  } else {
    next()
  }
})

export default router
