let chatData = {}
let chatList = []
let filteredChatList = []
let rootFolderPath = ""
let groupParticipants = {}
const currentGroupChat = null
let groupNames = []
let filteredGroupNames = []
let callLogs = []
let filteredCallLogs = []
let matrixAnimation = null
let currentSelectedChat = null

const chatListElem = document.getElementById("chat-list")
const mainHeaderElem = document.getElementById("main-header")
const messagesElem = document.getElementById("messages")
const infoSectionElem = document.getElementById("info-section")
const backBtn = document.getElementById("back-btn")
const groupsInfoPanel = document.getElementById("groups-info-panel")
const backBtnGroups = document.getElementById("back-btn-groups")
const callLogsPanel = document.getElementById("call-logs-panel")
const backBtnCalls = document.getElementById("back-btn-calls")
const hackerLoading = document.getElementById("hacker-loading")

function setSidebarVisibility(show) {
  const container = document.getElementById("container")
  if (show) {
    container.classList.remove("hide-sidebar")
  } else {
    container.classList.add("hide-sidebar")
  }
}

function initMatrixEffect() {
  const canvas = document.getElementById("matrix-canvas")
  const ctx = canvas.getContext("2d")

  canvas.width = window.innerWidth
  canvas.height = window.innerHeight

  const katakana =
    "アァカサタナハマヤャラワガザダバパイィキシチニヒミリヰギジヂビピウゥクスツヌフムユュルグズブヅプエェケセテネヘメレヱゲゼデベペオォコソトノホモヨョロヲゴゾドボポヴッン"
  const latin = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
  const nums = "0123456789"
  const alphabet = katakana + latin + nums

  const fontSize = 16
  const columns = canvas.width / fontSize

  const rainDrops = []
  for (let x = 0; x < columns; x++) {
    rainDrops[x] = 1
  }

  function draw() {
    ctx.fillStyle = "rgba(0, 0, 0, 0.05)"
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    ctx.fillStyle = "#3a76f0"
    ctx.font = fontSize + "px monospace"

    for (let i = 0; i < rainDrops.length; i++) {
      const text = alphabet.charAt(Math.floor(Math.random() * alphabet.length))
      ctx.fillText(text, i * fontSize, rainDrops[i] * fontSize)

      if (rainDrops[i] * fontSize > canvas.height && Math.random() > 0.975) {
        rainDrops[i] = 0
      }
      rainDrops[i]++
    }
  }

  return setInterval(draw, 35)
}

function showHackerLoading(message = "Analyzing Signal Database") {
  const loadingText = hackerLoading.querySelector(".loading-text")
  if (loadingText) {
    loadingText.textContent = message
  }
  hackerLoading.style.display = "flex"

  if (matrixAnimation) {
    clearInterval(matrixAnimation)
  }
  setTimeout(() => {
    matrixAnimation = initMatrixEffect()
  }, 100)

  const progressBar = hackerLoading.querySelector(".loading-progress")
  if (progressBar) {
    progressBar.style.animation = "none"
    progressBar.offsetHeight
    progressBar.style.animation = "loadingProgress 3s ease-in-out infinite, gradientShift 2s linear infinite"
  }
}

function hideHackerLoading() {
  hackerLoading.style.display = "none"
  if (matrixAnimation) {
    clearInterval(matrixAnimation)
    matrixAnimation = null
  }
}

function showError(message) {
  const errorElem = document.getElementById("input-error")
  errorElem.textContent = message
  errorElem.style.display = "block"
}

function hideError() {
  const errorElem = document.getElementById("input-error")
  errorElem.style.display = "none"
}

function onPathSubmit() {
  rootFolderPath = document.getElementById("root-folder-input").value.trim()
  if (!rootFolderPath) {
    showError("Please enter a folder path.")
    return
  }
  hideError()
  document.getElementById("after-path-options").style.display = "block"
  document.getElementById("submit-path-btn").style.display = "none"
  document.getElementById("root-folder-input").disabled = true
}

