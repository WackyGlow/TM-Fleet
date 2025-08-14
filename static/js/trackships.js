// Track Ships JavaScript
// Handles all functionality for the track ships page

// Global variables
let trackedShips = [];
let allShips = [];
let currentPage = 1;
let shipsPerPage = 50;
let totalShips = 0;
let sortField = 'ship_name';
let sortDirection = 'asc';
let currentSearch = '';
let isSearchMode = false;

// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeTrackShipsPage();
});

// Initialize the track ships page
function initializeTrackShipsPage() {
    loadTrackedShips();
    loadAllShips();
    setupEventListeners();
}

// Setup event listeners
function setupEventListeners() {
    // Search on Enter key
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchShips();
        }
    });

    // Search on input with debounce
    let searchTimeout;
    document.getElementById('searchInput').addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        const query = e.target.value.trim();

        if (query === '') {
            clearSearch();
        } else {
            searchTimeout = setTimeout(() => {
                searchShips();
            }, 500); // Debounce for 500ms
        }
    });

    // Manual add form submission
    document.getElementById('manualAddForm').addEventListener('submit', function(e) {
        e.preventDefault();
        addShipManually();
    });
}

// ======================
// TRACKED SHIPS FUNCTIONS
// ======================

// Load tracked ships
async function loadTrackedShips() {
    const loading = document.getElementById('trackedLoading');
    const container = document.getElementById('trackedShipsContainer');
    const table = document.getElementById('trackedShipsTable');
    const noShips = document.getElementById('noTrackedShips');
    const tbody = document.getElementById('trackedShipsBody');

    loading.style.display = 'block';

    try {
        const response = await fetch('/api/tracked-ships');
        const data = await response.json();

        trackedShips = data.tracked_ships || [];

        loading.style.display = 'none';

        if (trackedShips.length === 0) {
            table.style.display = 'none';
            noShips.style.display = 'block';
        } else {
            table.style.display = 'table';
            noShips.style.display = 'none';

            tbody.innerHTML = '';
            trackedShips.forEach(ship => {
                const row = createTrackedShipRow(ship);
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        loading.style.display = 'none';
        showMessage('trackedMessage', 'Error loading tracked ships: ' + error.message, 'error');
    }
}

// Create tracked ship table row
function createTrackedShipRow(ship) {
    const row = document.createElement('tr');

    const shipData = ship.ship_data || {};
    const lastSeen = shipData.last_seen ? new Date(shipData.last_seen).toLocaleString() : 'Unknown';
    const isActive = shipData.last_seen && (Date.now() - new Date(shipData.last_seen).getTime()) < 3600000; // 1 hour
    const shipName = ship.name || shipData.ship_name || 'Unknown';
    const shipType = getShipTypeName(shipData.ship_type);

    row.innerHTML = `
        <td>${ship.mmsi}</td>
        <td>${shipName}</td>
        <td>${shipType}</td>
        <td>${lastSeen}</td>
        <td class="${isActive ? 'status-active' : 'status-inactive'}">
            ${isActive ? '● Active' : '○ Inactive'}
        </td>
        <td>${ship.notes || '-'}</td>
        <td>
            <button onclick="editTrackedShip('${ship.mmsi}')" class="btn btn-primary btn-small">Edit</button>
            <button onclick="removeTrackedShip('${ship.mmsi}')" class="btn btn-danger btn-small">Remove</button>
            <div id="edit-${ship.mmsi}" class="edit-form">
                <input type="text" id="editName-${ship.mmsi}" value="${ship.name || ''}" placeholder="Name">
                <textarea id="editNotes-${ship.mmsi}" placeholder="Notes">${ship.notes || ''}</textarea>
                <button onclick="saveTrackedShip('${ship.mmsi}')" class="btn btn-success btn-small">Save</button>
                <button onclick="cancelEdit('${ship.mmsi}')" class="btn btn-secondary btn-small">Cancel</button>
            </div>
        </td>
    `;

    return row;
}

// Edit tracked ship
function editTrackedShip(mmsi) {
    const editForm = document.getElementById(`edit-${mmsi}`);
    editForm.style.display = editForm.style.display === 'none' ? 'block' : 'none';
}

// Save tracked ship changes
async function saveTrackedShip(mmsi) {
    const name = document.getElementById(`editName-${mmsi}`).value.trim() || null;
    const notes = document.getElementById(`editNotes-${mmsi}`).value.trim() || null;

    try {
        const response = await fetch(`/api/tracked-ships/${mmsi}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, notes })
        });

        const result = await response.json();

        if (result.success) {
            showMessage('trackedMessage', 'Ship updated successfully!', 'success');
            loadTrackedShips(); // Refresh the list
        } else {
            showMessage('trackedMessage', result.message, 'error');
        }
    } catch (error) {
        showMessage('trackedMessage', 'Error updating ship: ' + error.message, 'error');
    }
}

// Cancel edit
function cancelEdit(mmsi) {
    const editForm = document.getElementById(`edit-${mmsi}`);
    editForm.style.display = 'none';
}

// Remove tracked ship
async function removeTrackedShip(mmsi) {
    if (!confirm(`Are you sure you want to stop tracking ship ${mmsi}?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/tracked-ships/${mmsi}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            showMessage('trackedMessage', `Ship ${mmsi} removed from tracking!`, 'success');
            loadTrackedShips(); // Refresh the list
        } else {
            showMessage('trackedMessage', result.message, 'error');
        }
    } catch (error) {
        showMessage('trackedMessage', 'Error removing ship: ' + error.message, 'error');
    }
}

// ======================
// ALL SHIPS FUNCTIONS
// ======================

// Load all ships with pagination and optional search
async function loadAllShips(page = 1, searchQuery = '') {
    const loading = document.getElementById('allShipsLoading');
    const container = document.getElementById('allShipsContainer');
    const tbody = document.getElementById('allShipsBody');

    loading.style.display = 'block';
    container.style.display = 'none';

    try {
        let url = `/api/ships/all?page=${page}&per_page=${shipsPerPage}&sort=${sortField}&direction=${sortDirection}`;

        if (searchQuery) {
            url += `&search=${encodeURIComponent(searchQuery)}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        allShips = data.ships || [];
        totalShips = data.total || 0;
        currentPage = page;
        currentSearch = searchQuery;
        isSearchMode = !!searchQuery;

        loading.style.display = 'none';
        container.style.display = 'block';

        // Update pagination info
        updatePaginationInfo();
        updatePaginationButtons();

        // Populate table
        tbody.innerHTML = '';
        if (allShips.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; color: #6b7280; padding: 20px; font-style: italic;">
                        ${searchQuery ? `No ships found matching "${searchQuery}"` : 'No ships found'}
                    </td>
                </tr>
            `;
        } else {
            allShips.forEach(ship => {
                const row = createAllShipsRow(ship);
                tbody.appendChild(row);
            });
        }

        // Update sort indicators
        updateSortIndicators();

        // Update search status
        if (searchQuery) {
            showMessage('allShipsMessage', `Search results for "${searchQuery}" - ${totalShips} ships found`, 'success');
        } else {
            hideMessage('allShipsMessage');
        }

    } catch (error) {
        loading.style.display = 'none';
        showMessage('allShipsMessage', 'Error loading ships: ' + error.message, 'error');
    }
}

// Create row for all ships table (updated column order)
function createAllShipsRow(ship) {
    const row = document.createElement('tr');

    const lastSeen = ship.last_seen ? new Date(ship.last_seen).toLocaleString() : 'Unknown';
    const isActive = ship.last_seen && (Date.now() - new Date(ship.last_seen).getTime()) < 3600000; // 1 hour
    const shipName = ship.ship_name || 'Unknown';
    const shipType = getShipTypeName(ship.ship_type);
    const isTracked = ship.is_tracked;
    const imo = ship.imo || 'Unknown';

    row.innerHTML = `
        <td><strong>${shipName}</strong></td>
        <td>${ship.mmsi}</td>
        <td>${imo}</td>
        <td>${shipType}</td>
        <td>${lastSeen}</td>
        <td class="${isActive ? 'status-active' : 'status-inactive'}">
            ${isActive ? '● Active' : '○ Inactive'}
        </td>
        <td>
            ${isTracked ? 
                `<span style="color: #dc2626; font-size: 12px;">● Tracked</span>` :
                `<button onclick="addShipFromList('${ship.mmsi}')" class="btn btn-success btn-small">Track</button>`
            }
        </td>
    `;

    return row;
}

// Add ship from all ships list
async function addShipFromList(mmsi) {
    const ship = allShips.find(s => s.mmsi === mmsi);
    if (!ship) return;

    try {
        const response = await fetch('/api/tracked-ships', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mmsi: mmsi,
                name: ship.ship_name || '',
                notes: `Added from ship list on ${new Date().toLocaleString()}`,
                added_by: 'User'
            })
        });

        const result = await response.json();

        if (result.success) {
            showMessage('allShipsMessage', `Ship ${mmsi} added to tracking!`, 'success');
            loadTrackedShips(); // Refresh tracked ships list
            loadAllShips(currentPage, currentSearch); // Refresh all ships list to update button
        } else {
            showMessage('allShipsMessage', result.message, 'error');
        }
    } catch (error) {
        showMessage('allShipsMessage', 'Error adding ship: ' + error.message, 'error');
    }
}

