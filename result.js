const resultsFrame = document.getElementById("resultsFrame");

function showLoadingPlaceholders() {
  resultsFrame.innerHTML = '';
  for (let i = 0; i < 5; i++) {
    const placeholder = document.createElement("div");
    placeholder.className = "doc-card loading animate";
    placeholder.innerHTML = `
      <h3 class="shimmer">&nbsp;</h3>
      <p class="shimmer">&nbsp;</p>
      <p class="shimmer">&nbsp;</p>
      <p class="shimmer">&nbsp;</p>
      <button class="open-btn shimmer">&nbsp;</button>
    `;
    resultsFrame.appendChild(placeholder);
  }
}

function displayResults(data) {
  resultsFrame.innerHTML = '';

  if (!data || data.length === 0) {
    resultsFrame.innerHTML = '<p style="color:#8c50d1;font-weight:bold">No documents found.</p>';
    return;
  }

  data.forEach((doc, index) => {
    const card = document.createElement("div");
    card.className = "doc-card animate";
    card.style.animationDelay = `${index * 100}ms`;

    card.innerHTML = `
      <h3><strong>${doc.filename}</strong></h3>
      <p class="modified">Last modified: ${doc.modified}</p>
      <p>File path: ${doc.path}</p>
      <p>Type: ${doc.extension?.replace('.', '') || "unknown"}</p>  
      <button class="open-btn" data-path="${doc.path}">OPEN</button>
    `;

    resultsFrame.appendChild(card);
  });

  // ✅ Hook up open buttons
  document.querySelectorAll(".open-btn").forEach(button => {
    button.addEventListener("click", async (e) => {
      const filePath = e.target.getAttribute("data-path");
      if (!filePath) return;

      try {
        const res = await fetch("http://127.0.0.1:5005/openfile", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: filePath })
        });

        const result = await res.json();
        if (result.success) {
          console.log("✅ File opened:", filePath);
        } else {
          console.error("❌ Failed to open file: " + result.error);
        }
      } catch (err) {
        console.error("Error calling open-file API:", err);
        alert("❌ Could not connect to backend.");
      }
    });
  });
}

async function searchDocuments() {
  const query = document.getElementById("searchInput").value.trim();
  if (!query) return;

  showLoadingPlaceholders();

  try {
    const response = await fetch("http://127.0.0.1:5005/task", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        action: "search",
        q: query
      })
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const result = await response.json();
    setTimeout(() => {
      displayResults(result.results || []);
    }, 600);
  } catch (error) {
    console.error("Error fetching documents:", error);
    resultsFrame.innerHTML = `<p style="color:red;">Failed to fetch results</p>`;
  }
}

async function fetchAndDisplayFileCounts() {
  try {
    const res = await fetch("http://127.0.0.1:5005/count_files", {
      method: "POST"
    });

    const data = await res.json();
    console.log("📦 File counts from backend:", data);

    const folderCards = document.querySelectorAll(".folder-card");

    folderCards.forEach(card => {
      const folderName = card.querySelector("strong").textContent.trim();
      const countSpan = card.querySelector(".found");

      if (data[folderName] !== undefined) {
        countSpan.textContent = `${data[folderName]} Found`;
      } else {
        countSpan.textContent = "0 Found";
      }
    });

  } catch (error) {
    console.error("❌ Error fetching file counts:", error);
  }
}

// ✅ Combined DOMContentLoaded hook
document.addEventListener("DOMContentLoaded", () => {
  fetchAndDisplayFileCounts();
  document.getElementById("searchBtn").addEventListener("click", searchDocuments);
  document.getElementById("searchInput").addEventListener("keypress", function (e) {
    if (e.key === "Enter") searchDocuments();
  });
});
