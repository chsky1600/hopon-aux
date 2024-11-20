// index.js

setInterval(function() {
    window.location.reload();
}, 180000);

let timeLeft = remainingTime || 0; // Fallback to 0 if remainingTime is null or undefined

// Function to start and manage the countdown timer
function startGlobalCountdown() {
    const countdownElement = document.getElementById("countdown-timer");

    // Function to update the countdown every second
    function updateCountdown() {
        if (!countdownElement) {
            console.error("Countdown timer element not found!");
            return;
        }

        // If time is up, display expiration message
        if (timeLeft <= 0) {
            countdownElement.innerHTML = "Token has expired!";
            clearInterval(interval); // Stop the countdown
            return;
        }

        // Calculate minutes and seconds
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;

        // Update the DOM with the remaining time
        countdownElement.innerHTML = `Token expires in: ${minutes}m ${seconds}s`;

        // Decrease the remaining time by 1 second
        timeLeft -= 1;
    }

    // Start the countdown immediately and update every second
    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
}

function copyQrCode(url) {
    navigator.clipboard.writeText(url).then(function() {
        alert('Link copied to clipboard!');
    }, function(err) {
        console.error('Could not copy text: ', err);
    });
}

function addScannerToList(name) {
    const list = document.getElementById('active-scanners-list');
    if (list) {
        const listItem = document.createElement('li');
        listItem.className = 'text-blue-500';
        listItem.textContent = name;
        list.appendChild(listItem);
    }

    window.location.reload();
}

window.onload = function() {
    startGlobalCountdown();
};