function goBackToMenu() {
  document.getElementById("input-overlay").style.display = "flex"
  infoSectionElem.style.display = "none"
  messagesElem.style.display = "none"
  groupsInfoPanel.style.display = "none"
  callLogsPanel.style.display = "none"
  backBtn.style.display = "none"

  document.getElementById("chat-call-logs-btn").style.display = "none"
  document.getElementById("chat-call-logs-popup").style.display = "none"
  currentSelectedChat = null

  updateMainHeader("", "")
  setSidebarVisibility(true)
  hideHackerLoading()
  document.querySelectorAll(".chat-item").forEach((e) => e.classList.remove("active"))
}

function updateMainHeader(chatName, status = "") {
  const chatNameHeader = document.querySelector(".chat-name-header")
  const chatStatus = document.querySelector(".chat-status")
  const chatAvatarHeader = document.getElementById("chat-avatar-header")

  if (chatNameHeader) chatNameHeader.textContent = chatName
  if (chatStatus) chatStatus.textContent = status || "Click on a conversation to view messages"

  if (chatName && chatAvatarHeader) {
    chatAvatarHeader.style.display = "flex"
    chatAvatarHeader.textContent = getInitials(chatName)
  } else if (chatAvatarHeader) {
    chatAvatarHeader.style.display = "none"
  }
}

function toggleChatCallLogs() {
  const popup = document.getElementById("chat-call-logs-popup")
  const isVisible = popup.style.display === "block"

  if (isVisible) {
    popup.style.display = "none"
  } else {
    if (currentSelectedChat) {
      showChatCallLogs(currentSelectedChat)
      popup.style.display = "block"
    }
  }
}

function showChatCallLogs(chatName) {
  const popup = document.getElementById("chat-call-logs-popup")
  const chatNameElem = document.getElementById("popup-chat-name")
  const callLogsList = document.getElementById("chat-call-logs-list")
  const noCallLogs = document.getElementById("no-call-logs")

  chatNameElem.textContent = `${chatName} - Call History`

  const chatCallLogs = callLogs.filter((call) => {
    const contactName = call.contact_name || ""
    const contactNumber = call.contact_number || ""

    return (
      chatName.includes(contactName) ||
      chatName.includes(contactNumber) ||
      contactName.includes(chatName.split(" (")[0]) ||
      contactNumber.includes(chatName)
    )
  })

  callLogsList.innerHTML = ""

  if (chatCallLogs.length === 0) {
    noCallLogs.style.display = "flex"
    callLogsList.style.display = "none"
  } else {
    noCallLogs.style.display = "none"
    callLogsList.style.display = "block"

    chatCallLogs.forEach((call) => {
      const div = document.createElement("div")
      div.className = "popup-call-item"

      let dateTime = "Unknown"
      try {
        const dt = new Date(call.timestamp)
        const now = new Date()
        const isToday = dt.toDateString() === now.toDateString()
        const isYesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000).toDateString() === dt.toDateString()

        if (isToday) {
          dateTime = dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        } else if (isYesterday) {
          dateTime = "Yesterday"
        } else {
          dateTime = dt.toLocaleDateString([], { month: "short", day: "numeric" })
        }
      } catch (e) {
        dateTime = call.timestamp.toString()
      }

      const callIcon = call.call_type === "Video Call" ? "📹" : "📞"
      const statusClass = call.call_status.toLowerCase()

      div.innerHTML = `
        <div class="popup-call-icon ${statusClass}">
          ${callIcon}
        </div>
        <div class="popup-call-info">
          <div class="popup-call-type">${call.call_type}</div>
          <div class="popup-call-details">
            <span>${call.call_status}</span>
            ${call.duration !== "0:00" ? `<span>• ${call.duration}</span>` : ""}
          </div>
        </div>
        <div class="popup-call-time">${dateTime}</div>
      `

      callLogsList.appendChild(div)
    })
  }
}

