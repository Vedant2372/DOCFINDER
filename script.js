document.addEventListener("DOMContentLoaded", async function () {
  console.log("✅ Script loaded successfully");

  // ✅ Step 1: Check backend state to auto-redirect returning users or trigger full scan
  try {
    const statusRes = await fetch("http://127.0.0.1:5005/task", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "status" }),
    });

    const statusData = await statusRes.json();

    const alreadyAccepted = statusData?.termsAccepted;
    const indexExists = statusData?.indexExists;
    const jobStatus = statusData?.job?.status;
    
    if (
      alreadyAccepted &&
      indexExists &&
      (jobStatus === "done" || jobStatus === "idle") 
      /*localStorage.getItem("accepted") === "yes"*/
     ) {
      console.log("✅ User has already accepted & indexed. Skipping terms and redirecting to result.html...");
      window.location.href = "result.html";
      return;
    } else if (!alreadyAccepted || !indexExists) {
      console.log("🆕 First time user. Triggering scan directly...");

      // 🔁 Only trigger auto-accept if not already done
      if (!localStorage.getItem("accepted")) {
        await fetch("http://127.0.0.1:5005/task", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "accept" }),
        });
        localStorage.setItem("accepted", "yes");
        console.log("✅ Auto-accept triggered.");
      }

      pollScanStatusAndRedirect();
    }
  } catch (err) {
    console.error("⚠️ Could not check backend scan status:", err);
  }

  // 📝 TERMS MODAL
  const termsModal = document.getElementById("termsModal");
  const startBtn = document.querySelector(".start-button");
  const closeTermsBtn = document.querySelector(".close-btn");

  if (startBtn && termsModal && closeTermsBtn) {
  startBtn.addEventListener("click", function (event) {
    event.preventDefault();

    // ✅ Skip terms modal for returning user
    if (localStorage.getItem("accepted") === "yes") {
      console.log("✅ Terms already accepted — skipping modal and redirecting...");
      window.location.href = "result.html";
      return;
    }

    // 🆕 Show terms for first-time user
    termsModal.style.display = "block";
    console.log("📝 Terms modal opened");
  });

    closeTermsBtn.addEventListener("click", function () {
      termsModal.style.display = "none";
      console.log("❌ Terms modal closed");
    });

    window.addEventListener("click", function (e) {
      if (e.target === termsModal) {
        termsModal.style.display = "none";
        console.log("❌ Terms modal closed (clicked outside)");
      }
    });
  }

  // ℹ️ ABOUT MODAL
  const aboutModal = document.getElementById("aboutModal");
  const aboutBtn = document.getElementById("aboutBtn");
  const aboutClose = aboutModal?.querySelector(".close");

  if (aboutBtn && aboutModal && aboutClose) {
    aboutBtn.addEventListener("click", function () {
      aboutModal.style.display = "block";
      console.log("ℹ️ About modal opened");
    });

    aboutClose.addEventListener("click", function () {
      aboutModal.style.display = "none";
      console.log("ℹ️ About modal closed");
    });

    window.addEventListener("click", function (event) {
      if (event.target === aboutModal) {
        aboutModal.style.display = "none";
        console.log("ℹ️ About modal closed (clicked outside)");
      }
    });
  }

  // ✅ PROCEED BUTTON
  const proceedBtn = document.querySelector(".proceed-btn");
  const checkbox = document.getElementById("acceptCheckbox");

  if (proceedBtn && checkbox) {
    proceedBtn.addEventListener("click", async function () {
      if (!checkbox.checked) {
        alert("❗ Please accept the terms to proceed.");
        console.warn("❌ Terms not accepted — closing app.");
        window.close();
        return;
      }

      console.log("✅ Terms accepted. Proceeding to scan...");

      termsModal.style.display = "none";
      document.querySelector(".main-content").style.display = "none";
      document.getElementById("homepage").style.display = "flex";

      console.log("🔄 Triggering scan from backend...");

      try {
        const res = await fetch("http://127.0.0.1:5005/task", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "accept" }),
        });

        const data = await res.json();
        console.log("✅ Scan triggered:", data.message);

        // ✅ Start polling scan status
        pollScanStatusAndRedirect();
      } catch (err) {
        console.error("🚨 Failed to trigger scan:", err);
        alert("Something went wrong while scanning.");
      }
    });
  }

  // 🔁 Poll until scan is done, then redirect
  function pollScanStatusAndRedirect() {
    const interval = setInterval(async () => {
      try {
        const res = await fetch("http://127.0.0.1:5005/task", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "status" }),
        });

        const data = await res.json();
        const jobStatus = data?.job?.status;

        console.log("📡 Polling Status:", jobStatus);

        if (jobStatus === "done" || jobStatus === "idle") {
          clearInterval(interval);
          console.log("✅ Scan complete or already done. Redirecting...");
          window.location.href = "result.html";
        }

        if (jobStatus === "error") {
          clearInterval(interval);
          alert("❌ Scan failed. Please try again.");
        }
      } catch (err) {
        console.error("❌ Error polling scan status:", err);
      }
    }, 3000);
  }
});
