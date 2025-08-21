function trackNewShip() {
    // This will be populated by the template based on stats.can_track_more
    alert('Ship tracking interface coming soon');
}

function showUpgrade() {
    alert('Upgrade options:\n\n🏢 Company Account: Unlimited tracking\n📞 Contact: sales@teemarine.dk');
}

function showHelp() {
    alert('SpyFleet Help:\n\n🆓 Free: Track up to 5 ships\n🏢 Company: Unlimited tracking\n🗺️ Use the map to find and track ships');
}

function viewShipOnMap(mmsi) {
    window.location.href = '/map?highlight=' + mmsi;
}

function editShip(mmsi) {
    alert('Edit ship tracking settings for MMSI: ' + mmsi);
}

function removeShip(mmsi) {
    if (confirm('Remove ship ' + mmsi + ' from your tracking list?')) {
        // TODO: Implement ship removal
        alert('Ship removal coming soon');
    }
}

// Auto-refresh every 30 seconds
setInterval(function() {
    location.reload();
}, 30000);