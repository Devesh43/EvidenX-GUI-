document.addEventListener("DOMContentLoaded", () => {
  const loadingIndicator = document.getElementById("loadingIndicator")
  const errorMessageDiv = document.getElementById("errorMessageDiv")
  const errorDetailsPre = document.getElementById("errorDetailsPre")
  const noDataMessage = document.getElementById("noDataMessage")
  const resultsContent = document.getElementById("resultsContent")

  // Summary Elements
  const summaryCaseNumber = document.getElementById("summaryCaseNumber")
  const summaryExaminer = document.getElementById("examinerName")
  const summaryEvidenceItem = document.getElementById("evidenceItem")
  const summaryInputPath = document.getElementById("summaryInputPath")
  const summaryTimestamp = document.getElementById("summaryTimestamp")
  const totalMedia = document.getElementById("totalMedia")
  const totalMessages = document.getElementById("totalMessages")
  const totalUsers = document.getElementById("totalUsers")
  const totalSessions = document.getElementById("totalSessions")
  const v5Status = document.getElementById("v5Status")
  const v7Status = document.getElementById("v7Status")

  let dataPollingInterval
  let extractionData = null
  let currentUserId = null // Store the current user's ID for message direction

  // Helper function to safely get nested properties
  function getNestedProperty(obj, path, defaultValue = "N/A") {
    return (
      path.split(".").reduce((acc, part) => (acc && acc[part] !== undefined ? acc[part] : undefined), obj) ||
      defaultValue
    )
  }

  // Function to populate summary details
  function populateSummary(data) {
    // Get case info from metadata
    const caseInfo = getNestedProperty(data, "metadata.case_info", {})
    const metadata = getNestedProperty(data, "metadata", {})

    summaryCaseNumber.textContent = caseInfo.case_number || "N/A"
    summaryExaminer.textContent = caseInfo.examiner || "N/A"
    summaryEvidenceItem.textContent = caseInfo.evidence_item || "N/A"
    summaryInputPath.textContent = metadata.input_path || "N/A"
    summaryTimestamp.textContent = metadata.timestamp || "N/A"

    // Get summary counts
    const summary = getNestedProperty(data, "summary", {})
    totalMedia.textContent = summary.total_media_count || 0
    totalMessages.textContent = summary.total_messages_count || 0
    totalUsers.textContent = summary.total_users_analyzed || 0
    totalSessions.textContent = summary.total_sessions_found || 0

    // Get extractor statuses
    v5Status.textContent = getNestedProperty(data, "v5_report.status", "Not Run")
    v7Status.textContent = getNestedProperty(data, "v7_report.status", "Not Run")

    // Extract current user ID for message direction
    currentUserId =
      getNestedProperty(data, "merged_files.session_ids.logged_in_user_id", null) ||
      getNestedProperty(data, "merged_files.logged_in_user_profile.logged_in_user.user_id", null)

    console.log("Current user ID identified:", currentUserId)
  }

  // Function to populate tab content
  function populateTabContent(tabName, data) {
    if (tabName === "overview") {
      return // Overview is handled separately
    }

    formatReadableData(tabName, data)
  }

  // Function to show tab content
  window.showTab = (tabName) => {
    // Hide all tab contents
    const tabContents = document.querySelectorAll(".tab-content")
    tabContents.forEach((content) => content.classList.remove("active"))

    // Remove active class from all tabs
    const tabs = document.querySelectorAll(".tab")
    tabs.forEach((tab) => tab.classList.remove("active"))

    // Show selected tab content
    const selectedTab = document.getElementById(tabName)
    if (selectedTab) {
      selectedTab.classList.add("active")
    }

    // Add active class to clicked tab
    event.target.classList.add("active")

    // Populate tab-specific content
    if (extractionData) {
      populateTabContent(tabName, extractionData)
    }
  }

  // Function to create summary cards for overview
  function createSummaryCards(data) {
    const summaryContainer = document.getElementById("summaryCards")
    if (!summaryContainer) return

    const cards = [
      {
        title: "Messages Found",
        value: data.summary?.total_messages_count || 0,
        icon: "💬",
        color: "#3b82f6",
      },
      {
        title: "Media Items",
        value: data.summary?.total_media_count || 0,
        icon: "📷",
        color: "#10b981",
      },
      {
        title: "Sessions Found",
        value: data.summary?.total_sessions_found || 0,
        icon: "🔑",
        color: "#f59e0b",
      },
      {
        title: "Users Analyzed",
        value: data.summary?.total_users_analyzed || 0,
        icon: "👤",
        color: "#8b5cf6",
      },
    ]

    summaryContainer.innerHTML = cards
      .map(
        (card) => `
      <div class="summary-card" style="border-left: 4px solid ${card.color}">
        <div class="summary-card-header">
          <span class="summary-icon">${card.icon}</span>
          <span class="summary-title">${card.title}</span>
        </div>
        <div class="summary-value" style="color: ${card.color}">${card.value}</div>
      </div>
    `,
      )
      .join("")
  }

  // Function to poll for extracted data
  async function pollExtractedData() {
    try {
      const response = await fetch("/get_extracted_data")
      const result = await response.json()

      if (result.status === "in_progress") {
        loadingIndicator.querySelector(".loading-text").textContent =
          result.message || "Extraction in progress... Please wait."
        // Continue showing loading indicator
      } else if (result.status === "success") {
        clearInterval(dataPollingInterval) // Stop polling
        loadingIndicator.classList.add("hidden") // Hide loading
        errorMessageDiv.classList.add("hidden") // Hide errors
        noDataMessage.classList.add("hidden") // Hide no data message
        resultsContent.classList.remove("hidden") // Show results

        const data = result.data
        extractionData = data // Store globally

        if (data && Object.keys(data).length > 0) {
          populateSummary(data)
          createSummaryCards(data)

          // Initialize with overview tab
          populateTabContent("overview", data)
        } else {
          // If status is success but data is empty
          noDataMessage.classList.remove("hidden")
          console.warn("Extraction completed successfully, but no data was found in the report.")
        }
      } else if (result.status === "error") {
        clearInterval(dataPollingInterval)
        loadingIndicator.classList.add("hidden")
        errorMessageDiv.classList.remove("hidden")
        errorDetailsPre.textContent = result.message || "An unknown error occurred during extraction."
        console.error("Extraction failed:", result)
      } else if (result.status === "no_data") {
        // Initial state or no extraction started yet
        loadingIndicator.classList.remove("hidden") // Keep loading visible
        loadingIndicator.querySelector(".loading-text").textContent =
          result.message || "Waiting for extraction to start..."
      } else {
        // Unexpected status or no data (after a period of polling)
        clearInterval(dataPollingInterval)
        loadingIndicator.classList.add("hidden")
        noDataMessage.classList.remove("hidden")
        console.error("Failed to get structured data or unexpected status:", result)
      }
    } catch (error) {
      clearInterval(dataPollingInterval)
      loadingIndicator.classList.add("hidden")
      errorMessageDiv.classList.remove("hidden")
      errorDetailsPre.textContent = `Network error fetching data: ${error.message}`
      console.error("Error fetching extracted data:", error)
    }
  }

  // Start polling for data when the page loads
  dataPollingInterval = setInterval(pollExtractedData, 3000) // Poll every 3 seconds
  pollExtractedData() // Also attempt an immediate fetch

  // Function to format data in a readable way
  function formatReadableData(tabName, data) {
    const displayElement = document.getElementById(`${tabName}Display`)
    if (!displayElement) return

    let content = ""

    switch (tabName) {
      case "chats":
        content = formatChatsData(data.merged_files?.chats || [])
        break
      case "media":
        content = formatMediaData(data.merged_files?.media || [])
        break
      case "chat_media":
        content = formatChatMediaData(data.merged_files?.chat_media || [])
        break
      case "session_ids":
        content = formatSessionData(data.merged_files?.session_ids || {})
        break
      case "logged_in_user_profile":
        content = formatUserProfileData(data.merged_files?.logged_in_user_profile || {})
        break
      case "complete_folder_analysis":
        content = formatFolderAnalysisData(data.merged_files?.complete_folder_analysis || {})
        break
      case "extraction_report":
        content = formatExtractionReportData(data.merged_files?.extraction_report || {})
        break
      case "master":
        content = formatMasterData(data.merged_files?.master || {})
        break
      case "raw_json":
        content = `<pre class="json-code">${JSON.stringify(data, null, 2)}</pre>`
        break
      default:
        content = "<p>No data available</p>"
    }

    displayElement.innerHTML = content
  }

  // ENHANCED: Format chat messages with user IDs and proper sent/received positioning
  function formatChatsData(chats) {
    if (!chats || chats.length === 0) {
      return '<div class="no-data">No chat messages found</div>'
    }

    console.log("Original chats data:", chats)

    // Filter for chats with direct.db source
    const filteredChats = chats.filter((chat) => {
      const hasDirectDbSource = chat.source_file && chat.source_file.toLowerCase().includes("direct.db")
      const hasContent =
        chat.content || chat.text || chat.message || chat.data?.content || chat.data?.text || chat.data?.message
      return hasDirectDbSource && hasContent
    })

    console.log("Filtered chats (direct.db only):", filteredChats)

    if (filteredChats.length === 0) {
      return '<div class="no-data">No direct messages found from direct.db source</div>'
    }

    // Group chats by conversation/thread
    const conversationGroups = groupChatsByConversation(filteredChats)

    let html = `
    <div class="data-summary">
      <div class="summary-stats">
        <span class="stat-item">💬 Total Conversations: <strong>${Object.keys(conversationGroups).length}</strong></span>
        <span class="stat-item">📨 Total Messages: <strong>${filteredChats.length}</strong></span>
        <span class="stat-item">📅 Date Range: <strong>${getDateRange(filteredChats)}</strong></span>
        <span class="stat-item">🗂️ Source: <strong>direct.db</strong></span>
        <span class="stat-item">👤 Current User ID: <strong>${currentUserId || "Unknown"}</strong></span>
      </div>
    </div>
  `

    html += '<div class="modern-chat-container">'

    // Create conversation list (left panel)
    html += '<div class="conversation-list">'
    html += '<div class="conversation-header"><h3>💬 Direct Messages</h3></div>'

    Object.entries(conversationGroups).forEach(([conversationId, messages], index) => {
      const lastMessage = messages[messages.length - 1]
      const participantInfo = getConversationParticipants(messages)
      const messagePreview = getMessagePreview(lastMessage)
      const timestamp = formatTimestamp(
        lastMessage.timestamp || lastMessage.created_time || lastMessage.data?.timestamp,
      )
      const messageCount = messages.length

      html += `
      <div class="conversation-item ${index === 0 ? "active" : ""}" onclick="showConversation('${conversationId}')">
        <div class="conversation-avatar">
          <div class="avatar-circle">${participantInfo.displayName.charAt(0).toUpperCase()}</div>
        </div>
        <div class="conversation-info">
          <div class="conversation-name">${escapeHtml(participantInfo.displayName)}</div>
          <div class="conversation-participants">
            <span class="participant-ids">👥 ${participantInfo.participantIds.join(", ")}</span>
          </div>
          <div class="conversation-preview">${escapeHtml(messagePreview)}</div>
        </div>
        <div class="conversation-meta">
          <div class="conversation-time">${timestamp}</div>
          <div class="message-count">${messageCount}</div>
        </div>
      </div>
    `
    })

    html += "</div>" // End conversation list

    // Create chat display area (right panel)
    html += '<div class="chat-display-area">'

    Object.entries(conversationGroups).forEach(([conversationId, messages], index) => {
      const participantInfo = getConversationParticipants(messages)

      html += `
      <div id="conversation-${conversationId}" class="conversation-chat ${index === 0 ? "active" : ""}">
        <div class="chat-header">
          <div class="chat-participant">
            <div class="participant-avatar">
              <div class="avatar-circle">${participantInfo.displayName.charAt(0).toUpperCase()}</div>
            </div>
            <div class="participant-info">
              <div class="participant-name">${escapeHtml(participantInfo.displayName)}</div>
              <div class="participant-status">
                Active • ${messages.length} messages • Source: direct.db<br>
                <span class="participant-ids">Participants: ${participantInfo.participantIds.join(", ")}</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="chat-messages">
    `

      // Sort messages by timestamp
      const sortedMessages = messages.sort((a, b) => {
        const timeA = new Date(a.timestamp || a.created_time || a.data?.timestamp || 0)
        const timeB = new Date(b.timestamp || b.created_time || b.data?.timestamp || 0)
        return timeA - timeB
      })

      sortedMessages.forEach((message, msgIndex) => {
        const messageInfo = extractMessageInfo(message)
        const isOutgoing = isOutgoingMessage(message, currentUserId)

        html += `
        <div class="message-wrapper ${isOutgoing ? "outgoing" : "incoming"}">
          <div class="message-bubble">
            <div class="message-header-info">
              <div class="sender-info">
                <span class="sender-name">${escapeHtml(messageInfo.senderName)}</span>
                <span class="sender-id">ID: ${escapeHtml(messageInfo.senderId)}</span>
                ${messageInfo.receiverId ? `<span class="receiver-id">→ ${escapeHtml(messageInfo.receiverId)}</span>` : ""}
              </div>
              <div class="message-direction">
                <span class="direction-indicator ${isOutgoing ? "sent" : "received"}">
                  ${isOutgoing ? "📤 SENT" : "📥 RECEIVED"}
                </span>
              </div>
            </div>
            
            <div class="message-content">
              ${messageInfo.content ? escapeHtml(messageInfo.content) : "<em>No text content</em>"}
            </div>
            
            ${formatMessageMedia(message, conversationId)}
            ${formatCallInfo(message)}
            
            <div class="message-timestamp">
              ${formatTimestamp(messageInfo.timestamp)}
              ${messageInfo.messageType ? `• ${messageInfo.messageType}` : ""}
            </div>
          </div>
        </div>
      `
      })

      html += `
        </div>
      </div>
    `
    })

    html += "</div>" // End chat display area
    html += "</div>" // End modern chat container

    return html
  }

  // ENHANCED: Extract comprehensive message information
  function extractMessageInfo(message) {
    const msgData = message.data || message

    return {
      content: msgData.content || msgData.text || msgData.message || msgData.body || "",
      senderName: msgData.sender_name || msgData.author || msgData.from || msgData.user || "Unknown",
      senderId: msgData.sender_id || msgData.author_id || msgData.from_id || msgData.user_id || "Unknown",
      receiverId: msgData.receiver_id || msgData.to_id || msgData.recipient_id || null,
      timestamp: msgData.timestamp || msgData.created_time || msgData.sent_at || msgData.time,
      messageType: msgData.type || msgData.message_type || msgData.content_type || null,
      threadId: msgData.thread_id || msgData.conversation_id || msgData.chat_id,
      messageId: msgData.message_id || msgData.id,
    }
  }

  // ENHANCED: Determine if message is outgoing based on current user ID
  function isOutgoingMessage(message, currentUserId) {
    const msgData = message.data || message
    const senderId = msgData.sender_id || msgData.author_id || msgData.from_id || msgData.user_id
    const senderName = msgData.sender_name || msgData.author || msgData.from || msgData.user

    // Check by user ID first (most reliable)
    if (currentUserId && senderId) {
      return senderId.toString() === currentUserId.toString()
    }

    // Fallback to name-based detection
    if (senderName) {
      const name = senderName.toLowerCase()
      return name === "you" || name === "me" || msgData.is_outgoing === true
    }

    // Default to incoming if uncertain
    return false
  }

  // ENHANCED: Get conversation participants with IDs
  function getConversationParticipants(messages) {
    const participants = new Map()
    let displayName = "Unknown Conversation"

    messages.forEach((msg) => {
      const msgInfo = extractMessageInfo(msg)

      // Add sender
      if (msgInfo.senderId && msgInfo.senderId !== "Unknown") {
        participants.set(msgInfo.senderId, msgInfo.senderName)
      }

      // Add receiver if available
      if (msgInfo.receiverId && msgInfo.receiverId !== "Unknown") {
        participants.set(msgInfo.receiverId, "Receiver")
      }
    })

    const participantIds = Array.from(participants.keys())
    const participantNames = Array.from(participants.values())

    // Generate display name
    if (participantNames.length > 0) {
      const uniqueNames = [...new Set(participantNames.filter((name) => name !== "Unknown" && name !== "Receiver"))]
      if (uniqueNames.length === 1) {
        displayName = uniqueNames[0]
      } else if (uniqueNames.length > 1) {
        displayName = uniqueNames.slice(0, 2).join(", ") + (uniqueNames.length > 2 ? ` +${uniqueNames.length - 2}` : "")
      }
    }

    return {
      displayName,
      participantIds,
      participantNames: Array.from(participants.values()),
    }
  }

  // ENHANCED: Format message media with timestamps
  function formatMessageMedia(message, conversationId) {
    let mediaHtml = ""
    const msgData = message.data || message

    // Check for various media fields
    const mediaFields = ["media", "photos", "videos", "attachments", "media_url", "media_urls", "files"]
    let hasMedia = false

    mediaFields.forEach((field) => {
      if (msgData[field]) {
        hasMedia = true
        const timestamp = formatTimestamp(msgData.timestamp || msgData.created_time)

        mediaHtml += `<div class="message-media-section">`
        mediaHtml += `<div class="media-header">📎 Media Content • ${timestamp}</div>`

        if (Array.isArray(msgData[field])) {
          msgData[field].forEach((item, index) => {
            mediaHtml += formatMediaItem(item, index, field)
          })
        } else if (typeof msgData[field] === "string") {
          mediaHtml += formatMediaItem(msgData[field], 0, field)
        } else if (typeof msgData[field] === "object") {
          mediaHtml += formatMediaItem(msgData[field], 0, field)
        }

        mediaHtml += `</div>`
      }
    })

    // Get media from chat_media.json
    const chatMediaItems = getChatMediaForMessage(message, conversationId)
    if (chatMediaItems.length > 0) {
      const timestamp = formatTimestamp(msgData.timestamp || msgData.created_time)
      mediaHtml += `<div class="message-media-section">`
      mediaHtml += `<div class="media-header">🖼️ Chat Media • ${timestamp}</div>`

      chatMediaItems.forEach((mediaItem, index) => {
        mediaHtml += formatChatMediaItem(mediaItem, index)
      })

      mediaHtml += `</div>`
    }

    return mediaHtml
  }

  // ENHANCED: Format call information
  function formatCallInfo(message) {
    const msgData = message.data || message
    let callHtml = ""

    // Check for call-related fields
    const callFields = ["call", "call_type", "call_duration", "voice_call", "video_call"]
    const hasCall = callFields.some((field) => msgData[field])

    if (hasCall || (msgData.type && msgData.type.toLowerCase().includes("call"))) {
      const timestamp = formatTimestamp(msgData.timestamp || msgData.created_time)
      const callType = msgData.call_type || msgData.type || "Call"
      const duration = msgData.call_duration || msgData.duration
      const callStatus = msgData.call_status || msgData.status

      callHtml += `<div class="message-call-section">`
      callHtml += `<div class="call-header">📞 ${escapeHtml(callType)} • ${timestamp}</div>`

      if (duration) {
        callHtml += `<div class="call-detail">⏱️ Duration: ${escapeHtml(duration)}</div>`
      }

      if (callStatus) {
        callHtml += `<div class="call-detail">📊 Status: ${escapeHtml(callStatus)}</div>`
      }

      callHtml += `</div>`
    }

    return callHtml
  }

  // Helper function to format individual media items
  function formatMediaItem(item, index, fieldType) {
    let html = `<div class="media-item">`

    if (typeof item === "string") {
      // URL or file path
      const isImage = item.match(/\.(jpg|jpeg|png|gif|webp)$/i)
      const isVideo = item.match(/\.(mp4|mov|avi|webm)$/i)

      if (isImage) {
        html += `
          <img src="${escapeHtml(item)}" alt="Media ${index + 1}" class="media-preview" 
               onclick="openMediaViewer('${escapeHtml(item)}', 'image', 'Media ${index + 1}')"
               onerror="this.style.display='none'; this.nextElementSibling.style.display='block';" />
          <div class="media-fallback" style="display: none;">
            <span class="media-icon">🖼️</span>
            <span class="media-name">Image ${index + 1}</span>
          </div>
        `
      } else if (isVideo) {
        html += `
          <video class="media-preview" controls preload="metadata">
            <source src="${escapeHtml(item)}" type="video/mp4">
            Your browser does not support the video tag.
          </video>
        `
      } else {
        html += `
          <div class="media-file">
            <span class="media-icon">📎</span>
            <a href="${escapeHtml(item)}" target="_blank" class="media-link">${fieldType} ${index + 1}</a>
          </div>
        `
      }
    } else if (typeof item === "object" && item !== null) {
      // Media object with metadata
      const url = item.url || item.uri || item.path || item.src
      const name = item.name || item.filename || `${fieldType} ${index + 1}`
      const type = item.type || item.media_type || "unknown"

      html += `
        <div class="media-object">
          <div class="media-info">
            <span class="media-icon">${getMediaIcon(type)}</span>
            <span class="media-name">${escapeHtml(name)}</span>
            ${type ? `<span class="media-type">(${escapeHtml(type)})</span>` : ""}
          </div>
          ${url ? `<a href="${escapeHtml(url)}" target="_blank" class="media-link">📥 Download</a>` : ""}
        </div>
      `
    }

    html += `</div>`
    return html
  }

  // Helper function to format chat media items
  function formatChatMediaItem(mediaItem, index) {
    const mediaData = mediaItem.data || mediaItem
    const url = mediaData.media_url || mediaData.url || mediaData.uri || mediaData.path
    const filename = mediaData.filename || mediaData.name || `Chat Media ${index + 1}`
    const type = mediaData.type || mediaData.media_type || "unknown"

    let html = `<div class="chat-media-item">`

    if (url) {
      const isImage = url.match(/\.(jpg|jpeg|png|gif|webp)$/i) || type.toLowerCase().includes("image")
      const isVideo = url.match(/\.(mp4|mov|avi|webm)$/i) || type.toLowerCase().includes("video")

      if (isImage) {
        html += `
          <img src="${escapeHtml(url)}" alt="${escapeHtml(filename)}" class="chat-media-preview" 
               onclick="openMediaViewer('${escapeHtml(url)}', 'image', '${escapeHtml(filename)}')"
               onerror="this.style.display='none'; this.nextElementSibling.style.display='block';" />
          <div class="media-fallback" style="display: none;">
            <span class="media-icon">🖼️</span>
            <span class="media-name">${escapeHtml(filename)}</span>
          </div>
        `
      } else if (isVideo) {
        html += `
          <video class="chat-media-preview" controls preload="metadata">
            <source src="${escapeHtml(url)}" type="video/mp4">
            Your browser does not support the video tag.
          </video>
        `
      } else {
        html += `
          <div class="chat-media-file">
            <span class="media-icon">${getMediaIcon(type)}</span>
            <a href="${escapeHtml(url)}" target="_blank" class="media-link">${escapeHtml(filename)}</a>
          </div>
        `
      }
    } else {
      html += `
        <div class="chat-media-file">
          <span class="media-icon">${getMediaIcon(type)}</span>
          <span class="media-name">${escapeHtml(filename)}</span>
          <span class="no-url">No URL available</span>
        </div>
      `
    }

    html += `</div>`
    return html
  }

  // Helper function to get media icon based on type
  function getMediaIcon(type) {
    const typeStr = (type || "").toLowerCase()
    if (typeStr.includes("image") || typeStr.includes("photo")) return "🖼️"
    if (typeStr.includes("video")) return "🎥"
    if (typeStr.includes("audio") || typeStr.includes("voice")) return "🎵"
    if (typeStr.includes("document") || typeStr.includes("pdf")) return "📄"
    return "📎"
  }

  // Function to get chat media items for a specific message
  function getChatMediaForMessage(message, conversationId) {
    if (extractionData && extractionData.merged_files && extractionData.merged_files.chat_media) {
      const chatMediaItems = extractionData.merged_files.chat_media
      const messageData = message.data || message

      return chatMediaItems.filter((mediaItem) => {
        const mediaData = mediaItem.data || mediaItem

        // Match by thread/conversation ID
        if (
          mediaData.thread_id === messageData.thread_id ||
          mediaData.conversation_id === conversationId ||
          mediaData.thread_id === conversationId
        ) {
          return true
        }

        // Match by timestamp (within a reasonable range)
        const messageTime = new Date(messageData.timestamp || messageData.created_time || 0)
        const mediaTime = new Date(mediaData.timestamp || mediaData.created_time || 0)
        const timeDiff = Math.abs(messageTime - mediaTime)

        // If within 5 minutes and same sender
        if (
          timeDiff < 5 * 60 * 1000 &&
          (mediaData.sender_name === messageData.sender_name || mediaData.author === messageData.author)
        ) {
          return true
        }

        // Match by message ID if available
        if (messageData.message_id && mediaData.message_id === mediaData.message_id) {
          return true
        }

        return false
      })
    }

    return []
  }

  // Group chats by conversation
  function groupChatsByConversation(chats) {
    const grouped = {}

    chats.forEach((chat) => {
      const chatData = chat.data || chat
      const conversationId = chatData.thread_id || chatData.conversation_id || chatData.chat_id || "general"

      if (!grouped[conversationId]) {
        grouped[conversationId] = []
      }

      grouped[conversationId].push(chat)
    })

    return grouped
  }

  // Get message preview for conversation list
  function getMessagePreview(message) {
    const msgData = message.data || message
    const content = msgData.content || msgData.text || msgData.message || ""
    const hasMedia = msgData.attachments || msgData.media_url || msgData.media_urls || msgData.media
    const hasCall = msgData.call || msgData.call_type || (msgData.type && msgData.type.toLowerCase().includes("call"))

    if (hasCall) {
      return "📞 Call"
    } else if (hasMedia && !content) {
      return "📎 Media"
    } else if (content.length > 50) {
      return content.substring(0, 50) + "..."
    }

    return content || "No content"
  }

  // Global function to show conversation
  window.showConversation = (conversationId) => {
    // Hide all conversations
    document.querySelectorAll(".conversation-chat").forEach((chat) => {
      chat.classList.remove("active")
    })

    // Remove active class from all conversation items
    document.querySelectorAll(".conversation-item").forEach((item) => {
      item.classList.remove("active")
    })

    // Show selected conversation
    const selectedChat = document.getElementById(`conversation-${conversationId}`)
    if (selectedChat) {
      selectedChat.classList.add("active")
    }

    // Add active class to clicked conversation item
    event.target.closest(".conversation-item").classList.add("active")
  }

  // Enhanced format chat media data to show URLs prominently
  function formatChatMediaData(chatMedia) {
    if (!chatMedia || chatMedia.length === 0) {
      return '<div class="no-data">No chat media found</div>'
    }

    let html = `
    <div class="data-summary">
      <div class="summary-stats">
        <span class="stat-item">📊 Total Items: <strong>${chatMedia.length}</strong></span>
        <span class="stat-item">📅 Date Range: <strong>${getDateRange(chatMedia)}</strong></span>
        <span class="stat-item">🗂️ Source: <strong>chat_media.json</strong></span>
      </div>
    </div>
    <div class="chat-media-grid">
  `

    chatMedia.slice(0, 50).forEach((item, index) => {
      const mediaData = item.data || item

      const filename = mediaData.filename || mediaData.name || `Chat Media ${index + 1}`
      const type = mediaData.type || mediaData.media_type || "Unknown type"
      const timestamp = formatTimestamp(mediaData.timestamp || mediaData.creation_time)
      const sender = mediaData.sender_name || mediaData.author || "Unknown sender"
      const size = formatFileSize(mediaData.size || 0)

      const mediaUrl =
        mediaData.media_url ||
        mediaData.url ||
        mediaData.uri ||
        mediaData.path ||
        mediaData.local_file_path ||
        mediaData.view_link

      const threadId = mediaData.thread_id || mediaData.conversation_id || "Unknown thread"

      html += `
      <div class="chat-media-card">
        <div class="media-preview">
          ${getMediaPreviewWithUrl(mediaData, type, mediaUrl)}
        </div>
        <div class="media-info">
          <div class="media-filename">${escapeHtml(filename)}</div>
          <div class="media-details">
            <div class="detail-row">
              <span class="detail-label">👤 Sender:</span>
              <span class="detail-value">${escapeHtml(sender)}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">💬 Thread:</span>
              <span class="detail-value">${escapeHtml(threadId)}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">📅 Date:</span>
              <span class="detail-value">${timestamp}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">📏 Size:</span>
              <span class="detail-value">${formatFileSize(size)}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">🏷️ Type:</span>
              <span class="detail-value">${escapeHtml(type)}</span>
            </div>
            ${
              mediaUrl
                ? `
            <div class="detail-row">
              <span class="detail-label">🔗 URL:</span>
              <span class="detail-value">
                <div class="url-actions">
                  <button onclick="copyToClipboard('${escapeHtml(mediaUrl)}')" class="copy-url-btn">📋 Copy</button>
                  <a href="${escapeHtml(mediaUrl)}" target="_blank" class="view-url-btn">🔍 Open</a>
                  ${
                    type.toLowerCase().includes("image") || mediaUrl.match(/\.(jpg|jpeg|png|gif|webp)$/i)
                      ? `<button onclick="openMediaViewer('${escapeHtml(mediaUrl)}', 'image', '${escapeHtml(filename)}')" class="preview-btn">👁️ Preview</button>`
                      : type.toLowerCase().includes("video") || mediaUrl.match(/\.(mp4|mov|avi|webm)$/i)
                        ? `<button onclick="openMediaViewer('${escapeHtml(mediaUrl)}', 'video', '${escapeHtml(filename)}')" class="preview-btn">▶️ Play</button>`
                        : ""
                  }
                </div>
              </span>
            </div>
            `
                : '<div class="detail-row"><span class="detail-label">🔗 URL:</span><span class="detail-value">No URL available</span></div>'
            }
          </div>
        </div>
      </div>
    `
    })

    html += "</div>"

    if (chatMedia.length > 50) {
      html += `<div class="show-more">Showing first 50 of ${chatMedia.length} chat media items</div>`
    }

    return html
  }

  // Enhanced media preview with clickable URLs
  function getMediaPreviewWithUrl(item, type, mediaUrl) {
    const isImage = type.toLowerCase().includes("image") || (mediaUrl && mediaUrl.match(/\.(jpg|jpeg|png|gif|webp)$/i))
    const isVideo = type.toLowerCase().includes("video") || (mediaUrl && mediaUrl.match(/\.(mp4|mov|avi|webm)$/i))

    if (isImage && mediaUrl) {
      return `
      <div class="image-preview clickable" onclick="openMediaViewer('${escapeHtml(mediaUrl)}', 'image', '${escapeHtml(item.filename || item.name || "Image")}')">
        <img src="${escapeHtml(mediaUrl)}" alt="Preview" style="width: 100%; height: 100%; object-fit: cover; border-radius: 8px;" onerror="this.style.display='none'; this.parentElement.innerHTML='<div style=\\'display: flex; align-items: center; justify-content: center; height: 100%; font-size: 2rem;\\'>🖼️</div>';" />
      </div>
    `
    } else if (isVideo && mediaUrl) {
      return `
      <div class="video-preview clickable" onclick="openMediaViewer('${escapeHtml(mediaUrl)}', 'video', '${escapeHtml(item.filename || item.name || "Video")}')">
        <div style="position: relative; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #000; border-radius: 8px;">
          <div style="font-size: 3rem; color: white;">🎥</div>
          <div style="position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem;">▶️ Video</div>
        </div>
      </div>
    `
    } else if (mediaUrl) {
      return `
      <div class="file-preview clickable" onclick="window.open('${escapeHtml(mediaUrl)}', '_blank')">
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #6b7280;">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">📎</div>
          <div style="font-size: 0.8rem; text-align: center;">Click to open</div>
        </div>
      </div>
    `
    } else {
      return `<div class="file-preview" style="display: flex; align-items: center; justify-content: center; height: 100%; font-size: 2rem; color: #9ca3af;">📄</div>`
    }
  }

  // Enhanced format media data in a structured way
  function formatMediaData(media) {
    if (!media || media.length === 0) {
      return '<div class="no-data">No media files found</div>'
    }

    // Group media by type
    const mediaByType = groupMediaByType(media)
    const totalSize = calculateTotalSize(media)

    let html = `
      <div class="data-summary">
        <div class="summary-stats">
          <span class="stat-item">📊 Total Files: <strong>${media.length}</strong></span>
          <span class="stat-item">💾 Total Size: <strong>${formatFileSize(totalSize)}</strong></span>
          <span class="stat-item">📅 Date Range: <strong>${getDateRange(media)}</strong></span>
        </div>
      </div>
    `

    // Media type tabs
    html += `
      <div class="media-type-tabs">
        ${Object.keys(mediaByType)
          .map(
            (type, index) =>
              `<button class="media-tab ${index === 0 ? "active" : ""}" onclick="showMediaType('${type}')">${getMediaTypeIcon(type)} ${type} (${mediaByType[type].length})</button>`,
          )
          .join("")}
      </div>
    `

    // Media content for each type
    Object.keys(mediaByType).forEach((type, index) => {
      html += `
        <div id="media-${type}" class="media-type-content ${index === 0 ? "active" : ""}">
          <div class="media-grid">
      `

      mediaByType[type].slice(0, 24).forEach((item, itemIndex) => {
        const itemData = item.data || item
        const title = itemData.title || itemData.name || itemData.filename || `${type} ${itemIndex + 1}`
        const timestamp = formatTimestamp(itemData.taken_at || itemData.timestamp || itemData.creation_time)
        const size = formatFileSize(itemData.size || 0)
        const path = itemData.uri || itemData.path || itemData.local_file_path || "No path"
        const dimensions = getDimensions(itemData)

        html += `
          <div class="media-card">
            <div class="media-preview">
              ${getMediaPreview(itemData, type)}
            </div>
            <div class="media-info">
              <div class="media-title">${escapeHtml(title)}</div>
              <div class="media-details">
                <div class="detail-row">
                  <span class="detail-label">📅 Date:</span>
                  <span class="detail-value">${timestamp}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">📏 Size:</span>
                  <span class="detail-value">${size}</span>
                </div>
                ${
                  dimensions
                    ? `
                <div class="detail-row">
                  <span class="detail-label">📐 Dimensions:</span>
                  <span class="detail-value">${dimensions}</span>
                </div>
                `
                    : ""
                }
                <div class="detail-row">
                  <span class="detail-label">📁 Path:</span>
                  <span class="detail-value path-text">${escapeHtml(path)}</span>
                </div>
              </div>
            </div>
          </div>
        `
      })

      if (mediaByType[type].length > 24) {
        html += `<div class="show-more-media">Showing first 24 of ${mediaByType[type].length} ${type} files</div>`
      }

      html += `</div></div>`
    })

    return html
  }

  // Helper functions for enhanced formatting
  function groupChatsByThread(chats) {
    const grouped = {}
    chats.forEach((chat) => {
      const chatData = chat.data || chat
      const threadId = chatData.thread_id || chatData.conversation_id || chatData.chat_id || "general"
      if (!grouped[threadId]) {
        grouped[threadId] = []
      }
      grouped[threadId].push(chat)
    })
    return grouped
  }

  function getThreadTitle(messages) {
    if (messages.length === 0) return "Unknown Thread"

    // Try to get thread title from first message
    const firstMsg = messages[0]
    const firstMsgData = firstMsg.data || firstMsg
    if (firstMsgData.thread_title || firstMsgData.conversation_title) {
      return firstMsgData.thread_title || firstMsgData.conversation_title
    }

    // Generate title from participants
    const participants = [
      ...new Set(
        messages
          .map((m) => {
            const msgData = m.data || m
            return msgData.sender_name || msgData.author || msgData.user_id
          })
          .filter(Boolean),
      ),
    ]

    if (participants.length > 0) {
      return participants.length > 3
        ? `${participants.slice(0, 3).join(", ")} and ${participants.length - 3} others`
        : participants.join(", ")
    }

    return "Unknown Thread"
  }

  function getUniqueParticipants(chats) {
    const participants = new Set()
    chats.forEach((chat) => {
      const chatData = chat.data || chat
      const sender = chatData.sender_name || chatData.author || chatData.user_id
      if (sender) participants.add(sender)
    })
    return participants.size
  }

  function getDateRange(items) {
    if (!items || items.length === 0) return "Unknown"

    const dates = items
      .map((item) => {
        const itemData = item.data || item
        const dateStr = itemData.timestamp || itemData.created_time || itemData.sent_at || itemData.taken_at
        return dateStr ? new Date(dateStr) : null
      })
      .filter(Boolean)

    if (dates.length === 0) return "Unknown"

    const minDate = new Date(Math.min(...dates))
    const maxDate = new Date(Math.max(...dates))

    if (minDate.toDateString() === maxDate.toDateString()) {
      return minDate.toLocaleDateString()
    }

    return `${minDate.toLocaleDateString()} - ${maxDate.toLocaleDateString()}`
  }

  function formatTimestamp(timestamp) {
    if (!timestamp) return "Unknown time"
    try {
      const date = new Date(timestamp)
      return date.toLocaleString()
    } catch {
      return timestamp
    }
  }

  function formatMessageAttachments(attachments) {
    if (!attachments) return ""

    let html = '<div class="message-attachments">'

    if (Array.isArray(attachments)) {
      attachments.forEach((attachment) => {
        html += `<div class="attachment">📎 ${attachment.name || attachment.filename || "Attachment"}</div>`
      })
    } else if (typeof attachments === "object") {
      Object.keys(attachments).forEach((key) => {
        html += `<div class="attachment">📎 ${key}: ${attachments[key]}</div>`
      })
    }

    html += "</div>"
    return html
  }

  function groupMediaByType(media) {
    const grouped = {}
    media.forEach((item) => {
      const itemData = item.data || item
      let type = itemData.media_type || itemData.type || "unknown"

      // Normalize type names
      if (type.includes("image") || type.includes("photo")) type = "Images"
      else if (type.includes("video")) type = "Videos"
      else if (type.includes("audio")) type = "Audio"
      else if (type.includes("document")) type = "Documents"
      else type = "Other"

      if (!grouped[type]) grouped[type] = []
      grouped[type].push(item)
    })
    return grouped
  }

  function calculateTotalSize(media) {
    return media.reduce((total, item) => {
      const itemData = item.data || item
      return total + (Number.parseInt(itemData.size) || 0)
    }, 0)
  }

  function getMediaTypeIcon(type) {
    const icons = {
      Images: "🖼️",
      Videos: "🎥",
      Audio: "🎵",
      Documents: "📄",
      Other: "📎",
    }
    return icons[type] || "📎"
  }

  function getMediaPreview(item, type) {
    if (type === "Images") {
      return `<div class="image-preview">🖼️</div>`
    } else if (type === "Videos") {
      return `<div class="video-preview">🎥</div>`
    } else if (type === "Audio") {
      return `<div class="audio-preview">🎵</div>`
    }
    return `<div class="file-preview">📄</div>`
  }

  function getDimensions(item) {
    if (item.width && item.height) {
      return `${item.width} × ${item.height}`
    }
    return null
  }

  // Global function for media type switching
  window.showMediaType = (type) => {
    // Hide all media type contents
    document.querySelectorAll(".media-type-content").forEach((content) => {
      content.classList.remove("active")
    })

    // Remove active class from all tabs
    document.querySelectorAll(".media-tab").forEach((tab) => {
      tab.classList.remove("active")
    })

    // Show selected content and activate tab
    const selectedContent = document.getElementById(`media-${type}`)
    if (selectedContent) {
      selectedContent.classList.add("active")
    }

    event.target.classList.add("active")
  }

  // Format session data
  function formatSessionData(sessionData) {
    if (!sessionData || Object.keys(sessionData).length === 0) {
      return '<div class="no-data">No session data found</div>'
    }

    let html = ""

    // Primary session info
    if (sessionData.primary_instagram_session_id) {
      html += `
        <div class="session-primary">
          <h3>🔑 Primary Instagram Session</h3>
          <div class="session-id">${escapeHtml(sessionData.primary_instagram_session_id)}</div>
        </div>
      `
    }

    // User ID info
    if (sessionData.logged_in_user_id) {
      html += `
        <div class="session-user">
          <h3>👤 Logged In User ID</h3>
          <div class="user-id">${escapeHtml(sessionData.logged_in_user_id)}</div>
        </div>
      `
    }

    // All sessions
    const sessions = sessionData.all_unique_sessions || []
    if (sessions.length > 0) {
      html += `
        <div class="data-summary">
          <div class="summary-stats">
            <span class="stat-item">📊 Total Sessions: <strong>${sessions.length}</strong></span>
            <span class="stat-item">🔍 Session Types: <strong>${getUniqueSessionTypes(sessions)}</strong></span>
          </div>
        </div>
      `

      // Group sessions by type
      const sessionsByType = {}
      sessions.forEach((session) => {
        const type = session.type || "unknown"
        if (!sessionsByType[type]) {
          sessionsByType[type] = []
        }
        sessionsByType[type].push(session)
      })

      Object.keys(sessionsByType).forEach((type) => {
        html += `
          <div class="session-group">
            <h4>${getSessionTypeIcon(type)} ${escapeHtml(type.toUpperCase())} Sessions (${sessionsByType[type].length})</h4>
            <div class="session-list">
        `

        sessionsByType[type].slice(0, 10).forEach((session) => {
          html += `
            <div class="session-item">
              <div class="session-value">${escapeHtml(session.value || "No value")}</div>
              <div class="session-meta">
                <span class="meta-item">📍 Found in: ${escapeHtml(session.found_in || "Unknown")}</span>
                <span class="meta-item">🎯 Confidence: ${session.confidence || 0}%</span>
                <span class="meta-item">⏰ Pattern: ${escapeHtml(session.pattern || "N/A")}</span>
              </div>
            </div>
          `
        })

        if (sessionsByType[type].length > 10) {
          html += `<div class="show-more">Showing first 10 of ${sessionsByType[type].length} ${type} sessions</div>`
        }

        html += "</div></div>"
      })
    }

    return html || '<div class="no-data">No session data available</div>'
  }

  function getUniqueSessionTypes(sessions) {
    const types = new Set(sessions.map((s) => s.type || "unknown"))
    return types.size
  }

  function getSessionTypeIcon(type) {
    const icons = {
      sessionid: "🔐",
      csrf_token: "🛡️",
      user_id: "👤",
      device_id: "📱",
      auth_token: "🎫",
      api_key: "🔑",
      cookie: "🍪",
    }
    return icons[type.toLowerCase()] || "🔧"
  }

  // Format user profile data
  function formatUserProfileData(profileData) {
    if (!profileData || Object.keys(profileData).length === 0) {
      return '<div class="no-data">No user profile data found</div>'
    }

    const user = profileData.logged_in_user || profileData

    let html = '<div class="profile-container">'

    // Profile header with avatar and basic info
    html += `
      <div class="profile-header">
        <div class="profile-avatar">👤</div>
        <div class="profile-basic">
          <h2 class="profile-username">${escapeHtml(user.username || "Unknown User")}</h2>
          <p class="profile-fullname">${escapeHtml(user.full_name || "No full name")}</p>
          <div class="profile-badges">
            ${user.is_verified ? '<span class="badge verified">✅ Verified</span>' : ""}
            ${user.is_private ? '<span class="badge private">🔒 Private</span>' : '<span class="badge public">🌐 Public</span>'}
          </div>
        </div>
      </div>
    `

    // Basic info
    html += `
      <div class="profile-section">
        <h3>📋 Basic Information</h3>
        <div class="profile-grid">
          <div class="profile-item">
            <label>📧 Email:</label>
            <span>${escapeHtml(user.email || "Not available")}</span>
          </div>
          <div class="profile-item">
            <label>📱 Phone:</label>
            <span>${escapeHtml(user.phone_number || "Not available")}</span>
          </div>
          <div class="profile-item">
            <label>🆔 User ID:</label>
            <span class="user-id-text">${escapeHtml(user.user_id || "Not available")}</span>
          </div>
          <div class="profile-item">
            <label>🌐 Website:</label>
            <span>${escapeHtml(user.website || "Not available")}</span>
          </div>
          <div class="profile-item">
            <label>📝 Bio:</label>
            <span class="bio-text">${escapeHtml(user.bio || "Not available")}</span>
          </div>
          <div class="profile-item">
            <label>🔑 Session ID:</label>
            <span class="session-id-text">${escapeHtml(user.primary_instagram_session_id || "Not available")}</span>
          </div>
        </div>
      </div>
    `

    // Account stats
    html += `
      <div class="profile-section">
        <h3>📊 Account Statistics</h3>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon">👥</div>
            <div class="stat-value">${formatNumber(user.followers_count || 0)}</div>
            <div class="stat-label">Followers</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">➕</div>
            <div class="stat-value">${formatNumber(user.following_count || 0)}</div>
            <div class="stat-label">Following</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">📸</div>
            <div class="stat-value">${formatNumber(user.posts_count || 0)}</div>
            <div class="stat-label">Posts</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">⏳</div>
            <div class="stat-value">${formatNumber(user.pending_incoming_requests_count || 0)}</div>
            <div class="stat-label">Pending Requests</div>
          </div>
        </div>
      </div>
    `

    // Account timeline
    html += `
      <div class="profile-section">
        <h3>⏰ Account Timeline</h3>
        <div class="timeline">
          <div class="timeline-item">
            <div class="timeline-icon">🎂</div>
            <div class="timeline-content">
              <div class="timeline-title">Account Created</div>
              <div class="timeline-date">${formatTimestamp(user.account_creation_date) || "Unknown"}</div>
            </div>
          </div>
          <div class="timeline-item">
            <div class="timeline-icon">🔐</div>
            <div class="timeline-content">
              <div class="timeline-title">Last Login</div>
              <div class="timeline-date">${formatTimestamp(user.last_login) || "Unknown"}</div>
            </div>
          </div>
        </div>
      </div>
    `

    html += "</div>"

    return html
  }

  function formatNumber(num) {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + "M"
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + "K"
    }
    return num.toString()
  }

  // Format folder analysis data
  function formatFolderAnalysisData(analysisData) {
    if (!analysisData || Object.keys(analysisData).length === 0) {
      return '<div class="no-data">No folder analysis data found</div>'
    }

    let html = '<div class="analysis-container">'

    // File statistics
    if (analysisData.file_statistics) {
      const stats = analysisData.file_statistics
      html += `
        <div class="analysis-section">
          <h3>📊 File Statistics</h3>
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon">📄</div>
              <div class="stat-value">${formatNumber(stats.total_files || 0)}</div>
              <div class="stat-label">Total Files</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">📁</div>
              <div class="stat-value">${formatNumber(stats.total_directories || 0)}</div>
              <div class="stat-label">Directories</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">💾</div>
              <div class="stat-value">${formatFileSize(stats.total_size || 0)}</div>
              <div class="stat-label">Total Size</div>
            </div>
          </div>
        </div>
      `
    }

    // File types
    if (analysisData.file_types) {
      html += `
        <div class="analysis-section">
          <h3>🏷️ File Types Found</h3>
          <div class="file-types-grid">
      `

      Object.entries(analysisData.file_types).forEach(([type, count]) => {
        html += `
          <div class="file-type-card">
            <div class="file-type-icon">${getFileTypeIcon(type)}</div>
            <div class="file-type-info">
              <div class="file-type-name">${escapeHtml(type)}</div>
              <div class="file-type-count">${count} files</div>
            </div>
          </div>
        `
      })

      html += "</div></div>"
    }

    html += "</div>"

    return html
  }

  function getFileTypeIcon(type) {
    const icons = {
      json: "📋",
      jpg: "🖼️",
      jpeg: "🖼️",
      png: "🖼️",
      gif: "🎞️",
      mp4: "🎥",
      mov: "🎥",
      txt: "📄",
      pdf: "📕",
      zip: "📦",
    }
    return icons[type.toLowerCase()] || "📄"
  }

  // Format extraction report data
  function formatExtractionReportData(reportData) {
    if (!reportData || Object.keys(reportData).length === 0) {
      return '<div class="no-data">No extraction report data found</div>'
    }

    let html = '<div class="report-container">'

    // V5 Report Summary
    if (reportData.v5_report_summary) {
      html += `
        <div class="report-section">
          <h3>🔧 Module 1 (V5) Report</h3>
          <div class="report-content">
            ${formatReportSummary(reportData.v5_report_summary)}
          </div>
        </div>
      `
    }

    // V7 Report Summary
    if (reportData.v7_report_summary) {
      html += `
        <div class="report-section">
          <h3>⚙️ Module 2 (V7) Report</h3>
          <div class="report-content">
            ${formatReportSummary(reportData.v7_report_summary)}
          </div>
        </div>
      `
    }

    // Final summary
    if (reportData.final_user_profile_summary) {
      html += `
        <div class="report-section">
          <h3>📋 Final Profile Summary</h3>
          <div class="report-content">
            ${formatReportSummary(reportData.final_user_profile_summary)}
          </div>
        </div>
      `
    }

    html += "</div>"

    return html
  }

  // Format master data
  function formatMasterData(masterData) {
    if (!masterData || Object.keys(masterData).length === 0) {
      return '<div class="no-data">No master summary data found</div>'
    }

    let html = '<div class="master-container">'

    // Master summary
    html += `
      <div class="master-section">
        <h3>📋 Master Summary</h3>
        <p class="summary-text">${escapeHtml(masterData.master_summary || "No summary available")}</p>
      </div>
    `

    // Key session info
    if (masterData.key_session_info) {
      const sessionInfo = masterData.key_session_info
      html += `
        <div class="master-section">
          <h3>🔑 Key Session Information</h3>
          <div class="session-info-cards">
            <div class="info-card">
              <div class="info-icon">🔐</div>
              <div class="info-content">
                <div class="info-label">Primary Session ID</div>
                <div class="info-value">${escapeHtml(sessionInfo.primary_session_id || "Not available")}</div>
              </div>
            </div>
            <div class="info-card">
              <div class="info-icon">📊</div>
              <div class="info-content">
                <div class="info-label">Total Sessions Found</div>
                <div class="info-value">${sessionInfo.total_sessions_found || 0}</div>
              </div>
            </div>
          </div>
        </div>
      `
    }

    // Data summary
    if (masterData.data_summary) {
      const dataSummary = masterData.data_summary
      html += `
        <div class="master-section">
          <h3>📊 Data Summary</h3>
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon">💬</div>
              <div class="stat-value">${dataSummary.chats_found || 0}</div>
              <div class="stat-label">Chats Found</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">📷</div>
              <div class="stat-value">${dataSummary.media_found || 0}</div>
              <div class="stat-label">Media Found</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">🖼️</div>
              <div class="stat-value">${dataSummary.chat_media_found || 0}</div>
              <div class="stat-label">Chat Media Found</div>
            </div>
          </div>
        </div>
      `
    }

    html += "</div>"

    return html
  }

  // Global function to open media viewer
  window.openMediaViewer = (url, type, filename = "Media") => {
    const modal = document.createElement("div")
    modal.className = "media-viewer-modal"
    modal.innerHTML = `
      <div class="media-viewer-content">
        <div class="media-viewer-header">
          <h3>📱 ${escapeHtml(filename)}</h3>
          <button class="close-viewer" onclick="window.closeMediaViewer()">&times;</button>
        </div>
        <div class="media-viewer-body">
          ${
            type === "image"
              ? `<img src="${url}" alt="${escapeHtml(filename)}" class="viewer-image" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';" />
                 <div style="display: none; color: white; text-align: center;">
                   <div style="font-size: 3rem; margin-bottom: 1rem;">🖼️</div>
                   <p>Image could not be loaded</p>
                   <p style="font-size: 0.9rem; opacity: 0.7;">URL: ${url}</p>
                 </div>`
              : `<video src="${url}" controls class="viewer-video" preload="metadata">
                   <source src="${url}" type="video/mp4">
                   Your browser does not support the video tag.
                 </video>`
          }
        </div>
        <div class="media-viewer-footer">
          <a href="${url}" target="_blank" class="download-media">📥 Download</a>
          <button onclick="copyToClipboard('${url}')" class="copy-url">📋 Copy URL</button>
          <button onclick="window.closeMediaViewer()" class="close-media">❌ Close</button>
        </div>
      </div>
    `

    document.body.appendChild(modal)

    // Close on background click
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        window.closeMediaViewer()
      }
    })

    // Close on Escape key
    const handleEscape = (e) => {
      if (e.key === "Escape") {
        window.closeMediaViewer()
        document.removeEventListener("keydown", handleEscape)
      }
    }
    document.addEventListener("keydown", handleEscape)
  }

  // Global function to close media viewer
  window.closeMediaViewer = () => {
    const modal = document.querySelector(".media-viewer-modal")
    if (modal) {
      modal.remove()
    }
  }

  // Global function to copy URL to clipboard
  window.copyToClipboard = (text) => {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        alert("URL copied to clipboard!")
      })
      .catch(() => {
        // Fallback for older browsers
        const textArea = document.createElement("textarea")
        textArea.value = text
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand("copy")
        document.body.removeChild(textArea)
        alert("URL copied to clipboard!")
      })
  }

  // Helper functions
  function escapeHtml(text) {
    if (text == null) return ""
    const div = document.createElement("div")
    div.textContent = text
    return div.innerHTML
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }

  function formatReportSummary(summary) {
    if (typeof summary === "string") {
      return `<p class="summary-text">${escapeHtml(summary)}</p>`
    } else if (typeof summary === "object") {
      return `<pre class="json-code">${JSON.stringify(summary, null, 2)}</pre>`
    }
    return "<p>No summary available</p>"
  }
})
