// Voice Input
window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

const recognizer = new window.SpeechRecognition();
recognizer.lang = "en-IN";

function startVoice() {
    recognizer.start();
}

recognizer.onresult = function(event) {
    document.getElementById("user-input").value = event.results[0][0].transcript;
};

// Voice Output
function speak(text) {
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "en-IN";
    speechSynthesis.speak(utter);
}
