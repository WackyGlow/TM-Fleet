function showFleetManagement() {
    alert('Fleet management features coming soon');
}

function showCompanyUsers() {
    alert('Company user management coming soon');
}

function showReports() {
    alert('Fleet reports coming soon');
}

function showTrackShip() {
    alert('Ship tracking interface coming soon');
}

function viewShipOnMap(mmsi) {
    window.location.href = '/map?highlight=' + mmsi;
}

function editShip(mmsi) {
    alert('Edit ship: ' + mmsi);
}

function removeShip(mmsi) {
    if (confirm('Remove ship ' + mmsi + ' from tracking?')) {
        // TODO: Implement ship removal
        alert('Ship removal coming soon');
    }
}

// Auto-refresh every 30 seconds
setInterval(function() {
    location.reload();
}, 30000);