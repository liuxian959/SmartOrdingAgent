// Vue 应用启动入口：创建根实例、注册全局依赖并挂载到页面 DOM。
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import { ElMessage } from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'

const app = createApp(App)

// 注册Element Plus
app.use(ElementPlus)

// Vue 组件未捕获的异常统一在此记录，并显示对用户友好的提示。
app.config.errorHandler = (err) => {
  try {
    console.error(err)
    ElMessage.error(err?.message || '页面运行出错')
  } catch (e) {
    // ignore
  }
}

app.mount('#app') 
