let chatData = {}
let chatList = []
let filteredChatList = []
let rootFolderPath = ""
let groupParticipants = {}
let currentGroupChat = null
let groupNames = []
let filteredGroupNames = []
let callLogs = []
let filteredCallLogs = []
let matrixAnimation = null
let currentSelectedChat = null // NEW: Track currently selected chat

// NEW: Media viewer variables
let currentMediaFiles = []
let filteredMediaFiles = []
const selectedMediaFiles = new Set()
let currentMediaFilter = "all"

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

    ctx.fillStyle = "#00ff41"
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

function showHackerLoading(message = "Analyzing WhatsApp Database") {
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

  // NEW: Hide media viewer panel
  const mediaViewerPanel = document.getElementById("media-viewer-panel")
  if (mediaViewerPanel) {
    mediaViewerPanel.style.display = "none"
  }

  // NEW: Hide chat call logs button and popup
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
  if (chatStatus) chatStatus.textContent = status || "Click on a chat to view messages"

  if (chatName && chatAvatarHeader) {
    chatAvatarHeader.style.display = "flex"
    chatAvatarHeader.textContent = getInitials(chatName)
  } else if (chatAvatarHeader) {
    chatAvatarHeader.style.display = "none"
  }
}

// NEW: Toggle chat-specific call logs popup
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