function loadChats() {
  showHackerLoading("Infiltrating Signal Database...")
  const submitBtn = document.getElementById("submit-path-btn")
  if (submitBtn) submitBtn.classList.add("loading")

  fetch("/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ root_folder: rootFolderPath }),
  })
    .then(async (response) => {
      let result
      try {
        result = await response.json()
      } catch (e) {
        const text = await response.text()
        hideHackerLoading()
        showError("Server error: " + text)
        return
      }
      if (result.error) {
        hideHackerLoading()
        showError(result.error)
      } else {
        chatData = result.messages
        chatList = result.chat_list
        filteredChatList = chatList.slice()
        groupParticipants = result.group_participants || {}
        callLogs = result.call_logs || []
        filteredCallLogs = callLogs.slice()
        groupNames = Object.keys(groupParticipants).sort((a, b) => a.localeCompare(b))
        filteredGroupNames = groupNames.slice()

        setTimeout(() => {
          hideHackerLoading()
          document.getElementById("input-overlay").style.display = "none"
          groupsInfoPanel.style.display = "none"
          callLogsPanel.style.display = "none"
          renderChatList()
          infoSectionElem.style.display = "flex"
          messagesElem.style.display = "none"
          updateMainHeader("Signal Desktop", `${chatList.length} conversations loaded`)
          backBtn.style.display = "inline-block"
          setSidebarVisibility(true)
          hideError()
        }, 2000)
      }
    })
    .catch((err) => {
      hideHackerLoading()
      showError("Error: " + err)
    })
    .finally(() => {
      if (submitBtn) submitBtn.classList.remove("loading")
    })
}

function downloadContacts(fmt) {
  showHackerLoading("Extracting Contact Database...")
  fetch("/contacts?format=" + fmt, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ root_folder: rootFolderPath }),
  })
    .then(async (response) => {
      if (!response.ok) {
        const text = await response.text()
        hideHackerLoading()
        showError("Error: " + text)
        return
      }
      const blob = await response.blob()
      const filename = fmt === "html" ? "signal_contacts.html" : "signal_contacts.json"
      const a = document.createElement("a")
      a.href = URL.createObjectURL(blob)
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      hideHackerLoading()
      hideError()
    })
    .catch((err) => {
      hideHackerLoading()
      showError("Error: " + err)
    })
}

function showCallLogs() {
  showHackerLoading("Analyzing Call History...")

  if (callLogs.length > 0) {
    setTimeout(() => {
      hideHackerLoading()
      document.getElementById("input-overlay").style.display = "none"
      callLogsPanel.style.display = "flex"
      updateMainHeader("", "")
      messagesElem.innerHTML = ""
      infoSectionElem.style.display = "none"
      groupsInfoPanel.style.display = "none"
      renderCallLogs()
      setSidebarVisibility(false)
      backBtn.style.display = "none"
      backBtnGroups.style.display = "none"
      backBtnCalls.style.display = "inline-block"
      hideError()
    }, 1500)
    return
  }

  fetch("/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ root_folder: rootFolderPath }),
  })
    .then(async (response) => {
      let result
      try {
        result = await response.json()
      } catch (e) {
        const text = await response.text()
        hideHackerLoading()
        showError("Server error: " + text)
        return
      }
      if (result.error) {
        hideHackerLoading()
        showError(result.error)
      } else {
        callLogs = result.call_logs || []
        filteredCallLogs = callLogs.slice()

        setTimeout(() => {
          hideHackerLoading()
          document.getElementById("input-overlay").style.display = "none"
          callLogsPanel.style.display = "flex"
          updateMainHeader("", "")
          messagesElem.innerHTML = ""
          infoSectionElem.style.display = "none"
          groupsInfoPanel.style.display = "none"
          renderCallLogs()
          setSidebarVisibility(false)
          backBtn.style.display = "none"
          backBtnGroups.style.display = "none"
          backBtnCalls.style.display = "inline-block"
          hideError()
        }, 1500)
      }
    })
    .catch((err) => {
      hideHackerLoading()
      showError("Error: " + err)
    })
}

