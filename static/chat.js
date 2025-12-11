const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");
const chatBox = document.getElementById("chat-box");
const typing = document.getElementById("typing");

function scrollChat() {
    chatBox.scrollTop = chatBox.scrollHeight;
}

function showTyping() {
    typing.style.display = "block";
    scrollChat();
}

function hideTyping() {
    typing.style.display = "none";
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const msg = input.value.trim();
    if (!msg) return;

    chatBox.innerHTML += `
        <div class="msg user-msg"><strong>You:</strong> ${msg}</div>
    `;
    scrollChat();
    input.value = "";

    showTyping();

    const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg })
    });

    const data = await res.json();
    hideTyping();

    chatBox.innerHTML += `
        <div class="msg bot-msg"><strong>Harsha:</strong> ${data.reply}</div>
    `;
    scrollChat();

    // Speak output
    speak(data.reply);
});
