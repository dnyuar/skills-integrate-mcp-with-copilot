document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const teacherRequired = document.getElementById("teacher-required");
  const authButton = document.getElementById("teacher-auth-button");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginMessage = document.getElementById("login-message");
  let teacher = null;

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => {
      const entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      };
      return entities[character];
    });
  }

  function setTeacher(username) {
    teacher = username;
    const signedIn = teacher !== null;
    signupForm.classList.toggle("hidden", !signedIn);
    teacherRequired.classList.toggle("hidden", signedIn);
    authButton.textContent = signedIn
      ? `👤 ${teacher} · Sign out`
      : "👤 Teacher sign in";
  }

  function showMessage(element, text, type) {
    element.textContent = text;
    element.className = type;
    setTimeout(() => element.classList.add("hidden"), 5000);
  }

  async function fetchAuthSession() {
    const response = await fetch("/auth/session");
    if (!response.ok) {
      throw new Error("Unable to check teacher sign-in status");
    }
    const session = await response.json();
    setTeacher(session.authenticated ? session.username : null);
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error("Unable to load activities");
      }
      const activities = await response.json();

      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(activitySelect.options[0]);

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) =>
                      `<li><span class="participant-email">${escapeHtml(
                        email
                      )}</span>${
                        teacher
                          ? `<button class="delete-btn" data-activity="${escapeHtml(
                              name
                            )}" data-email="${escapeHtml(
                              email
                            )}" aria-label="Unregister ${escapeHtml(
                              email
                            )} from ${escapeHtml(name)}">❌</button>`
                          : ""
                      }</li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : "<p><em>No participants yet</em></p>";

        activityCard.innerHTML = `
          <h4>${escapeHtml(name)}</h4>
          <p>${escapeHtml(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHtml(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE" }
      );
      const result = await response.json();

      if (response.ok) {
        showMessage(messageDiv, result.message, "success");
        await fetchActivities();
      } else {
        showMessage(messageDiv, result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage(
        messageDiv,
        "Failed to unregister. Please try again.",
        "error"
      );
      console.error("Error unregistering:", error);
    }
  }

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = activitySelect.value;
    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        { method: "POST" }
      );
      const result = await response.json();

      if (response.ok) {
        showMessage(messageDiv, result.message, "success");
        signupForm.reset();
        await fetchActivities();
      } else {
        showMessage(messageDiv, result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage(
        messageDiv,
        "Failed to sign up. Please try again.",
        "error"
      );
      console.error("Error signing up:", error);
    }
  });

  authButton.addEventListener("click", async () => {
    if (teacher) {
      try {
        const response = await fetch("/auth/logout", { method: "POST" });
        if (!response.ok) {
          throw new Error("Unable to sign out");
        }
        setTeacher(null);
        await fetchActivities();
      } catch (error) {
        showMessage(messageDiv, "Failed to sign out. Please try again.", "error");
        console.error("Error signing out:", error);
      }
      return;
    }

    loginMessage.className = "hidden";
    loginForm.reset();
    loginDialog.showModal();
  });

  document.getElementById("close-login").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const credentials = {
      username: document.getElementById("username").value,
      password: document.getElementById("password").value,
    };

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });
      const result = await response.json();
      if (!response.ok) {
        loginMessage.textContent = result.detail || "Unable to sign in";
        loginMessage.className = "error";
        return;
      }

      loginForm.reset();
      loginDialog.close();
      setTeacher(result.username);
      await fetchActivities();
    } catch (error) {
      loginMessage.textContent = "Failed to sign in. Please try again.";
      loginMessage.className = "error";
      console.error("Error signing in:", error);
    }
  });

  async function initialize() {
    try {
      await fetchAuthSession();
      await fetchActivities();
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to initialize the application. Please try again later.</p>";
      console.error("Error initializing app:", error);
    }
  }

  initialize();
});
