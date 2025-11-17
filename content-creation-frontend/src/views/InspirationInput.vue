<template>
  <div class="inspiration-input">
    <ScriptOptimization
      placeholder="输入您的创意描述···"
      button-text="生成脚本"
      mode="inspiration"
      @success="handleSuccess"
      @error="handleError"
    />
  </div>
</template>

<script setup lang="ts">
import ScriptOptimization from '@/components/common/ScriptOptimization.vue'
import { useProjectStore } from '@/stores'

const projectStore = useProjectStore()

const handleSuccess = (data: any) => {
  // 脚本生成成功后的处理
}

const handleError = (error: string) => {
  // 错误处理
  console.error('脚本生成失败:', error)
}
</script>

<style scoped>
.inspiration-input {
  width: 100%;
  height: 100%;
}
</style>