// NEW: Show call logs for specific chat
function showChatCallLogs(chatName) {
  const popup = document.getElementById("chat-call-logs-popup")
  const chatNameElem = document.getElementById("popup-chat-name")
  const callLogsList = document.getElementById("chat-call-logs-list")
  const noCallLogs = document.getElementById("no-call-logs")

  chatNameElem.textContent = `${chatName} - Call History`

  // Filter call logs for this specific chat
  const chatCallLogs = callLogs.filter((call) => {
    const contactName = call.contact_name || ""
    const contactNumber = call.contact_number || ""

    // Check if the call is from/to this chat
    return (
      chatName.includes(contactName) ||
      chatName.includes(contactNumber) ||
      contactName.includes(chatName.split(" (")[0]) || // Handle "Name (number)" format
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

// NEW: Media viewer functions
function loadMediaViewer() {
  if (!rootFolderPath) {
    showError("Please enter a folder path first")
    return
  }

  showHackerLoading("Scanning Media Files...")

  fetch("/view-media", {
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
        currentMediaFiles = result.media_files || []
        filteredMediaFiles = [...currentMediaFiles]
        selectedMediaFiles.clear()

        setTimeout(() => {
          hideHackerLoading()
          document.getElementById("input-overlay").style.display = "none"
          showMediaViewer(result)
          document.getElementById("back-btn").style.display = "inline-block"
          setSidebarVisibility(false)
          hideError()
        }, 2000)
      }
    })
    .catch((err) => {
      hideHackerLoading()
      showError("Error: " + err)
    })
}

function showMediaViewer(data) {
  // Hide other panels
  infoSectionElem.style.display = "none"
  messagesElem.style.display = "none"
  groupsInfoPanel.style.display = "none"
  callLogsPanel.style.display = "none"

  // Show media viewer panel
  const mediaViewerPanel = document.getElementById("media-viewer-panel")
  if (!mediaViewerPanel) {
    // Create media viewer panel if it doesn't exist
    createMediaViewerPanel()
  }

  document.getElementById("media-viewer-panel").style.display = "flex"

  displayMediaStats(data.statistics)
  displayMediaFiles()
  updateSelectedCount()
}

function hideMediaViewer() {
  const mediaViewerPanel = document.getElementById("media-viewer-panel")
  if (mediaViewerPanel) {
    mediaViewerPanel.style.display = "none"
  }
  infoSectionElem.style.display = "flex"
}

function createMediaViewerPanel() {
  const mediaViewerHTML = `
    <div id="media-viewer-panel" style="display:none;">
      <div class="panel-header">
        <button class="back-btn" onclick="goBackToMenu()">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
          </svg>
          Back
        </button>
        <h2 class="panel-title">Media Files</h2>
      </div>
      <div class="panel-content">
        <div class="search-container">
          <div class="search-input-wrapper">
            <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L23.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
            </svg>
            <input type="text" id="media-search" placeholder="Search media files..." oninput="filterMediaFiles()">
          </div>
        </div>
        
        <div class="media-stats" id="media-stats"></div>
        
        <div class="media-controls">
          <div class="media-filter-buttons">
            <button class="filter-btn active" data-type="all" onclick="filterMediaByType('all')">All</button>
            <button class="filter-btn" data-type="Image" onclick="filterMediaByType('Image')">Images</button>
            <button class="filter-btn" data-type="Video" onclick="filterMediaByType('Video')">Videos</button>
            <button class="filter-btn" data-type="Audio" onclick="filterMediaByType('Audio')">Audio</button>
            <button class="filter-btn" data-type="Document" onclick="filterMediaByType('Document')">Documents</button>
          </div>
          
          <div class="media-actions">
            <button class="select-all-btn" onclick="toggleSelectAll()">Select All</button>
            <div class="selected-count" id="selected-count">0 selected</div>
            <button class="download-selected-btn" id="download-selected-btn" onclick="downloadSelectedMedia()" disabled>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z"/>
              </svg>
              Download Selected
            </button>
          </div>
        </div>
        
        <div id="media-list"></div>
      </div>
    </div>
  `

  document.getElementById("main").insertAdjacentHTML("beforeend", mediaViewerHTML)
}

function displayMediaStats(stats) {
  const mediaStats = document.getElementById("media-stats")

  const typeStats = Object.entries(stats.types)
    .map(([type, count]) => {
      const typeClass = type.toLowerCase().replace(" ", "")
      return `
        <div class="media-stat-item ${typeClass}">
          <span class="stat-number">${count}</span>
          <span class="stat-label">${type}</span>
        </div>
      `
    })
    .join("")

  mediaStats.innerHTML = `
    <div class="media-stat-item">
      <span class="stat-number">${stats.total_files}</span>
      <span class="stat-label">Total Files</span>
    </div>
    <div class="media-stat-item">
      <span class="stat-number">${stats.total_size_formatted}</span>
      <span class="stat-label">Total Size</span>
    </div>
    ${typeStats}
  `
}

function displayMediaFiles() {
  const mediaList = document.getElementById("media-list")
  const mediaGrid = document.createElement("div")
  mediaGrid.className = "media-grid"

  mediaList.innerHTML = ""

  if (filteredMediaFiles.length === 0) {
    mediaList.innerHTML = '<div style="padding: 40px; text-align: center; color: #8696a0;">No media files found</div>'
    return
  }

  filteredMediaFiles.forEach((media, index) => {
    const mediaItem = document.createElement("div")
    mediaItem.className = "media-item"
    mediaItem.dataset.index = index

    if (selectedMediaFiles.has(index)) {
      mediaItem.classList.add("selected")
    }

    const typeIcon = getMediaTypeIcon(media.type)
    const typeClass = media.type.toLowerCase().replace(" ", "")

    mediaItem.innerHTML = `
      <div class="media-item-header">
        <div class="media-type-icon ${typeClass}">
          ${typeIcon}
        </div>
        <div class="media-checkbox ${selectedMediaFiles.has(index) ? "checked" : ""}" onclick="toggleMediaSelection(${index})"></div>
      </div>
      <div class="media-filename">${media.filename}</div>
      <div class="media-details">
        <span class="media-size">${media.size_formatted}</span>
        <span class="media-date">${media.date_formatted}</span>
      </div>
      <div class="media-actions-row">
        <button class="download-single-btn" onclick="downloadSingleMedia(${index})">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
            <path d="M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z"/>
          </svg>
          Download
        </button>
      </div>
    `

    mediaGrid.appendChild(mediaItem)
  })

  mediaList.appendChild(mediaGrid)
  updateSelectedCount()
}

function getMediaTypeIcon(type) {
  const icons = {
    Image: "🖼️",
    Video: "🎥",
    Audio: "🎵",
    Document: "📄",
    Archive: "📦",
    Text: "📝",
    Contact: "👤",
    App: "📱",
  }
  return icons[type] || "📄"
}

function filterMediaByType(type) {
  currentMediaFilter = type

  // Update filter button styling
  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.classList.remove("active")
  })
  document.querySelector(`[data-type="${type}"]`).classList.add("active")

  // Filter media files
  if (type === "all") {
    filteredMediaFiles = [...currentMediaFiles]
  } else {
    filteredMediaFiles = currentMediaFiles.filter((media) => media.type === type)
  }

  // Clear selections when filtering
  selectedMediaFiles.clear()

  displayMediaFiles()
}

function filterMediaFiles() {
  const searchTerm = document.getElementById("media-search").value.toLowerCase()

  if (currentMediaFilter === "all") {
    filteredMediaFiles = currentMediaFiles.filter((media) => media.filename.toLowerCase().includes(searchTerm))
  } else {
    filteredMediaFiles = currentMediaFiles.filter(
      (media) => media.type === currentMediaFilter && media.filename.toLowerCase().includes(searchTerm),
    )
  }

  displayMediaFiles()
}

function toggleMediaSelection(index) {
  if (selectedMediaFiles.has(index)) {
    selectedMediaFiles.delete(index)
  } else {
    selectedMediaFiles.add(index)
  }

  // Update UI
  const mediaItem = document.querySelector(`[data-index="${index}"]`)
  const checkbox = mediaItem.querySelector(".media-checkbox")

  if (selectedMediaFiles.has(index)) {
    mediaItem.classList.add("selected")
    checkbox.classList.add("checked")
  } else {
    mediaItem.classList.remove("selected")
    checkbox.classList.remove("checked")
  }

  updateSelectedCount()
}

function toggleSelectAll() {
  const allSelected = selectedMediaFiles.size === filteredMediaFiles.length

  if (allSelected) {
    // Deselect all
    selectedMediaFiles.clear()
  } else {
    // Select all visible files
    filteredMediaFiles.forEach((_, index) => {
      selectedMediaFiles.add(index)
    })
  }

  displayMediaFiles()
}

function updateSelectedCount() {
  const selectedCount = document.getElementById("selected-count")
  const downloadBtn = document.getElementById("download-selected-btn")

  if (selectedCount) {
    selectedCount.textContent = `${selectedMediaFiles.size} selected`
  }
  if (downloadBtn) {
    downloadBtn.disabled = selectedMediaFiles.size === 0
  }
}

function downloadSelectedMedia() {
  if (selectedMediaFiles.size === 0) {
    showError("No media files selected")
    return
  }

  const selectedFiles = Array.from(selectedMediaFiles).map((index) => filteredMediaFiles[index])

  fetch("/download-media", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      root_folder: rootFolderPath,
      media_files: selectedFiles,
    }),
  })
    .then((response) => {
      if (response.ok) {
        return response.blob()
      }
      throw new Error("Download failed")
    })
    .then((blob) => {
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `whatsapp_media_${new Date().toISOString().slice(0, 10)}.zip`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    })
    .catch((error) => {
      console.error("Error:", error)
      showError("Failed to download media files")
    })
}

