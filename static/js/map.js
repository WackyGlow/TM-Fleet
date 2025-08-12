const map = L.map('map').setView([55.46, 8.45], 12); // Esbjerg

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 18,
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        const shipMarkers = {};
        const shipLabels = {};

        // Function to open ship details sidebar
        function openShipSidebar(mmsi, shipData, shipDetail) {
            const sidebar = document.getElementById('shipSidebar');
            const title = document.getElementById('sidebarTitle');
            const content = document.getElementById('sidebarContent');

            const shipName = shipDetail.ship_name ? shipDetail.ship_name.trim().replace(/@/g, '') : 'Unknown Vessel';
            title.textContent = shipName;

            // Check if coordinates are valid (database uses latitude/longitude)
            const lat = (shipData && typeof shipData.latitude === 'number') ? shipData.latitude : null;
            const lon = (shipData && typeof shipData.longitude === 'number') ? shipData.longitude : null;

            let detailsHTML = `
                <div class="info-section">
                    <h3>Vessel Identity</h3>
                    <div class="info-row">
                        <span class="info-label">MMSI:</span>
                        <span class="info-value">${mmsi}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Name:</span>
                        <span class="info-value">${shipName}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">IMO:</span>
                        <span class="info-value">${shipDetail.imo || 'Unknown'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Callsign:</span>
                        <span class="info-value">${shipDetail.callsign || 'Unknown'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Ship Type:</span>
                        <span class="info-value">${getShipTypeName(shipDetail.ship_type)}</span>
                    </div>
                </div>

                <div class="info-section">
                    <h3>Position & Navigation</h3>
                    <div class="info-row">
                        <span class="info-label">Latitude:</span>
                        <span class="info-value">${lat !== null ? lat.toFixed(6) + '°' : 'Unknown'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Longitude:</span>
                        <span class="info-value">${lon !== null ? lon.toFixed(6) + '°' : 'Unknown'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Speed:</span>
                        <span class="info-value">${shipDetail.speed !== undefined && shipDetail.speed !== null ? shipDetail.speed + ' knots' : 'Unknown'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Course:</span>
                        <span class="info-value">${shipDetail.course !== undefined && shipDetail.course !== null ? shipDetail.course + '°' : 'Unknown'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Heading:</span>
                        <span class="info-value">${(shipDetail.heading !== undefined && shipDetail.heading !== null && shipDetail.heading !== 511) ? shipDetail.heading + '°' : 'Unknown'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Nav Status:</span>
                        <span class="info-value">${getNavStatusName(shipDetail.nav_status)}</span>
                    </div>
                </div>

                <div class="info-section">
                    <h3>Vessel Details</h3>
                    <div class="info-row">
                        <span class="info-label">Destination:</span>
                        <span class="info-value">${shipDetail.destination || 'Unknown'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Draught:</span>
                        <span class="info-value">${shipDetail.draught ? shipDetail.draught + ' m' : 'Unknown'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Length:</span>
                        <span class="info-value">${(shipDetail.to_bow && shipDetail.to_stern) ? (shipDetail.to_bow + shipDetail.to_stern) + ' m' : 'Unknown'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Width:</span>
                        <span class="info-value">${(shipDetail.to_port && shipDetail.to_starboard) ? (shipDetail.to_port + shipDetail.to_starboard) + ' m' : 'Unknown'}</span>
                    </div>
                </div>

                <div class="info-section">
                    <h3>System Information</h3>
                    <div class="info-row">
                        <span class="info-label">First Seen:</span>
                        <span class="info-value">${shipDetail.first_seen ? new Date(shipDetail.first_seen).toLocaleString() : 'Unknown'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Last Seen:</span>
                        <span class="info-value">${shipDetail.last_seen ? new Date(shipDetail.last_seen).toLocaleString() : 'Unknown'}</span>
                    </div>
                </div>
            `;

            content.innerHTML = detailsHTML;
            sidebar.classList.add('open');
        }

        // Function to close sidebar
        function closeSidebar() {
            const sidebar = document.getElementById('shipSidebar');
            sidebar.classList.remove('open');
        }

        // Function to get ship type name from AIS ship type code
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

        // Function to get navigation status name
        function getNavStatusName(navStatus) {
            if (navStatus === undefined || navStatus === null) return 'Unknown';

            const navStatuses = {
                0: 'Under way using engine',
                1: 'At anchor',
                2: 'Not under command',
                3: 'Restricted manoeuverability',
                4: 'Constrained by her draught',
                5: 'Moored',
                6: 'Aground',
                7: 'Engaged in fishing',
                8: 'Under way sailing',
                9: 'Reserved for HSC',
                10: 'Reserved for WIG',
                11: 'Reserved',
                12: 'Reserved',
                13: 'Reserved',
                14: 'AIS-SART',
                15: 'Not defined'
            };

            return navStatuses[navStatus] || `Status ${navStatus}`;
        }

        // Function to get ship icon based on type and highlighted status
        function getShipIcon(shipType, isHighlighted) {
            if (isHighlighted) {
                return '/static/content/RedShip.svg';
            }

            if (!shipType) return '/static/content/BlueShip.svg';

            // Categorize ship types to colors
            if (shipType >= 30 && shipType <= 39) {
                // Fishing, towing, special operations - Green
                return '/static/content/GreenShip.svg';
            } else if (shipType >= 40 && shipType <= 49) {
                // High speed craft - Purple
                return '/static/content/PurpleShip.svg';
            } else if (shipType >= 50 && shipType <= 59) {
                // Pilot, rescue, tugs, etc. - Orange
                return '/static/content/OrangeShip.svg';
            } else if (shipType >= 60 && shipType <= 69) {
                // Passenger vessels - Orange
                return '/static/content/OrangeShip.svg';
            } else if (shipType >= 70 && shipType <= 79) {
                // Cargo vessels - Blue
                return '/static/content/BlueShip.svg';
            } else if (shipType >= 80 && shipType <= 89) {
                // Tankers - Brown
                return '/static/content/BrownShip.svg';
            } else {
                // Default/Other - Blue
                return '/static/content/BlueShip.svg';
            }
        }

        function createShipIcon(isHighlighted, heading, shipType) {
            const rotation = typeof heading === "number" && heading !== 511 ? heading : 0;
            const iconPath = getShipIcon(shipType, isHighlighted);

            return L.divIcon({
                html: `<div style="
                    width: 32px;
                    height: 32px;
                    transform: rotate(${rotation}deg);
                    transform-origin: center center;
                ">
                    <img src="${iconPath}"
                         style="
                             width: 32px;
                             height: 32px;
                             filter: drop-shadow(0 0 4px rgba(0,0,0,0.5));
                         " />
                </div>`,
                className: 'ship-div-icon',
                iconSize: [32, 32],
                iconAnchor: [16, 16],
                popupAnchor: [0, -16]
            });
        }

        function createShipLabel(shipName, isHighlighted) {
            const textColor = isHighlighted ? '#dc2626' : '#1e293b';

            return L.divIcon({
                html: `<div style="
                    color: ${textColor};
                    font-size: 12px;
                    font-weight: 700;
                    text-shadow: 1px 1px 2px rgba(255,255,255,0.8), -1px -1px 2px rgba(255,255,255,0.8);
                    white-space: nowrap;
                    pointer-events: none;
                    text-align: center;
                ">${shipName}</div>`,
                className: 'ship-label-icon',
                iconSize: [0, 0],
                iconAnchor: [-20, 8], // Position text below the ship
                popupAnchor: [0, 0]
            });
        }

        async function updateShips() {
            try {
                const res = await fetch('/db/ships');
                const data = await res.json();

                const ships = data.ships || [];
                const highlighted = new Set(["219213000", "219024900"]); // Your highlighted MMSIs

                // GET ZOOM LEVEL FIRST - before any processing
                const currentZoom = map.getZoom();

                // Remove ships that are no longer present
                const currentMMSIs = new Set(ships.map(ship => ship.mmsi));
                for (const mmsi in shipMarkers) {
                    if (!currentMMSIs.has(mmsi)) {
                        map.removeLayer(shipMarkers[mmsi]);
                        delete shipMarkers[mmsi];
                        if (shipLabels[mmsi]) {
                            map.removeLayer(shipLabels[mmsi]);
                            delete shipLabels[mmsi];
                        }
                    }
                }

                // Update or create ship markers
                for (const ship of ships) {
                    const mmsi = ship.mmsi;

                    // Skip ships without valid coordinates
                    if (!ship || typeof ship.latitude !== 'number' || typeof ship.longitude !== 'number') {
                        console.warn(`Skipping ship ${mmsi} - invalid coordinates:`, ship);
                        continue;
                    }

                    const isHighlighted = highlighted.has(mmsi);

                    // Use database heading data
                    let heading = 0;
                    if (ship.heading !== undefined && ship.heading !== null && ship.heading !== 511) {
                        heading = ship.heading;
                    } else if (ship.course !== undefined && ship.course !== null && ship.course < 360) {
                        heading = ship.course;
                    }

                    const shipName = ship.ship_name ? ship.ship_name.trim().replace(/@/g, '') : null;
                    const imo = ship.imo || 'Unknown';

                    // Simple hover tooltip with database data
                    let hoverTooltip = `<div class="ship-info">`;
                    if (shipName) {
                        hoverTooltip += `<strong>${shipName}</strong><br>`;
                    }
                    hoverTooltip += `IMO: ${imo}<br>`;
                    hoverTooltip += `Type: ${getShipTypeName(ship.ship_type)}<br>`;
                    hoverTooltip += `${ship.latitude.toFixed(4)}, ${ship.longitude.toFixed(4)}`;
                    hoverTooltip += `</div>`;

                    if (shipMarkers[mmsi]) {
                        // Update existing marker
                        shipMarkers[mmsi].setLatLng([ship.latitude, ship.longitude]);
                        shipMarkers[mmsi].setIcon(createShipIcon(isHighlighted, heading, ship.ship_type));
                        shipMarkers[mmsi].setTooltipContent(hoverTooltip);

                        // Update click handler for existing markers
                        shipMarkers[mmsi].off('click').on('click', function() {
                            openShipSidebar(mmsi, ship, ship);
                        });
                    } else {
                        // Create new marker
                        shipMarkers[mmsi] = L.marker([ship.latitude, ship.longitude], {
                            icon: createShipIcon(isHighlighted, heading, ship.ship_type)
                        })
                        .addTo(map)
                        .bindTooltip(hoverTooltip, { permanent: false, direction: 'top' })
                        .on('click', function() {
                            openShipSidebar(mmsi, ship, ship);
                        });
                    }

                    // Handle ship labels for highlighted ships (SAME LOGIC FOR BOTH NEW AND EXISTING)
                    if (isHighlighted && shipName && currentZoom >= 16) {
                        if (shipLabels[mmsi]) {
                            shipLabels[mmsi].setLatLng([ship.latitude, ship.longitude]);
                            shipLabels[mmsi].setIcon(createShipLabel(shipName, isHighlighted));
                        } else {
                            shipLabels[mmsi] = L.marker([ship.latitude, ship.longitude], {
                                icon: createShipLabel(shipName, isHighlighted),
                                interactive: false,
                                zIndexOffset: 1000
                            }).addTo(map);
                        }
                    } else if (shipLabels[mmsi]) {
                        map.removeLayer(shipLabels[mmsi]);
                        delete shipLabels[mmsi];
                    }
                }
            } catch (error) {
                console.error('Error updating ships:', error);
            }
        }
        
        map.on('zoomend', function() {
            const currentZoom = map.getZoom();
            if (currentZoom < 16) {
                // Hide all labels when zoomed out
                for (const mmsi in shipLabels) {
                    if (shipLabels[mmsi]) {
                        map.removeLayer(shipLabels[mmsi]);
                        delete shipLabels[mmsi];
                    }
                }
            }
            // Labels will be shown on next updateShips cycle if zoomed in enough
        });

        // Update ships every 2 seconds
        setInterval(updateShips, 2000);
        updateShips();