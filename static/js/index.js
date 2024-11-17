// index.js

setInterval(function() {
    window.location.reload();
}, 180000);

function startGlobalCountdown() {
    let serverExpiration = tokenExpiration;
    const storedExpiration = localStorage.getItem('tokenExpiration');
    const currentTime = Date.now() / 1000;

    let timeLeft;

    if (storedExpiration !== String(serverExpiration)) {
        timeLeft = serverExpiration - currentTime;
        timeLeft = timeLeft > 0 ? Math.floor(timeLeft) : 0;
        localStorage.setItem('tokenExpiration', serverExpiration);
        localStorage.setItem('timeLeft', timeLeft);
    } else {
        timeLeft = localStorage.getItem('timeLeft') ? parseInt(localStorage.getItem('timeLeft')) : serverExpiration - currentTime;
        timeLeft = timeLeft > 0 ? Math.floor(timeLeft) : 0;
    }

    localStorage.setItem('timeLeft', timeLeft);

    function updateCountdown() {
        const countdownElement = document.getElementById("countdown-timer");
        if (!countdownElement) return;

        const currentTime = Date.now() / 1000;
        timeLeft = Math.floor(serverExpiration - currentTime);

        if (timeLeft < 0) {
            timeLeft = 0;
        }

        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;

        countdownElement.innerHTML = `New QR Code in: ${minutes}m ${seconds}s`;

        if (timeLeft <= 0) {
            clearInterval(interval);
            countdownElement.innerHTML = "Generating new QR code...";
            localStorage.removeItem('timeLeft');
            localStorage.removeItem('tokenExpiration');
        } else {
            timeLeft--;
            localStorage.setItem('timeLeft', timeLeft);
        }
    }

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);

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