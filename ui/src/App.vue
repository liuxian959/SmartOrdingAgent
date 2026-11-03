<template>
  <div id="app">
    <el-container class="main-container">
      <el-header class="header">
        <div class="header-content">
          <div class="brand-mark">食</div>
          <div class="brand-copy">
            <h1>食光 · 智能点餐</h1>
            <span>让每一餐，都刚刚好</span>
          </div>
        </div>
        <div class="header-status">
          <span class="status-dot"></span>
          在线为您服务
        </div>
      </el-header>
      
      <el-main class="main-content">
        <el-row :gutter="20">
          <!-- 左侧：智能对话区域 -->
          <el-col :span="10">
            <el-card class="chat-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <div class="section-heading">
                    <span class="section-icon chat-icon">✦</span>
                    <div><strong>专属点餐顾问</strong><small>告诉我你的口味和想法</small></div>
                  </div>
                  <el-tag size="small" type="success" effect="light">AI 在线</el-tag>
                </div>
              </template>
              
              <!-- 聊天历史记录 -->
              <div class="chat-history" ref="chatHistoryRef">
                <div v-if="chatMessages.length === 0" class="welcome-message">
                  <div class="welcome-orb">✦</div>
                  <p class="welcome-eyebrow">WELCOME TO SHIGUANG</p>
                  <h2>今天想吃点什么？</h2>
                  <p>告诉我你的口味、忌口或用餐计划，<br>我来为你挑选合适的美味。</p>
                  <div class="suggestion-chips">
                    <el-tag class="chip" @click="quickAsk('你们几点营业？')">营业时间</el-tag>
                    <el-tag class="chip" @click="quickAsk('推荐几个不辣的菜')">清淡不辣</el-tag>
                  </div>
                </div>
                
                <div v-for="(msg, index) in chatMessages" :key="index" class="message-wrapper" :class="msg.role">
                  <div class="avatar">
                    {{ msg.role === 'user' ? '👤' : '🤖' }}
                  </div>
                  <div class="message-bubble">
                    <div v-if="msg.role === 'assistant'" class="markdown-content">{{ msg.content }}</div>
                    <div v-else>{{ msg.content }}</div>
                  </div>
                </div>
                
                <div v-if="chatLoading" class="message-wrapper assistant">
                  <div class="avatar">🤖</div>
                  <div class="message-bubble loading-bubble">
                    <div class="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 输入区域 -->
              <div v-if="faqSuggestionsVisible" class="faq-suggestions">
                <div class="faq-suggestions-title">您可能想问：</div>
                <div class="faq-suggestions-list">
                  <el-button
                    v-for="item in faqSuggestions"
                    :key="item.id"
                    type="primary"
                    plain
                    size="small"
                    class="faq-suggestion-btn"
                    @click="selectFaqSuggestion(item)"
                  >
                    {{ item.question }}
                  </el-button>
                </div>
              </div>

              <div class="chat-input-wrapper">
                <el-input
                  v-model="chatQuery"
                  type="textarea"
                  :rows="2"
                  placeholder="请输入您的需求..."
                  class="chat-input"
                  @keyup.enter.native.prevent="sendChatQuery"
                  resize="none"
                />
                <el-button
                  type="primary"
                  @click="sendChatQuery"
                  :loading="chatLoading"
                  class="send-btn"
                  circle
                >
                  <template #icon>
                    <span>➤</span>
                  </template>
                </el-button>
              </div>
            </el-card>
          </el-col>
          
          <!-- 右侧：功能区域 -->
          <el-col :span="14">

            <!-- 预订信息 -->
            <el-card class="reservation-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>📅 预订信息</span>
                  <el-button type="text" @click="loadReservations" :loading="reservationLoading">刷新</el-button>
                </div>
              </template>
              <div class="reservation-body">
                <div v-if="reservationLoading" class="reservation-loading">
                  <el-skeleton :rows="3" animated />
                </div>
                <div v-else-if="reservations.length > 0" class="reservation-list">
                  <div v-for="item in reservations" :key="item.id" class="reservation-item">
                    <div class="reservation-title">
                      <span>预订 #{{ item.id }}</span>
                      <span class="reservation-time">{{ item.arrival_time }}</span>
                    </div>
                    <div class="reservation-meta">
                      <span>👥 {{ item.num_people }} 人</span>
                      <span>🧒 {{ item.num_children }} 儿童</span>
                      <span v-if="item.seat_preference">🪑 {{ item.seat_preference }}</span>
                      <span v-if="item.main_dish_preference">🍲 {{ item.main_dish_preference }}</span>
                    </div>
                    <div v-if="item.other_comments" class="reservation-comments">
                      {{ item.other_comments }}
                    </div>
                  </div>
                </div>
                <el-empty v-else description="暂无预订信息" image-size="60"></el-empty>
              </div>
            </el-card>


            
            <!-- 菜品列表 -->
            <el-card class="menu-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>📋 菜单列表</span>
                  <el-tag size="small" effect="plain">数量: {{ menuItems.length }}</el-tag>
                  <el-button type="text" @click="loadMenuItems" :loading="menuLoading">刷新</el-button>
                </div>
              </template>
              
              <div class="menu-container">
                 <el-alert
                   v-if="menuError"
                   :title="menuError"
                   type="error"
                   :closable="true"
                   show-icon
                   effect="dark"
                   style="margin-bottom: 12px;"
                 />
                 <div v-if="menuLoading" class="loading-state">
                    <el-skeleton :rows="5" animated />
                 </div>
                 
                 <div v-else-if="menuItems.length > 0" class="menu-grid">
                    <div
                      v-for="item in menuItems"
                      :key="item.id"
                      class="menu-item-card"
                      :class="{
                        highlighted: highlightedItems.includes(getItemIdStr(item)),
                        flashing: flashingItems.includes(getItemIdStr(item))
                      }"
                    >
                      <div class="item-badge" v-if="highlightedItems.includes(getItemIdStr(item))">推荐</div>
                      <div class="item-header">
                        <div class="item-name">{{ item.dish_name }}</div>
                        <div class="item-price">{{ item.formatted_price }}</div>
                      </div>
                      <div class="item-tags">
                         <el-tag size="small" effect="plain">{{ item.category }}</el-tag>
                         <el-tag size="small" :type="getSpiceType(item.spice_level)" effect="light">{{ item.spice_text }}</el-tag>
                         <el-tag v-if="item.is_vegetarian" size="small" type="success" effect="light">素食</el-tag>
                      </div>
                      <div class="item-desc" :title="item.description">{{ item.description }}</div>
                    </div>
                 </div>
                 <el-empty v-else description="暂无菜品" />
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>


  </div>
