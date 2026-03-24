<template>
  <el-dialog
    v-model="dialogVisible"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    width="500px"
    align-center
  >
    <!-- 关闭按钮 -->
    <div class="close-button" @click="handleCancel">
      <el-icon><Close /></el-icon>
    </div>
    <div class="loading-container">
      <!-- 动画图标 -->
      <div class="loading-icon">
        <div class="plane-animation">
          ✈️
        </div>
      </div>

      <!-- 标题 -->
      <h3 class="loading-title">{{ currentStatus.title }}</h3>
      
      <!-- 描述 -->
      <p class="loading-description">{{ currentStatus.description }}</p>

      <!-- 进度条 -->
      <div class="progress-wrapper">
        <el-progress
          :percentage="progress"
          :stroke-width="12"
          :color="progressColors"
          :show-text="false"
        />
        <!-- 不显示实时进度百分比 -->
      </div>

      <!-- 状态步骤 -->
      <div class="steps-wrapper">
        <el-steps :active="activeStep" align-center finish-status="success">
          <el-step 
            v-for="step in steps" 
            :key="step.id"
            :title="step.title"
            :icon="step.icon"
          />
        </el-steps>
      </div>

      <!-- 提示信息 -->
      <div class="tips">
        <el-icon class="tip-icon"><InfoFilled /></el-icon>
        <span>{{ randomTip }}</span>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { InfoFilled, Close } from '@element-plus/icons-vue'
import type { TripPlanProgressEvent } from '@/services/api'

interface Props {
  visible: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:visible': [value: boolean]
  'cancel': []
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const progress = ref(0)
const activeStep = ref(0)
const tipInterval = ref<number>()
const randomTip = ref('')
// 当前进度消息（来自真实 SSE 事件）
const currentMessage = ref('正在启动规划引擎...')

// 进度条颜色
const progressColors = [
  { color: '#6366f1', percentage: 30 },
  { color: '#8b5cf6', percentage: 60 },
  { color: '#ec4899', percentage: 100 }
]

// 加载步骤
const steps = [
  { id: 1, title: '分析需求', icon: 'Search' },
  { id: 2, title: '查询信息', icon: 'DataAnalysis' },
  { id: 3, title: '智能规划', icon: 'MagicStick' },
  { id: 4, title: '生成行程', icon: 'Check' }
]

// SSE 阶段 → 步骤映射
const stageToStep: Record<string, number> = {
  phase1_start: 0,
  phase1_attraction_done: 1,
  phase1_weather_done: 1,
  phase2_start: 2,
  phase2_day_done: 2,
  phase3_start: 3,
  done: 3
}

// 当前状态文案（根据真实进度动态生成）
const currentStatus = computed(() => {
  if (progress.value < 15) {
    return { title: '🔍 正在分析您的需求...', description: '了解您的旅行偏好和预算范围' }
  } else if (progress.value < 35) {
    return { title: '📍 正在查询目的地信息...', description: currentMessage.value }
  } else if (progress.value < 88) {
    return { title: '🤖 AI正在智能规划中...', description: currentMessage.value }
  } else if (progress.value < 100) {
    return { title: '🎨 正在合成行程方案...', description: currentMessage.value }
  } else {
    return { title: '✨ 规划完成！', description: '您的专属旅行计划已生成' }
  }
})

// 旅行小贴士
const tips = [
  '💡 提前预订门票可以节省排队时间',
  '💡 建议准备一个充电宝，随时为设备充电',
  '💡 出行前检查目的地天气，准备合适衣物',
  '💡 下载离线地图，即使没有网络也能导航',
  '💡 记录重要信息，如酒店地址和联系方式',
  '💡 随身携带常用药品，以备不时之需',
  '💡 尊重当地文化和习俗，做文明游客',
  '💡 保管好个人财物和重要证件',
  '💡 品尝当地特色美食，体验地道风味',
  '💡 适当安排休息时间，避免过度疲劳'
]

const updateRandomTip = () => {
  randomTip.value = tips[Math.floor(Math.random() * tips.length)]
}

// 接收真实 SSE 进度事件，更新进度和步骤
const handleProgressEvent = (event: TripPlanProgressEvent) => {
  // 平滑更新进度：只允许进度前进，不允许后退
  if (event.progress > progress.value) {
    progress.value = event.progress
  }
  if (event.message) {
    currentMessage.value = event.message
  }
  const step = stageToStep[event.stage]
  if (step !== undefined && step > activeStep.value) {
    activeStep.value = step
  }
}

// 重置状态（每次打开弹窗时调用）
const resetProgress = () => {
  progress.value = 0
  activeStep.value = 0
  currentMessage.value = '正在启动规划引擎...'
  updateRandomTip()
  tipInterval.value = window.setInterval(updateRandomTip, 4000)
}

// 停止（关闭弹窗时调用）
const stopProgress = () => {
  if (tipInterval.value) {
    clearInterval(tipInterval.value)
    tipInterval.value = undefined
  }
}

// 完成进度（规划成功后调用）
const completeProgress = () => {
  progress.value = 100
  activeStep.value = steps.length - 1
  currentMessage.value = '行程规划完成！'
}

// 监听可见性变化
watch(() => props.visible, (newVal) => {
  if (newVal) {
    resetProgress()
  } else {
    stopProgress()
  }
})

onUnmounted(() => {
  stopProgress()
})

const handleCancel = () => {
  stopProgress()
  emit('cancel')
  emit('update:visible', false)
}

defineExpose({
  completeProgress,
  handleProgressEvent
})
</script>

<style scoped lang="scss">
.loading-container {
  padding: 40px 20px;
  text-align: center;

  .loading-icon {
    margin-bottom: 30px;
    
    .plane-animation {
      font-size: 80px;
      display: inline-block;
      animation: fly 2s ease-in-out infinite;
    }
  }

  .loading-title {
    margin: 0 0 12px 0;
    font-size: 24px;
    font-weight: 600;
    color: #303133;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .loading-description {
    margin: 0 0 30px 0;
    font-size: 14px;
    color: #909399;
  }

  .progress-wrapper {
    margin-bottom: 30px;
    position: relative;
  }

  .steps-wrapper {
    margin: 40px 0 30px 0;
  }

  .tips {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 16px;
    background: #f0f9ff;
    border-radius: 8px;
    font-size: 14px;
    color: #606266;
    transition: all 0.5s ease;

    .tip-icon {
      color: #409eff;
      font-size: 16px;
    }
  }
}

@keyframes fly {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  25% {
    transform: translateY(-20px) rotate(-5deg);
  }
  50% {
    transform: translateY(0) rotate(0deg);
  }
  75% {
    transform: translateY(-10px) rotate(5deg);
  }
}

:deep(.el-dialog) {
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

:deep(.el-dialog__body) {
  padding: 0;
  position: relative;
}

.close-button {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 50%;
  cursor: pointer;
  z-index: 1000;
  transition: all 0.3s;
  
  &:hover {
    background: rgba(0, 0, 0, 0.1);
    transform: scale(1.1);
  }
  
  .el-icon {
    font-size: 18px;
    color: #909399;
  }
  
  &:hover .el-icon {
    color: #303133;
  }
}

:deep(.el-step__title) {
  font-size: 13px;
}

:deep(.el-step__icon) {
  width: 28px;
  height: 28px;
}
</style>