function renderCallLogs() {
  const listElem = document.getElementById("call-logs-list")
  listElem.innerHTML = ""

  updateCallLogsStats()

  if (filteredCallLogs.length === 0) {
    listElem.innerHTML = "<div style='color:#9ca4ab; text-align: center; padding: 20px;'>No call logs found.</div>"
    return
  }

  filteredCallLogs.forEach((call) => {
    const div = document.createElement("div")
    div.className = "call-log-item"

    let dateTime = "Unknown"
    try {
      const dt = new Date(call.timestamp)
      dateTime = dt.toLocaleString()
    } catch (e) {
      dateTime = call.timestamp.toString()
    }

    const callIcon = call.call_type === "Video Call" ? "📹" : "📞"
    const statusClass = call.call_status.toLowerCase()

    div.innerHTML = `
      <div class="call-icon ${statusClass}">
        ${callIcon}
      </div>
      <div class="call-info">
        <div class="call-contact">${call.contact_name}</div>
        <div class="call-details">
          <span>${call.call_status} ${call.call_type}</span>
          ${call.duration !== "0:00" ? `<span>• ${call.duration}</span>` : ""}
        </div>
      </div>
      <div class="call-time">${dateTime}</div>
    `

    listElem.appendChild(div)
  })
}

function updateCallLogsStats() {
  const totalCalls = callLogs.length
  const missedCalls = callLogs.filter((call) => call.call_status === "Missed").length
  const outgoingCalls = callLogs.filter((call) => call.call_status === "Outgoing").length
  const incomingCalls = callLogs.filter((call) => call.call_status === "Incoming").length

  document.getElementById("total-calls").textContent = totalCalls
  document.getElementById("missed-calls").textContent = missedCalls
  document.getElementById("outgoing-calls").textContent = outgoingCalls
  document.getElementById("incoming-calls").textContent = incomingCalls
}

document.getElementById("call-logs-search").addEventListener("input", (e) => {
  const query = e.target.value.trim().toLowerCase()
  if (!query) {
    filteredCallLogs = callLogs.slice()
  } else {
    filteredCallLogs = callLogs.filter(
      (call) =>
        call.contact_name.toLowerCase().includes(query) ||
        call.contact_number.includes(query) ||
        call.call_type.toLowerCase().includes(query) ||
        call.call_status.toLowerCase().includes(query),
    )
  }
  renderCallLogs()
})

function downloadCallLogs(fmt) {
  showHackerLoading("Exporting Call Logs...")
  fetch("/call-logs?format=" + fmt, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ root_folder: rootFolderPath }),
  })
    .then(async (response) => {
      if (!response.ok) {
        const text = await response.text()
        hideHackerLoading()
        showError("Error: " + text)
        return
      }
      const blob = await response.blob()
      const filename = fmt === "html" ? "signal_call_logs.html" : "signal_call_logs.json"
      const a = document.createElement("a")
      a.href = URL.createObjectURL(blob)
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      hideHackerLoading()
      hideError()
    })
    .catch((err) => {
      hideHackerLoading()
      showError("Error: " + err)
    })
}

function showGroupsInfo() {
  showHackerLoading("Analyzing Group Networks...")

  if (Object.keys(groupParticipants).length > 0) {
    setTimeout(() => {
      hideHackerLoading()
      document.getElementById("input-overlay").style.display = "none"
      groupsInfoPanel.style.display = "flex"
      updateMainHeader("", "")
      messagesElem.innerHTML = ""
      infoSectionElem.style.display = "none"
      callLogsPanel.style.display = "none"
      renderGroupsList()
      setSidebarVisibility(false)
      backBtn.style.display = "none"
      backBtnCalls.style.display = "none"
      backBtnGroups.style.display = "inline-block"
      hideError()
    }, 1500)
    return
  }

  // For Signal, we don't have detailed group participants, so show basic group info
  setTimeout(() => {
    hideHackerLoading()
    document.getElementById("input-overlay").style.display = "none"
    groupsInfoPanel.style.display = "flex"
    updateMainHeader("", "")
    messagesElem.innerHTML = ""
    infoSectionElem.style.display = "none"
    callLogsPanel.style.display = "none"
    renderGroupsList()
    setSidebarVisibility(false)
    backBtn.style.display = "none"
    backBtnCalls.style.display = "none"
    backBtnGroups.style.display = "inline-block"
    hideError()
  }, 1500)
}

function renderGroupsList() {
  const listElem = document.getElementById("groups-list")
  listElem.innerHTML = ""

  // Get group chats from chat list
  const groupChats = chatList.filter((chat) => chat.type === "group")

  if (groupChats.length === 0) {
    listElem.innerHTML = "<div style='color:#9ca4ab; text-align: center; padding: 20px;'>No groups found.</div>"
    return
  }

  groupChats.forEach((group) => {
    const div = document.createElement("div")
    div.className = "group-list-item"
    div.textContent = group.display
    listElem.appendChild(div)
  })
}