function downloadSingleMedia(index) {
  const mediaFile = filteredMediaFiles[index]

  fetch("/download-single-media", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      root_folder: rootFolderPath,
      media_file: mediaFile,
    }),
  })
    .then((response) => {
      if (response.ok) {
        return response.blob()
      }
      throw new Error("Download failed")
    })
    .then((blob) => {
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = mediaFile.filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    })
    .catch((error) => {
      console.error("Error:", error)
      showError("Failed to download media file")
    })
}

function loadChats() {
  showHackerLoading("Infiltrating WhatsApp Database...")
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
          updateMainHeader("WhatsApp Web", `${chatList.length} chats loaded`)
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
      const filename = fmt === "html" ? "contacts.html" : "contacts.json"
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
    listElem.innerHTML = "<div style='color:#8696a0; text-align: center; padding: 20px;'>No call logs found.</div>"
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
      const filename = fmt === "html" ? "call_logs.html" : "call_logs.json"
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
      document.getElementById("group-participants-panel").style.display = "none"
      renderGroupsList()
      setSidebarVisibility(false)
      backBtn.style.display = "none"
      backBtnCalls.style.display = "none"
      backBtnGroups.style.display = "inline-block"
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
        groupParticipants = result.group_participants || {}
        groupNames = Object.keys(groupParticipants).sort((a, b) => a.localeCompare(b))
        filteredGroupNames = groupNames.slice()

        setTimeout(() => {
          hideHackerLoading()
          document.getElementById("input-overlay").style.display = "none"
          groupsInfoPanel.style.display = "flex"
          updateMainHeader("", "")
          messagesElem.innerHTML = ""
          infoSectionElem.style.display = "none"
          callLogsPanel.style.display = "none"
          document.getElementById("group-participants-panel").style.display = "none"
          renderGroupsList()
          setSidebarVisibility(false)
          backBtn.style.display = "none"
          backBtnCalls.style.display = "none"
          backBtnGroups.style.display = "inline-block"
          hideError()
        }, 1500)
      }
    })
    .catch((err) => {
      hideHackerLoading()
      showError("Error: " + err)
    })
}