// ======================
// SEARCH FUNCTIONS
// ======================

// Search ships (now integrated with main list)
function searchShips() {
    const query = document.getElementById('searchInput').value.trim();
    currentPage = 1; // Reset to first page when searching
    loadAllShips(1, query);
}

// Clear search function
function clearSearch() {
    document.getElementById('searchInput').value = '';
    currentPage = 1;
    loadAllShips(1, ''); // Load without search
}

// ======================
// PAGINATION FUNCTIONS
// ======================

// Update pagination info
function updatePaginationInfo() {
    const info = document.getElementById('paginationInfo');
    const start = (currentPage - 1) * shipsPerPage + 1;
    const end = Math.min(currentPage * shipsPerPage, totalShips);
    const searchText = isSearchMode ? ' (filtered)' : '';
    info.textContent = `Showing ${start}-${end} of ${totalShips} ships${searchText}`;
}

// Update pagination buttons
function updatePaginationButtons() {
    const container = document.getElementById('paginationButtons');
    const totalPages = Math.ceil(totalShips / shipsPerPage);

    let html = '';

    // Previous button
    html += `<button onclick="goToPage(${currentPage - 1})" ${currentPage <= 1 ? 'disabled' : ''}>‹ Prev</button>`;

    // Page numbers (show 5 pages around current)
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);

    if (startPage > 1) {
        html += `<button onclick="goToPage(1)">1</button>`;
        if (startPage > 2) html += '<span style="padding: 0 5px;">...</span>';
    }

    for (let i = startPage; i <= endPage; i++) {
        html += `<button onclick="goToPage(${i})" ${i === currentPage ? 'class="active"' : ''}>${i}</button>`;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) html += '<span style="padding: 0 5px;">...</span>';
        html += `<button onclick="goToPage(${totalPages})">${totalPages}</button>`;
    }

    // Next button
    html += `<button onclick="goToPage(${currentPage + 1})" ${currentPage >= totalPages ? 'disabled' : ''}>Next ›</button>`;

    container.innerHTML = html;
}