function getInitials(name) {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2)
}

function renderChatList() {
  chatListElem.innerHTML = ""
  const filtered = filteredChatList.filter((chat) => !(chat.display && chat.display.endsWith("@lid")))
  const contacts = filtered.filter((c) => c.type === "contact").sort((a, b) => a.sort_key.localeCompare(b.sort_key))
  const groups = filtered.filter((c) => c.type === "group").sort((a, b) => a.sort_key.localeCompare(b.sort_key))
  const numbers = filtered.filter((c) => c.type === "number").sort((a, b) => a.sort_key.localeCompare(b.sort_key))
  const sorted = [...contacts, ...numbers, ...groups]

  sorted.forEach((chat) => {
    const div = document.createElement("div")
    div.className = "chat-item"
    div.dataset.chat = chat.display

    const chatMessages = chatData[chat.display]
    let lastMessage = ""
    let lastTime = ""
    let hasCallLog = false

    if (chatMessages) {
      const dates = Object.keys(chatMessages).sort().reverse()
      if (dates.length > 0) {
        const lastDate = dates[0]
        const messages = chatMessages[lastDate]
        if (messages.length > 0) {
          const lastMsg = messages[messages.length - 1]
          lastMessage = lastMsg[1] || ""
          hasCallLog = lastMsg[5]

          try {
            const dt = new Date(lastMsg[0] * 1000)
            const now = new Date()
            const isToday = dt.toDateString() === now.toDateString()
            const isYesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000).toDateString() === dt.toDateString()

            if (isToday) {
              lastTime = dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
            } else if (isYesterday) {
              lastTime = "Yesterday"
            } else {
              lastTime = dt.toLocaleDateString([], { month: "short", day: "numeric" })
            }
          } catch (e) {
            lastTime = ""
          }
        }
      }
    }

    if (lastMessage.length > 50) {
      lastMessage = lastMessage.substring(0, 50) + "..."
    }

    div.innerHTML = `
      <div class="chat-avatar">${getInitials(chat.display)}</div>
      <div class="chat-info">
        <div class="chat-name">${chat.display}</div>
        <div class="chat-preview">
          ${hasCallLog ? '<span style="color: #9ca4ab;">📞</span>' : ""}
          ${lastMessage || "No messages"}
        </div>
      </div>
      <div class="chat-meta">
        <div class="chat-time">${lastTime}</div>
      </div>
    `

    div.onclick = () => selectChat(chat.display, div)
    chatListElem.appendChild(div)
  })
}

function selectChat(chat, elem) {
  groupsInfoPanel.style.display = "none"
  callLogsPanel.style.display = "none"

  document.getElementById("chat-call-logs-popup").style.display = "none"

  document.querySelectorAll(".chat-item").forEach((e) => e.classList.remove("active"))
  if (elem) elem.classList.add("active")

  currentSelectedChat = chat
  document.getElementById("chat-call-logs-btn").style.display = "inline-block"

  const messageCount = chatData[chat] ? Object.values(chatData[chat]).reduce((sum, msgs) => sum + msgs.length, 0) : 0
  updateMainHeader(chat, `${messageCount} messages`)

  infoSectionElem.style.display = "none"
  messagesElem.style.display = "flex"
  renderMessages(chat)
  backBtn.style.display = "inline-block"
  backBtnGroups.style.display = "none"
  backBtnCalls.style.display = "none"
  setSidebarVisibility(true)
}

