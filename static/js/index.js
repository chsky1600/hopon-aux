setInterval(function() {
    window.location.reload();
}, 180000);

function startGlobalCountdown() {
    let timeLeft = 1800; 

    function updateCountdown() {
        const countdownElement = document.getElementById("countdown-timer");
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;

        countdownElement.innerHTML = `New QR Code in: ${minutes}m ${seconds}s`;

        if (timeLeft <= 0) {
            clearInterval(interval);
            countdownElement.innerHTML = "Generating new QR code...";
        } else {
            timeLeft--;
        }
    }

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);

    // Reset the timer every 60 seconds
    setInterval(() => {
        clearInterval(interval);
        startGlobalCountdown();
    }, 60000);
}

function copyQrCode(url) {
    navigator.clipboard.writeText(url).then(function() {
        alert('Link copied to clipboard!');
    }, function(err) {
        console.error('Could not copy text: ', err);
    });
}


// Start the global countdown timer
window.onload = startGlobalCountdown;