// Go to specific page
function goToPage(page) {
    if (page >= 1 && page <= Math.ceil(totalShips / shipsPerPage)) {
        loadAllShips(page, currentSearch);
    }
}

// Change ships per page
function changeShipsPerPage() {
    shipsPerPage = parseInt(document.getElementById('shipsPerPage').value);
    currentPage = 1; // Reset to first page
    loadAllShips(1, currentSearch);
}

// ======================
// SORTING FUNCTIONS
// ======================

// Sort ships by field
function sortShips(field) {
    if (sortField === field) {
        // Toggle direction if same field
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        // New field, default to ascending except for dates
        sortField = field;
        sortDirection = field === 'last_seen' ? 'desc' : 'asc';
    }

    currentPage = 1; // Reset to first page when sorting
    loadAllShips(1, currentSearch);
}

// Update sort indicators
function updateSortIndicators() {
    // Reset all indicators
    document.querySelectorAll('[id^="sort-"]').forEach(el => {
        el.textContent = '⇅';
        el.style.color = '#6b7280';
    });

    // Set active indicator
    const activeIndicator = document.getElementById(`sort-${sortField}`);
    if (activeIndicator) {
        activeIndicator.textContent = sortDirection === 'asc' ? '↑' : '↓';
        activeIndicator.style.color = '#1e3c72';
    }
}