function renderMessages(chat) {
  messagesElem.innerHTML = ""
  const chatObj = chatData[chat]
  if (!chatObj) return

  Object.keys(chatObj)
    .sort()
    .forEach((date) => {
      const dateLabel = document.createElement("div")
      dateLabel.className = "date-label"
      dateLabel.textContent = new Date(date).toLocaleDateString("en-US", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
      })
      messagesElem.appendChild(dateLabel)

      chatObj[date].forEach((msgArr) => {
        const [ts, msg, direction, sender_name, media_url, is_call, call_info] = msgArr
        const row = document.createElement("div")
        row.className = "message-row"
        const bubble = document.createElement("div")

        let bubbleClass = "bubble " + (direction === 1 ? "sent" : "received")
        if (is_call) {
          bubbleClass += " call"
          if (call_info && call_info.status === "Missed") {
            bubbleClass += " missed"
          }
        }
        bubble.className = bubbleClass

        if (sender_name && sender_name !== chat && sender_name !== "You" && !is_call) {
          const senderDiv = document.createElement("span")
          senderDiv.className = "sender-label"
          senderDiv.textContent = sender_name
          bubble.appendChild(senderDiv)
        }

        if (is_call && call_info) {
          const callContainer = document.createElement("div")
          callContainer.style.display = "flex"
          callContainer.style.alignItems = "center"
          callContainer.style.gap = "12px"
          callContainer.style.width = "100%"

          const iconContainer = document.createElement("div")
          iconContainer.className = "call-icon-container"

          if (call_info.status === "Missed") {
            iconContainer.className += " missed-call"
            iconContainer.innerHTML = "📞"
          } else if (call_info.is_video) {
            iconContainer.className += " video-call"
            iconContainer.innerHTML = "📹"
          } else {
            iconContainer.className += " voice-call"
            iconContainer.innerHTML = "📞"
          }

          const callContent = document.createElement("div")
          callContent.className = "call-content"

          const callTitle = document.createElement("div")
          callTitle.className = "call-title"

          if (call_info.status === "Missed") {
            callTitle.textContent = call_info.is_video ? "Missed video call" : "Missed voice call"
          } else {
            callTitle.textContent = call_info.is_video ? "Video call" : "Voice call"
          }

          const callSubtitle = document.createElement("div")
          callSubtitle.className = "call-subtitle"

          if (call_info.status === "Missed") {
            callSubtitle.className += " missed"
            callSubtitle.textContent = "Tap to call back"
          } else if (call_info.duration && call_info.duration !== "0:00") {
            callSubtitle.className += " answered"
            callSubtitle.textContent = call_info.duration
          } else {
            callSubtitle.className += " answered"
            callSubtitle.textContent = "No answer"
          }

          callContent.appendChild(callTitle)
          callContent.appendChild(callSubtitle)

          callContainer.appendChild(iconContainer)
          callContainer.appendChild(callContent)
          bubble.appendChild(callContainer)
        } else if (msg && msg.trim() !== "") {
          const msgText = document.createElement("div")
          msgText.textContent = msg
          bubble.appendChild(msgText)
        }

        if (media_url) {
          const ext = media_url.split(".").pop().toLowerCase()
          if (["jpg", "jpeg", "png", "gif", "webp", "bmp"].includes(ext)) {
            const img = document.createElement("img")
            img.src = media_url
            img.style.maxWidth = "280px"
            img.style.display = "block"
            img.style.marginTop = "8px"
            img.alt = "Image"
            img.loading = "lazy"
            bubble.appendChild(img)
          } else if (["mp4", "webm", "ogg", "3gp"].includes(ext)) {
            const video = document.createElement("video")
            video.src = media_url
            video.controls = true
            video.style.maxWidth = "280px"
            video.style.display = "block"
            video.style.marginTop = "8px"
            video.preload = "metadata"
            bubble.appendChild(video)
          } else if (["mp3", "wav", "m4a", "aac", "opus", "amr", "oga", "ptt"].includes(ext)) {
            const audio = document.createElement("audio")
            audio.src = media_url
            audio.controls = true
            audio.style.display = "block"
            audio.style.marginTop = "8px"
            audio.preload = "metadata"
            bubble.appendChild(audio)
          } else {
            const link = document.createElement("a")
            link.href = media_url
            link.target = "_blank"
            link.style.display = "block"
            link.style.marginTop = "8px"
            link.style.color = "#3a76f0"
            link.style.textDecoration = "none"
            link.textContent = "📎 " + media_url.split("/").pop()
            bubble.appendChild(link)
          }
        }

        const time = document.createElement("span")
        time.className = "timestamp"
        const d = new Date(ts * 1000)
        time.textContent = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        bubble.appendChild(time)
        row.appendChild(bubble)
        messagesElem.appendChild(row)
      })
    })
  messagesElem.scrollTop = messagesElem.scrollHeight
}

