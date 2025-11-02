document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("extractorForm")
  const inputPathField = document.getElementById("inputPath")
  const caseNumberField = document.getElementById("caseNumber")
  const examinerNameField = document.getElementById("examinerName")
  const evidenceItemField = document.getElementById("evidenceItem")
  const extractButton = document.getElementById("extractButton")
  const buttonText = document.getElementById("buttonText")
  const loader = document.getElementById("loader")
  const errorMessage = document.getElementById("errorMessage")

  // Modal elements
  const progressModal = document.getElementById("progressModal")
  const modalOutputContent = document.getElementById("modalOutputContent")
  const modalStatusText = document.getElementById("modalStatusText")
  const viewResultsBtn = document.getElementById("viewResultsBtn")

  let pollingInterval

  // Function to display messages in the modal's output area
  function displayModalOutput(message, append = true) {
    if (modalOutputContent) {
      if (append) {
        modalOutputContent.textContent += message + "\n"
      } else {
        modalOutputContent.textContent = message + "\n"
      }
      modalOutputContent.scrollTop = modalOutputContent.scrollHeight
    }
  }

  // Function to set loading state
  function setLoading(isLoading) {
    if (isLoading) {
      if (buttonText) buttonText.classList.add("hidden")
      if (loader) loader.classList.remove("hidden")
      if (extractButton) extractButton.disabled = true
      if (progressModal) progressModal.classList.remove("hidden")
      errorMessage.classList.add("hidden") // Hide error message on new attempt
    } else {
      if (buttonText) buttonText.classList.remove("hidden")
      if (loader) loader.classList.add("hidden")
      if (extractButton) extractButton.disabled = false
    }
  }

  // Function to show error message on main page
  function showError(message) {
    errorMessage.textContent = message
    errorMessage.classList.remove("hidden")
  }

  // Handle form submission
  form.addEventListener("submit", async (event) => {
    event.preventDefault() // Prevent default form submission

    setLoading(true)
    displayModalOutput("Initiating extraction...", false) // Clear and set initial message
    if (modalStatusText) modalStatusText.textContent = "Connecting to server..."
    if (viewResultsBtn) viewResultsBtn.classList.add("hidden") // Hide results button initially

    const inputPath = inputPathField.value
    const caseNumber = caseNumberField.value
    const examinerName = examinerNameField.value
    const evidenceItem = evidenceItemField.value

    try {
      const response = await fetch("/extract", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          inputPath,
          caseNumber,
          examinerName,
          evidenceItem,
        }),
      })

      const result = await response.json()

      if (result.status === "success") {
        displayModalOutput("Extraction initiated successfully. Polling for updates...")
        if (modalStatusText) modalStatusText.textContent = "Extraction started."

        // Start polling for status updates
        pollingInterval = setInterval(async () => {
          try {
            const statusResponse = await fetch("/get_status") // Correct endpoint
            const statusResult = await statusResponse.json()

            if (statusResult.status === "success") {
              // Update modal output with new lines from the server
              const newOutput = statusResult.output || ""
              modalOutputContent.textContent = newOutput // Replace content to reflect current state
              modalOutputContent.scrollTop = modalOutputContent.scrollHeight // Scroll to bottom

              if (modalStatusText) modalStatusText.textContent = statusResult.message

              if (statusResult.extraction_status === "completed") {
                clearInterval(pollingInterval)
                displayModalOutput("--- Extraction Complete! ---")
                if (viewResultsBtn) viewResultsBtn.classList.remove("hidden") // Show results button
                if (modalStatusText) modalStatusText.textContent = "Extraction Completed!"
                setLoading(false)
                showError("Extraction completed successfully.") // Show success message on main page too
              } else if (statusResult.extraction_status === "failed") {
                clearInterval(pollingInterval)
                displayModalOutput("--- Extraction Failed! ---")
                if (modalStatusText) modalStatusText.textContent = "Extraction Failed!"
                setLoading(false)
                showError("Extraction failed. Check the output above.")
              }
            } else {
              displayModalOutput(`Error during polling: ${statusResult.message}`)
              if (modalStatusText) modalStatusText.textContent = "Polling error!"
              clearInterval(pollingInterval)
              setLoading(false)
              showError(`Polling error: ${statusResult.message}`)
            }
          } catch (pollError) {
            displayModalOutput(`Polling error: ${pollError.message}`)
            if (modalStatusText) modalStatusText.textContent = "Polling error!"
            clearInterval(pollingInterval)
            setLoading(false)
            showError(`Network error during polling: ${pollError.message}`)
          }
        }, 3000) // Poll every 3 seconds
      } else {
        displayModalOutput(`Error: ${result.message}`)
        if (modalStatusText) modalStatusText.textContent = "Extraction failed to start."
        setLoading(false)
        showError(`Error starting extraction: ${result.message}`)
      }
    } catch (error) {
      console.error("Network error during extraction:", error)
      displayModalOutput(`Network error during extraction: ${error.message}`)
      if (modalStatusText) modalStatusText.textContent = "Network error."
      setLoading(false)
      showError(`Network error: ${error.message}`)
    }
  })

  // Close modal when clicking outside
  if (progressModal) {
    progressModal.addEventListener("click", (event) => {
      if (event.target === progressModal) {
        if (pollingInterval) {
          clearInterval(pollingInterval)
        }
        progressModal.classList.add("hidden")
        setLoading(false)
      }
    })
  }

  // Handle escape key to close modal
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && progressModal && !progressModal.classList.contains("hidden")) {
      if (pollingInterval) {
        clearInterval(pollingInterval)
      }
      progressModal.classList.add("hidden")
      setLoading(false)
    }
  })

  // Handle View Results button click
  if (viewResultsBtn) {
    viewResultsBtn.addEventListener("click", () => {
      window.location.href = "/results" // Redirect to the results page
    })
  }
})
