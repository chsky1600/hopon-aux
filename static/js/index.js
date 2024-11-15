setInterval(function() {
    window.location.reload();
}, 180000);

function startGlobalCountdown() {
    let timeLeft = localStorage.getItem('timeLeft') ? parseInt(localStorage.getItem('timeLeft')) : 1800;

    function updateCountdown() {
        const countdownElement = document.getElementById("countdown-timer");
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;

        countdownElement.innerHTML = `New QR Code in: ${minutes}m ${seconds}s`;

        if (timeLeft <= 0) {
            clearInterval(interval);
            countdownElement.innerHTML = "Generating new QR code...";
            localStorage.removeItem('timeLeft');
        } else {
            timeLeft--;
            localStorage.setItem('timeLeft', timeLeft);
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

function addScannerToList(name) {
    window.location.reload();
    const list = document.getElementById('active-scanners-list');
    const listItem = document.createElement('li');
    listItem.className = 'text-blue-500';
    listItem.textContent = name;
    list.appendChild(listItem);
}

window.onload = function() {
    localStorage.removeItem('timeLeft'); 
    startGlobalCountdown();
};