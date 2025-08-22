document.addEventListener("DOMContentLoaded", async () => {
  console.log("📂 Render loaded");

  // ✅ Ensure backend is ready before searching
  const status = await fetchStatus();
  if (!status?.termsAccepted) {
    console.warn("🔓 Terms not accepted — sending auto-accept");

    if (!localStorage.getItem("accepted")) {
      try {
        await fetch("http://127.0.0.1:5005/task", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "accept" }),
        });
        localStorage.setItem("accepted", "yes");
        console.log("✅ Auto-accept sent from render.js");
      } catch (err) {
        console.error("❌ Auto-accept failed:", err);
      }
    }
  }

  const results = await fetchAllFiles();
  renderResults(results);
});

// ✅ Helper to check scan/terms state
async function fetchStatus() {
  try {
    const response = await fetch("http://127.0.0.1:5005/task", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "status" }),
    });
    return await response.json();
  } catch (e) {
    console.error("❌ Failed to fetch status:", e);
    return null;
  }
}

// ✅ Run a blank search
async function fetchAllFiles() {
  try {
    const response = await fetch("http://127.0.0.1:5005/task", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "search", q: " " })
    });

    const result = await response.json();
    console.log("📁 Search Results:", result);

    if (result.results) return result.results;
    return [];
  } catch (err) {
    console.error("❌ Fetching files failed:", err);
    return [];
  }
}

// ✅ Display results in UI
function renderResults(results) {
  const container = document.getElementById("results");
  container.innerHTML = "";

  if (!results.length) {
    container.innerHTML = " ";
    return;
  }

  results.forEach(file => {
    const div = document.createElement("div");
    div.className = "file-card";
    div.innerHTML = `
      <p><strong>${file.filename}</strong></p>
      <p>${file.path}</p>
      <button class="open-btn" data-path="${file.path}">Open</button>
    `;
    container.appendChild(div);
  });

  document.querySelectorAll(".open-btn").forEach(button => {
    button.addEventListener("click", (e) => {
      const path = e.target.getAttribute("data-path");
      console.log("📂 Opening:", path);
      window.electronAPI.openFile(path);
    });
  });
}