</template>

<script>
// ref/computed 管理响应式状态，watch 监听输入变化，onMounted 初始化页面数据。
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import { chatAPI, menuAPI, faqAPI, reservationAPI } from './api/index.js'
import { ElMessage } from 'element-plus'

const CHAT_SESSION_STORAGE_KEY = 'smart-ordering-chat-session-id'

function getChatSessionId() {
  let sessionId = sessionStorage.getItem(CHAT_SESSION_STORAGE_KEY)
  if (!sessionId) {
    sessionId = crypto.randomUUID()
    sessionStorage.setItem(CHAT_SESSION_STORAGE_KEY, sessionId)
  }
  return sessionId
}

export default {
  name: 'App',
  setup() {
    // 聊天输入、消息列表、加载状态以及滚动容器引用。
    const chatQuery = ref('')
    const chatMessages = ref([])
    const sessionId = getChatSessionId()
    const chatLoading = ref(false)
    const chatHistoryRef = ref(null)
    const faqSuggestions = ref([])
    const faqSuggestLoading = ref(false)
    let faqSuggestTimer = null

    // 菜单相关
    const menuItems = ref([])
    const menuLoading = ref(false)
    const menuError = ref('')
    const highlightedItems = ref([])
    const flashingItems = ref([])
    let autoHighlightTimer = null
    let lastHighlightKey = ''

    // 预订信息
    const reservations = ref([])
    const reservationLoading = ref(false)

    // 滚动到底部
    const scrollToBottom = async () => {
      await nextTick()
      if (chatHistoryRef.value) {
        chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
      }
    }

    // 快速提问
    const quickAsk = (text) => {
      chatQuery.value = text
      sendChatQuery()
    }

    const fetchFaqSuggestions = async (query) => {
      const q = (query || '').trim()
      if (!q) {
        faqSuggestions.value = []
        return
      }
      faqSuggestLoading.value = true
      try {
        const res = await faqAPI.suggest(q, 6)
        const items = Array.isArray(res?.suggestions) ? res.suggestions : []
        faqSuggestions.value = items
      } catch (e) {
        faqSuggestions.value = []
      } finally {
        faqSuggestLoading.value = false
      }
    }

    const selectFaqSuggestion = async (item) => {
      if (!item?.question || !item?.answer) return
      if (chatLoading.value) return
      const question = item.question
      const answer = item.answer
      chatMessages.value.push({ role: 'user', content: question })
      chatMessages.value.push({ role: 'assistant', content: answer })
      chatQuery.value = ''
      faqSuggestions.value = []
      scrollToBottom()
    }

    // 提交用户消息并消费后端 SSE；每收到一个 token 就追加到当前助手消息中。
    const sendChatQuery = async () => {
      if (!chatQuery.value.trim() || chatLoading.value) return
      
      const query = chatQuery.value
      faqSuggestions.value = []
      chatMessages.value.push({ role: 'user', content: query })
      chatQuery.value = ''
      chatLoading.value = true
      scrollToBottom()

      let hasCreatedMessage = false

      await chatAPI.sendStreamMessage(
        query,
        sessionId,
        (data) => {
          if (data?.type === 'recommendation' || data?.menu_ids) {
            highlightRecommendedItems(data.menu_ids)
          }

          const token =
            data?.type === 'token'
              ? (typeof data?.content === 'string'
                  ? data.content
                  : typeof data?.data === 'string'
                    ? data.data
                    : '')
              : ''
          const err = data?.type === 'error' ? data?.error : data?.error

          if (token) {
            if (!hasCreatedMessage) {
              chatLoading.value = false
              chatMessages.value.push({ role: 'assistant', content: '' })
              hasCreatedMessage = true
            }
            const currentMsg = chatMessages.value[chatMessages.value.length - 1]
            currentMsg.content += token
            scheduleAutoHighlightFromText(currentMsg.content)
            scrollToBottom()
          }

          if (err) {
            if (!hasCreatedMessage) {
              chatLoading.value = false
              chatMessages.value.push({ role: 'assistant', content: '' })
              hasCreatedMessage = true
            }
            const currentMsg = chatMessages.value[chatMessages.value.length - 1]
            currentMsg.content += `\n[错误: ${err}]`
          }
        },
        (error) => {
          console.error('Chat error:', error)
          chatLoading.value = false
          
          if (!hasCreatedMessage) {
            chatMessages.value.push({ role: 'assistant', content: '' })
            hasCreatedMessage = true
          }
          const currentMsg = chatMessages.value[chatMessages.value.length - 1]
          currentMsg.content += '\n[网络错误，请检查连接]'
        },
        () => {
          chatLoading.value = false
          scrollToBottom()
        }
      )
    }

    // 加载菜单
    const getMenuItemsFromResponse = (response) => {
      if (!response) return []
      if (Array.isArray(response)) return response
      if (Array.isArray(response.menu_items)) return response.menu_items
      if (Array.isArray(response.menuItems)) return response.menuItems
      const data = response.data
      if (Array.isArray(data)) return data
      if (Array.isArray(data?.menu_items)) return data.menu_items
      if (Array.isArray(data?.menuItems)) return data.menuItems
      if (Array.isArray(data?.items)) return data.items
      return []
    }

    const loadMenuItems = async () => {
      menuLoading.value = true
      menuError.value = ''
      try {
        const response = await menuAPI.getMenuList()
        const items = getMenuItemsFromResponse(response)
        menuItems.value = items
        if (!items.length && response?.message) {
          ElMessage.warning(response.message)
        }
      } catch (e) {
        menuItems.value = []
        menuError.value = e?.message || '菜品获取失败'
        ElMessage.error(menuError.value)
      } finally {
        menuLoading.value = false
      }
    }

    const loadReservations = async () => {
      reservationLoading.value = true
      try {
        const res = await reservationAPI.list(10)
        reservations.value = Array.isArray(res?.reservations) ? res.reservations : []
      } catch (e) {
        reservations.value = []
        ElMessage.error(e?.message || '预订信息获取失败')
      } finally {
        reservationLoading.value = false
      }
    }

    // 高亮推荐
    const highlightRecommendedItems = (ids) => {
      if (!ids) return
      const normalized = (Array.isArray(ids) ? ids : [])
        .map(id => (id == null ? '' : String(id)))
        .filter(Boolean)
      const unique = Array.from(new Set(normalized)).sort()
      const key = unique.join(',')
      if (!key || key === lastHighlightKey) return
      lastHighlightKey = key
      highlightedItems.value = unique
      flashingItems.value = unique
      window.setTimeout(() => {
        flashingItems.value = []
      }, 900)
      // 滚动到菜单区域
      // 这里如果需要可以做自动滚动，但现在布局是左右分栏，可能不需要强制滚动
    }

    const extractMenuIdsFromText = (text) => {
      if (!text) return []
      const ids = []
      for (const item of menuItems.value) {
        if (!item?.dish_name || item?.id == null) continue
        if (text.includes(item.dish_name)) ids.push(String(item.id))
      }
      return ids
    }

    const getItemIdStr = (item) => {
      if (!item || item.id == null) return ''
      return String(item.id)
    }

    const scheduleAutoHighlightFromText = (text) => {
      if (autoHighlightTimer) window.clearTimeout(autoHighlightTimer)
      autoHighlightTimer = window.setTimeout(() => {
        const ids = extractMenuIdsFromText(text)
        if (ids.length) highlightRecommendedItems(ids)
      }, 240)
    }

    const getSpiceType = (level) => {
      return ['', 'success', 'warning', 'danger'][level] || ''
    }

    const cleanupBrowserCaches = async () => {
      try {
        if ('serviceWorker' in navigator) {
          const regs = await navigator.serviceWorker.getRegistrations()
          for (const reg of regs) {
            try {
              await reg.unregister()
            } catch (e) {
              // ignore
            }
          }
        }
        if ('caches' in window) {
          const keys = await window.caches.keys()
          for (const k of keys) {
            try {
              await window.caches.delete(k)
            } catch (e) {
              // ignore
            }
          }
        }
      } catch (e) {
        // ignore
      }
    }

    onMounted(() => {
      cleanupBrowserCaches()
      loadMenuItems()
      loadReservations()
    })

    watch(
      chatQuery,
      (val) => {
        if (faqSuggestTimer) window.clearTimeout(faqSuggestTimer)
        const q = (val || '').trim()
        if (!q || q.length < 2 || chatLoading.value) {
          faqSuggestions.value = []
          return
        }
        faqSuggestTimer = window.setTimeout(() => {
          fetchFaqSuggestions(q)
        }, 220)
      },
      { flush: 'post' }
    )

    return {
      chatQuery,
      chatMessages,
      chatLoading,
      chatHistoryRef,
      sendChatQuery,
      quickAsk,
      faqSuggestions,
      faqSuggestLoading,
      selectFaqSuggestion,
      faqSuggestionsVisible: computed(() => !faqSuggestLoading.value && faqSuggestions.value.length > 0),
      
      menuItems,
      menuLoading,
      menuError,
      highlightedItems,
      flashingItems,
      loadMenuItems,
      getSpiceType,
      getItemIdStr,

      reservations,
      reservationLoading,
      loadReservations
    }
  }
}
</script>

