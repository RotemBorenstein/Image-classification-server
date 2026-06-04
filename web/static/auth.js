const TOKEN_KEY = "picture_server_token";

const tabButtons = document.querySelectorAll("[data-tab-target]");
const tabPanels = document.querySelectorAll(".tab-panel");
const feedback = document.getElementById("auth-feedback");
const resumeButton = document.getElementById("resume-session");

function setFeedback(message, kind) {
    feedback.textContent = message || "";
    feedback.className = "feedback";

    if (!message) {
        return;
    }

    feedback.classList.add("is-visible", kind === "error" ? "is-error" : "is-success");
}

function selectTab(targetId) {
    tabButtons.forEach((button) => {
        const active = button.dataset.tabTarget === targetId;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-selected", String(active));
    });

    tabPanels.forEach((panel) => {
        const active = panel.id === targetId;
        panel.classList.toggle("is-active", active);
        panel.hidden = !active;
    });
}

async function sendAuthRequest(path, payload) {
    const response = await fetch(path, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    const data = await response.json();
    return { response, data };
}

async function handleLogin(event) {
    event.preventDefault();
    setFeedback("Signing in...", "success");

    const formData = new FormData(event.currentTarget);
    const payload = Object.fromEntries(formData.entries());

    try {
        const { response, data } = await sendAuthRequest("/login", payload);

        if (!response.ok) {
            throw new Error(data.error?.message || "Login failed");
        }

        sessionStorage.setItem(TOKEN_KEY, data.token);
        setFeedback("Login successful. Redirecting to upload page...", "success");
        window.location.href = "/upload";
    } catch (error) {
        setFeedback(error.message, "error");
    }
}

async function handleRegister(event) {
    event.preventDefault();
    setFeedback("Creating account...", "success");

    const form = event.currentTarget;
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());

    try {
        const { response, data } = await sendAuthRequest("/register", payload);

        if (!response.ok) {
            throw new Error(data.error?.message || "Registration failed");
        }

        setFeedback("Registration successful. You can now log in.", "success");
        form.reset();
        selectTab("login-panel");
    } catch (error) {
        setFeedback(error.message, "error");
    }
}

tabButtons.forEach((button) => {
    button.addEventListener("click", () => selectTab(button.dataset.tabTarget));
});

document.getElementById("login-form").addEventListener("submit", handleLogin);
document.getElementById("register-form").addEventListener("submit", handleRegister);

if (sessionStorage.getItem(TOKEN_KEY)) {
    resumeButton.hidden = false;
    resumeButton.addEventListener("click", () => {
        window.location.href = "/upload";
    });
}
