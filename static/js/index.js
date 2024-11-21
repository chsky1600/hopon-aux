setInterval(function() {
    window.location.reload();
}, 180000);

let timeLeft = remainingTime || 0; // fallback to 0 if remainingTime is null or undefined

function startGlobalCountdown() {
    const countdownElement = document.getElementById("countdown-timer");

    function updateCountdown() {
        if (!countdownElement) {
            console.error("Countdown timer element not found!");
            return;
        }

        // if time is up display expiration message
        if (timeLeft <= 0) {
            countdownElement.innerHTML = "QR code has expired!";
            clearInterval(interval); // Stop the countdown
            return;
        }

        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;

        // update DOM with remaining time
        countdownElement.innerHTML = `Expires in: ${minutes}m ${seconds}s`;

        // decrease the remaining time by 1 sec
        timeLeft -= 1;
    }

    // start the countdown immediately and update every sec
    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
}

function fetchTTLAndUpdateTimer() {
    console.log('Fetching TTL...');
    fetch('/get_ttl')
        .then(response => response.json())
        .then(data => {
            console.log('\nTTL Data:', data.ttl, '\n');
            if (data.ttl) {
                localStorage.setItem('timeLeft', data.ttl);
                window.location.reload();
            }
        })
        .catch(error => console.error('Error fetching TTL:', error));
}

function copyQrCode(url) {
    navigator.clipboard.writeText(url).then(function() {
        alert('Link copied to clipboard!');
        fetchTTLAndUpdateTimer();
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