<style>
/* 全局重置 */
body {
  margin: 0;
  background: #f5f6f2;
  color: #24332b;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
}

#app {
  height: 100vh;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.main-container {
  height: 100%;
  min-height: 0;
}

/* 头部 */
.header {
  height: 76px;
  flex: 0 0 76px;
  background: rgba(255, 255, 255, 0.94);
  border-bottom: 1px solid #e9eee8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 30px;
  z-index: 10;
}

.header-content, .section-heading, .header-status {
  display: flex;
  align-items: center;
}

.header-content { gap: 12px; }

.brand-mark {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: linear-gradient(145deg, #2c7654, #174a38);
  color: #fff;
  font-size: 21px;
  font-weight: 700;
  box-shadow: 0 7px 16px rgba(28, 94, 65, .2);
}

.brand-copy h1 { font-size: 17px; margin: 0; color: #20382c; letter-spacing: .04em; }
.brand-copy span { display: block; margin-top: 3px; color: #849187; font-size: 11px; letter-spacing: .1em; }
.header-status { gap: 8px; color: #597264; font-size: 12px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #52b788; box-shadow: 0 0 0 4px #e8f5ed; }

/* 主内容区 */
.main-content {
  flex: 1;
  min-height: 0;
  padding: 24px 30px 28px;
  overflow: hidden;
  background:
    radial-gradient(ellipse at 8% 0%, rgba(227, 239, 225, .7), transparent 35%),
    #f5f6f2;
}

.el-row, .el-col {
  height: 100%;
  min-height: 0;
}

/* 卡片通用 */
.el-card {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(223, 231, 222, .9);
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 12px 36px rgba(29, 57, 40, .06);
  transition: box-shadow .25s ease, transform .25s ease;
}

.el-card:hover { box-shadow: 0 16px 42px rgba(29, 57, 40, .1); }
.el-card__header { padding: 18px 20px; border-bottom: 1px solid #edf1ec; }

.el-card__body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-weight: 600;
}

.section-heading { gap: 11px; }
.section-heading strong { display: block; color: #263b30; font-size: 14px; }
.section-heading small { display: block; margin-top: 4px; color: #98a49a; font-size: 11px; font-weight: 400; }
.section-icon { width: 34px; height: 34px; border-radius: 11px; display: grid; place-items: center; font-size: 16px; }
.chat-icon { background: #eaf4ed; color: #327452; }

/* 聊天卡片 */
.chat-card .el-card__body {
  padding: 0;
  background: linear-gradient(180deg, #fbfcfa 0%, #f7f9f6 100%);
  border-radius: 0 0 18px 18px;
}

.chat-history {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 17px;
  scrollbar-width: thin;
  scrollbar-color: #d5dfd6 transparent;
}

.welcome-message {
  text-align: center;
  color: #839087;
  margin: auto 0;
  padding: 24px 8px;
}

.welcome-orb {
  width: 54px;
  height: 54px;
  margin: 0 auto 17px;
  display: grid;
  place-items: center;
  border-radius: 18px;
  color: #fff;
  font-size: 25px;
  background: linear-gradient(145deg, #78a987, #2f6b4b);
  box-shadow: 0 10px 24px rgba(47, 107, 75, .23);
}

.welcome-eyebrow { margin: 0 0 8px !important; color: #9aaa9d !important; font-size: 9px; letter-spacing: .2em; }
.welcome-message h2 { margin: 0 0 9px; color: #294435; font-size: 21px; font-weight: 650; }
.welcome-message p { line-height: 1.8; font-size: 12px; }

.suggestion-chips {
  margin-top: 15px;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}

.chip {
  cursor: pointer;
  height: auto;
  padding: 8px 13px;
  border: 1px solid #e1eae1;
  border-radius: 999px;
  background: #fff;
  color: #53745d;
  transition: all 0.2s ease;
}

.chip:hover {
  transform: translateY(-2px);
  border-color: #8bb499;
  background: #f2f8f2;
  color: #286344;
}

.message-wrapper {
  display: flex;
  gap: 10px;
  max-width: 90%;
  animation: messageIn .24s ease both;
}

@keyframes messageIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

.message-wrapper.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: #eaf2eb;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 9px rgba(38, 70, 48, .08);
  font-size: 17px;
  flex-shrink: 0;
}

.message-bubble {
  white-space: pre-wrap;
  background: #fff;
  padding: 12px 15px;
  border: 1px solid #edf0eb;
  border-radius: 4px 16px 16px 16px;
  box-shadow: 0 4px 12px rgba(29, 57, 40, .045);
  line-height: 1.65;
  font-size: 13px;
  color: #3a4a40;
  overflow-wrap: anywhere;
}

.message-wrapper.user .message-bubble {
  background: linear-gradient(135deg, #3d8b63, #2b704e);
  border-color: transparent;
  color: white;
  border-radius: 16px 4px 16px 16px;
  box-shadow: 0 6px 14px rgba(43, 112, 78, .17);
}

.message-wrapper.assistant .message-bubble {
  border-top-left-radius: 2px;
}

.chat-input-wrapper {
  padding: 14px 16px 16px;
  background: #fff;
  display: flex;
  gap: 10px;
  align-items: flex-end;
  border-top: 1px solid #edf1ec;
}

.chat-input-wrapper .el-textarea__inner { border: 1px solid #e7ece6; border-radius: 13px; box-shadow: none; padding: 11px 13px; background: #fafbf9; }
.chat-input-wrapper .el-textarea__inner:focus { border-color: #76a789; background: #fff; }
.send-btn { width: 42px; height: 42px; border: 0; background: #2f7652; box-shadow: 0 5px 12px rgba(47, 118, 82, .2); }
.send-btn:hover { background: #246442; }


.faq-suggestions {
  background: white;
  border-top: 1px solid #eee;
  padding: 10px 15px;
}

.faq-suggestions-title {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.faq-suggestions-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.faq-suggestion-btn {
  border-radius: 999px;
}

.typing-indicator span {
  display: inline-block;
  width: 6px;
  height: 6px;
  background-color: #909399;
  border-radius: 50%;
  margin: 0 2px;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* 功能区布局 */
.reservation-card {
  height: auto;
  margin-bottom: 18px;
  border-radius: 16px;
}

.reservation-card .el-card__body {
  padding: 14px 18px;
}


.reservation-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reservation-item {
  border: 1px solid #e9eee8;
  border-radius: 12px;
  padding: 12px 14px;
  background: linear-gradient(135deg, #fff, #fafcf9);
}

.reservation-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  margin-bottom: 8px;
}

.reservation-time {
  font-weight: 400;
  font-size: 12px;
  color: #909399;
}

.reservation-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 13px;
  color: #606266;
}

.reservation-comments {
  margin-top: 8px;
  font-size: 13px;
  color: #303133;
  background: #f7f7f7;
  border-radius: 8px;
  padding: 8px 10px;
}


.menu-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.menu-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 17px;
  scrollbar-width: thin;
  scrollbar-color: #d5dfd6 transparent;
}

.menu-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 14px;
}

.menu-item-card {
  background: linear-gradient(160deg, #fff, #fbfcfa);
  border: 1px solid #e8eee7;
  border-radius: 14px;
  padding: 15px;
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}

.menu-item-card:hover {
  border-color: #bfd5c3;
  box-shadow: 0 10px 22px rgba(39, 79, 52, .09);
  transform: translateY(-3px);
}

.menu-item-card.highlighted {
  border-color: #F56C6C;
  background-color: #fef0f0;
}

.menu-item-card.flashing {
  animation: flashPulse 0.9s ease-in-out 1;
}

@keyframes flashPulse {
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 rgba(245, 108, 108, 0);
  }
  35% {
    transform: scale(1.02);
    box-shadow: 0 0 0 8px rgba(245, 108, 108, 0.18);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 rgba(245, 108, 108, 0);
  }
}

.item-badge {
  position: absolute;
  top: 0;
  right: 0;
  background: #F56C6C;
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-bottom-left-radius: 8px;
}

.item-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-weight: 600;
}

.item-price {
  color: #b66b3a;
  font-size: 14px;
  white-space: nowrap;
}

.item-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}

.item-desc {
  font-size: 12px;
  color: #909399;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 900px) {
  #app { height: auto; min-height: 100vh; }
  .main-container { height: auto; min-height: 100vh; }
  .main-content { overflow: visible; padding: 16px; }
  .el-row { height: auto; }
  .el-col { height: auto; margin-bottom: 16px; }
  .chat-card { height: min(72vh, 720px); min-height: 480px; }
  .reservation-card { margin-bottom: 16px; }
  .menu-card { height: 65vh; min-height: 420px; }
  .header { padding: 0 18px; }
}

@media (max-width: 560px) {
  .header { height: 66px; flex-basis: 66px; }
  .header-status { font-size: 0; }
  .header-status .status-dot { width: 9px; height: 9px; }
  .main-content { padding: 12px; }
  .chat-card { min-height: 420px; }
  .menu-grid { grid-template-columns: 1fr; }
  .menu-card { height: 62vh; }
  .welcome-message h2 { font-size: 19px; }
}

</style>