document.getElementById("chat-search-input").addEventListener("input", (e) => {
  const query = e.target.value.trim().toLowerCase()
  if (!query) {
    filteredChatList = chatList.slice()
  } else {
    filteredChatList = chatList.filter((chat) => chat.display.toLowerCase().includes(query))
  }
  renderChatList()
  infoSectionElem.style.display = "flex"
  messagesElem.style.display = "none"

  document.getElementById("chat-call-logs-btn").style.display = "none"
  document.getElementById("chat-call-logs-popup").style.display = "none"
  currentSelectedChat = null

  updateMainHeader("Signal Desktop", `${filteredChatList.length} conversations found`)
  backBtn.style.display = "inline-block"
})

function downloadAll(fmt) {
  showHackerLoading("Compiling All Data...")

  const estimatedTime = chatList.length > 50 ? "2-5 minutes" : "30-60 seconds"
  const loadingText = hackerLoading.querySelector(".loading-text")
  if (loadingText) {
    loadingText.textContent = `Processing ${chatList.length || "your"} conversations... Est. ${estimatedTime}`
  }

  const timeoutDuration = chatList.length > 50 ? 300000 : 120000

  const timeoutId = setTimeout(() => {
    hideHackerLoading()
    showError(
      `Download timed out after ${timeoutDuration / 1000} seconds. Try using JSON format for large datasets, or contact support.`,
    )
  }, timeoutDuration)

  fetch("/download-all?format=" + fmt, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ root_folder: rootFolderPath }),
  })
    .then(async (response) => {
      clearTimeout(timeoutId)

      if (!response.ok) {
        const text = await response.text()
        hideHackerLoading()
        showError("Error: " + text)
        return
      }

      const blob = await response.blob()
      const filename = fmt === "html" ? "signal_complete_export.html" : "signal_complete_export.json"
      const a = document.createElement("a")
      a.href = URL.createObjectURL(blob)
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      hideHackerLoading()
      hideError()

      const successMsg = `✅ Export completed! Downloaded ${filename}`
      showError(successMsg)
      setTimeout(() => {
        hideError()
      }, 5000)
    })
    .catch((err) => {
      clearTimeout(timeoutId)
      hideHackerLoading()
      showError("Network error: " + err + ". Please check your connection and try again.")
    })
}

function loadMediaViewer() {
  showError("Media viewer not yet implemented for Signal data format.")
}

document.addEventListener("DOMContentLoaded", () => {
  const buttons = document.querySelectorAll("button")
  buttons.forEach((btn) => {
    btn.addEventListener("click", function () {
      if (!this.classList.contains("loading")) {
        this.style.transform = "scale(0.98)"
        setTimeout(() => {
          this.style.transform = ""
        }, 150)
      }
    })
  })

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const overlay = document.getElementById("input-overlay")
      const popup = document.getElementById("chat-call-logs-popup")

      if (popup.style.display === "block") {
        popup.style.display = "none"
        return
      }

      if (overlay.style.display !== "flex") {
        goBackToMenu()
      }
    }
  })

  const searchInputs = document.querySelectorAll('input[type="text"]')
  searchInputs.forEach((input) => {
    input.addEventListener("focus", function () {
      this.parentElement.style.transform = "scale(1.02)"
    })

    input.addEventListener("blur", function () {
      this.parentElement.style.transform = ""
    })
  })

  window.addEventListener("resize", () => {
    if (matrixAnimation && hackerLoading.style.display === "flex") {
      clearInterval(matrixAnimation)
      setTimeout(() => {
        matrixAnimation = initMatrixEffect()
      }, 100)
    }
  })

  document.addEventListener("click", (e) => {
    const popup = document.getElementById("chat-call-logs-popup")
    const callLogsBtn = document.getElementById("chat-call-logs-btn")

    if (popup.style.display === "block" && !popup.contains(e.target) && !callLogsBtn.contains(e.target)) {
      popup.style.display = "none"
    }
  })
})