function renderGroupsList() {
  const listElem = document.getElementById("groups-list")
  listElem.innerHTML = ""
  if (filteredGroupNames.length === 0) {
    listElem.innerHTML = "<div style='color:#8696a0; text-align: center; padding: 20px;'>No groups found.</div>"
    return
  }
  filteredGroupNames.forEach((group) => {
    const div = document.createElement("div")
    div.className = "group-list-item"
    div.textContent = group
    div.onclick = () => showGroupParticipants(group)
    listElem.appendChild(div)
  })
}

document.getElementById("group-list-search").addEventListener("input", (e) => {
  const query = e.target.value.trim().toLowerCase()
  if (!query) {
    filteredGroupNames = groupNames.slice()
  } else {
    filteredGroupNames = groupNames.filter((name) => name.toLowerCase().includes(query))
  }
  renderGroupsList()
})

function showGroupParticipants(groupName) {
  currentGroupChat = groupName
  document.getElementById("group-participants-title").textContent = groupName
  document.getElementById("group-participants-panel").style.display = "block"

  document.querySelectorAll(".group-list-item").forEach((item) => item.classList.remove("active"))
  event.target.classList.add("active")

  renderGroupParticipants()
}

function closeParticipantsPanel() {
  document.getElementById("group-participants-panel").style.display = "none"
  document.querySelectorAll(".group-list-item").forEach((item) => item.classList.remove("active"))
}

function renderGroupParticipants() {
  const listElem = document.getElementById("group-participant-list")
  listElem.innerHTML = ""
  if (!currentGroupChat || !groupParticipants[currentGroupChat]) {
    listElem.innerHTML = "<div style='color:#8696a0; text-align: center; padding: 20px;'>No participants found.</div>"
    return
  }
  const query = document.getElementById("group-participant-search").value.trim().toLowerCase()
  let participants = groupParticipants[currentGroupChat]
  if (query) {
    participants = participants.filter(
      (p) => (p.number && p.number.includes(query)) || (p.name && p.name.toLowerCase().includes(query)),
    )
  }
  if (participants.length === 0) {
    listElem.innerHTML = "<div style='color:#8696a0; text-align: center; padding: 20px;'>No match found.</div>"
  } else {
    participants.forEach((p) => {
      let label = p.number
      if (p.name && p.name !== p.number) label += " (" + p.name + ")"
      const row = document.createElement("div")
      row.className = "group-participant-row"
      row.textContent = label
      listElem.appendChild(row)
    })
  }
}

document.getElementById("group-participant-search").addEventListener("input", renderGroupParticipants)