// ======================
// MANUAL ADD FUNCTIONS
// ======================

// Add ship manually
async function addShipManually() {
    const form = document.getElementById('manualAddForm');
    const formData = new FormData(form);

    const data = {
        mmsi: formData.get('mmsi').trim(),
        name: formData.get('name').trim() || null,
        notes: formData.get('notes').trim() || null,
        added_by: 'User'
    };

    try {
        const response = await fetch('/api/tracked-ships', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            showMessage('manualMessage', `Ship ${data.mmsi} added to tracking!`, 'success');
            form.reset();
            loadTrackedShips(); // Refresh tracked ships list
        } else {
            showMessage('manualMessage', result.message, 'error');
        }
    } catch (error) {
        showMessage('manualMessage', 'Error adding ship: ' + error.message, 'error');
    }
}

// ======================
// UTILITY FUNCTIONS
// ======================

// Show message
function showMessage(elementId, message, type) {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.textContent = message;
    element.className = `message ${type}`;
    element.style.display = 'block';

    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            element.style.display = 'none';
        }, 5000);
    }
}

// Hide message
function hideMessage(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.style.display = 'none';
    }
}

// Get ship type name from AIS ship type code
function getShipTypeName(shipType) {
    if (!shipType) return 'Unknown';

    const shipTypes = {
        30: 'Fishing',
        31: 'Towing',
        32: 'Towing (large)',
        33: 'Dredging/Underwater operations',
        34: 'Diving operations',
        35: 'Military operations',
        36: 'Sailing',
        37: 'Pleasure craft',
        40: 'High speed craft (HSC)',
        41: 'HSC - Hazardous category A',
        42: 'HSC - Hazardous category B',
        43: 'HSC - Hazardous category C',
        44: 'HSC - Hazardous category D',
        50: 'Pilot vessel',
        51: 'Search and rescue vessel',
        52: 'Tug',
        53: 'Port tender',
        54: 'Anti-pollution equipment',
        55: 'Law enforcement',
        56: 'Spare - Local vessel',
        57: 'Spare - Local vessel',
        58: 'Medical transport',
        59: 'Noncombatant ship',
        60: 'Passenger',
        61: 'Passenger - Hazardous category A',
        62: 'Passenger - Hazardous category B',
        63: 'Passenger - Hazardous category C',
        64: 'Passenger - Hazardous category D',
        70: 'Cargo',
        71: 'Cargo - Hazardous category A',
        72: 'Cargo - Hazardous category B',
        73: 'Cargo - Hazardous category C',
        74: 'Cargo - Hazardous category D',
        80: 'Tanker',
        81: 'Tanker - Hazardous category A',
        82: 'Tanker - Hazardous category B',
        83: 'Tanker - Hazardous category C',
        84: 'Tanker - Hazardous category D',
        90: 'Other type',
        91: 'Other - Hazardous category A',
        92: 'Other - Hazardous category B',
        93: 'Other - Hazardous category C',
        94: 'Other - Hazardous category D'
    };

    return shipTypes[shipType] || `Type ${shipType}`;
}