function showMyShips() {
    // Already on ships view, maybe filter or scroll to ships section
    document.querySelector('.ships-grid').scrollIntoView({ behavior: 'smooth' });
}

function showReports() {
    alert('Ship reports feature coming soon');
}

function requestAccess() {
    alert('Contact your company administrator to request access to additional ships');
}

function viewShipOnMap(mmsi) {
    window.location.href = '/map?highlight=' + mmsi;
}

function showShipDetails(mmsi) {
    alert('Detailed ship information for MMSI: ' + mmsi + ' coming soon');
}

// Auto-refresh every 30 seconds
setInterval(function() {
    location.reload();
}, 30000);