function downloadParticipants(fmt) {
  if (!currentGroupChat || !groupParticipants[currentGroupChat]) return
  const participants = groupParticipants[currentGroupChat]
  if (fmt === "json") {
    const blob = new Blob([JSON.stringify(participants, null, 2)], { type: "application/json" })
    const a = document.createElement("a")
    a.href = URL.createObjectURL(blob)
    a.download = `${currentGroupChat.replace(/[^a-zA-Z0-9]/g, "_")}_participants.json`
    document.body.appendChild(a)
    a.click()
    a.remove()
  } else if (fmt === "html") {
    let html = `
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <title>Group Participants</title>
        <style>
            body { background: #181f23; color: #e9edef; font-family: 'Segoe UI', sans-serif; }
            h2 { color: #00a884; }
            .participant { margin-bottom: 10px; }
        </style>
        </head>
        <body>
        <h2>Participants of ${currentGroupChat}</h2>
        <ul>
        `
    participants.forEach((p) => {
      let label = p.number
      if (p.name && p.name !== p.number) label += " (" + p.name + ")"
      html += `<li class="participant">${label}</li>`
    })
    html += `</ul></body></html>`
    const blob = new Blob([html], { type: "text/html" })
    const a = document.createElement("a")
    a.href = URL.createObjectURL(blob)
    a.download = `${currentGroupChat.replace(/[^a-zA-Z0-9]/g, "_")}_participants.html`
    document.body.appendChild(a)
    a.click()
    a.remove()
  }
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

    // Get last message preview and time
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
          hasCallLog = lastMsg[5] // is_call flag

          // Format time
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

    // Truncate long messages
    if (lastMessage.length > 50) {
      lastMessage = lastMessage.substring(0, 50) + "..."
    }

    div.innerHTML = `
      <div class="chat-avatar">${getInitials(chat.display)}</div>
      <div class="chat-info">
        <div class="chat-name">${chat.display}</div>
        <div class="chat-preview">
          ${hasCallLog ? '<span style="color: #8696a0;">📞</span>' : ""}
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

  // NEW: Hide media viewer panel
  const mediaViewerPanel = document.getElementById("media-viewer-panel")
  if (mediaViewerPanel) {
    mediaViewerPanel.style.display = "none"
  }

  // NEW: Hide call logs popup when switching chats
  document.getElementById("chat-call-logs-popup").style.display = "none"

  document.querySelectorAll(".chat-item").forEach((e) => e.classList.remove("active"))
  if (elem) elem.classList.add("active")

  // NEW: Set current selected chat and show call logs button
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

// In the renderMessages function, fix the call message rendering logic
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
        // Handle both old format (6 elements) and new format (7 elements with call_info)
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

        // Add sender label for group messages
        if (sender_name && sender_name !== chat && sender_name !== "You" && !is_call) {
          const senderDiv = document.createElement("span")
          senderDiv.className = "sender-label"
          senderDiv.textContent = sender_name
          bubble.appendChild(senderDiv)
        }

        // Render call message with WhatsApp-style design
        if (is_call && call_info) {
          console.log("Rendering call message:", call_info) // Debug log

          const callContainer = document.createElement("div")
          callContainer.style.display = "flex"
          callContainer.style.alignItems = "center"
          callContainer.style.gap = "12px"
          callContainer.style.width = "100%"

          // Call icon container
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

          // Call content
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
        }
        // Render regular text message
        else if (msg && msg.trim() !== "") {
          const msgText = document.createElement("div")
          msgText.textContent = msg
          bubble.appendChild(msgText)
        }

        // Handle media attachments
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
            link.style.color = "#53bdeb"
            link.style.textDecoration = "none"
            link.textContent = "📎 " + media_url.split("/").pop()
            bubble.appendChild(link)
          }
        }

        // Add timestamp
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

  // NEW: Hide call logs button and popup when searching
  document.getElementById("chat-call-logs-btn").style.display = "none"
  document.getElementById("chat-call-logs-popup").style.display = "none"
  currentSelectedChat = null

  updateMainHeader("WhatsApp Web", `${filteredChatList.length} chats found`)
  backBtn.style.display = "inline-block"
})

function downloadAll(fmt) {
  showHackerLoading("Compiling All Data...")

  const estimatedTime = chatList.length > 50 ? "2-5 minutes" : "30-60 seconds"
  const loadingText = hackerLoading.querySelector(".loading-text")
  if (loadingText) {
    loadingText.textContent = `Processing ${chatList.length || "your"} chats... Est. ${estimatedTime}`
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
      const filename = fmt === "html" ? "whatsapp_complete_export.html" : "whatsapp_complete_export.json"
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

      // NEW: Close popup on Escape key
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

  // NEW: Close popup when clicking outside
  document.addEventListener("click", (e) => {
    const popup = document.getElementById("chat-call-logs-popup")
    const callLogsBtn = document.getElementById("chat-call-logs-btn")

    if (popup.style.display === "block" && !popup.contains(e.target) && !callLogsBtn.contains(e.target)) {
      popup.style.display = "none"
    }
  })
})
