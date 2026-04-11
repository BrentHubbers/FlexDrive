async function getJson(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `Request failed: ${response.status}`);
    }

    return response.json();
}

const TRINIDAD_BRANCHES = {
    "Port of Spain": { lat: 10.6667, lng: -61.5167 },
    "San Fernando": { lat: 10.2833, lng: -61.4667 },
    Chaguanas: { lat: 10.5167, lng: -61.4167 },
    Arima: { lat: 10.6333, lng: -61.2833 },
    "Diego Martin": { lat: 10.7333, lng: -61.5667 },
    Tunapuna: { lat: 10.6500, lng: -61.3833 },
    Couva: { lat: 10.4333, lng: -61.4500 },
    "Point Fortin": { lat: 10.1833, lng: -61.6833 },
};

function formatMoney(value) {
    return new Intl.NumberFormat("en-TT", { style: "currency", currency: "TTD" }).format(value || 0);
}

function formatDateInput(date) {
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, "0");
    const dd = String(date.getDate()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd}`;
}

async function loadLocations() {
    const select = document.querySelector("#location-filter");
    if (!select) return;

    const locations = await getJson("/api/vehicles/locations");
    for (const location of locations) {
        const opt = document.createElement("option");
        opt.value = location;
        opt.textContent = location;
        select.appendChild(opt);
    }
}

function selectLocation(location) {
    const select = document.querySelector("#location-filter");
    if (!select) return;

    const optionExists = Array.from(select.options).some((option) => option.value === location);
    if (!optionExists) return;

    select.value = location;
    loadVehicles();
}

function initializeTrinidadMap() {
    const mapContainer = document.querySelector("#trinidad-branch-map");
    if (!mapContainer || typeof L === "undefined") return;

    const map = L.map("trinidad-branch-map").setView([10.55, -61.35], 9);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    Object.entries(TRINIDAD_BRANCHES).forEach(([location, coords]) => {
        const marker = L.marker([coords.lat, coords.lng]).addTo(map);
        marker.bindPopup(`<strong>${location}</strong><br/>Click to view available rentals`);
        marker.on("click", () => selectLocation(location));
    });
}

function vehicleCardTemplate(vehicle) {
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(now.getDate() + 1);
    const afterTomorrow = new Date(now);
    afterTomorrow.setDate(now.getDate() + 2);

    return `
        <div class="col-md-6 col-xl-4">
            <div class="card h-100 vehicle-card shadow-sm">
                <img src="${vehicle.url_image || vehicle.exterior_image_url || ""}" class="card-img-top vehicle-thumb" alt="${vehicle.make} ${vehicle.model}">
                <div class="card-body d-flex flex-column">
                    <h5 class="card-title mb-1">${vehicle.year} ${vehicle.make} ${vehicle.model}</h5>
                    <p class="text-muted mb-2">${vehicle.category} - ${vehicle.location}</p>
                    <p class="fw-semibold mb-3">${formatMoney(vehicle.price_per_day)} / day</p>
                    <div class="mt-auto">
                        <div class="row g-2 mb-2">
                            <div class="col-6">
                                <input type="date" class="form-control form-control-sm" id="from-${vehicle.id}" value="${formatDateInput(tomorrow)}">
                            </div>
                            <div class="col-6">
                                <input type="date" class="form-control form-control-sm" id="to-${vehicle.id}" value="${formatDateInput(afterTomorrow)}">
                            </div>
                        </div>
                        <button class="btn btn-primary w-100 reserve-btn" data-vehicle-id="${vehicle.id}" data-location="${vehicle.location}">
                            Reserve Now
                        </button>
                        <button class="btn btn-outline-secondary w-100 mt-2 vehicle-details-btn" data-vehicle-id="${vehicle.id}">
                            More Details
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

async function loadVehicles() {
    const listEl = document.querySelector("#vehicle-list");
    if (!listEl) return;

    const location = document.querySelector("#location-filter")?.value || "";
    const query = new URLSearchParams({ available_only: "true" });
    if (location) query.set("location", location);

    const vehicles = await getJson(`/api/vehicles?${query.toString()}`);
    listEl.innerHTML = vehicles.map(vehicleCardTemplate).join("");
}

function reservationRowTemplate(reservation) {
    return `
        <tr>
            <td>${reservation.id}</td>
            <td>${reservation.vehicle_id}</td>
            <td>${new Date(reservation.date_from).toLocaleString()}</td>
            <td>${new Date(reservation.date_to).toLocaleString()}</td>
            <td>${reservation.status}</td>
            <td>${formatMoney(reservation.total_cost)}</td>
        </tr>
    `;
}

async function loadMyReservations() {
    const listEl = document.querySelector("#reservation-list");
    if (!listEl) return;

    const reservations = await getJson("/api/my-reservations");
    listEl.innerHTML = reservations.map(reservationRowTemplate).join("");
}

async function reserveVehicle(vehicleId, location) {
    const fromValue = document.querySelector(`#from-${vehicleId}`)?.value;
    const toValue = document.querySelector(`#to-${vehicleId}`)?.value;
    if (!fromValue || !toValue) {
        alert("Please choose start and end dates.");
        return;
    }

    const payload = {
        vehicle_id: Number(vehicleId),
        date_from: `${fromValue}T10:00:00Z`,
        date_to: `${toValue}T10:00:00Z`,
        pickup_location: location,
        return_location: location,
        payment_method: "card",
        comment: "Booked from web app",
    };

    try {
        await getJson("/api/reservations", {
            method: "POST",
            body: JSON.stringify(payload),
        });
        await Promise.all([loadVehicles(), loadMyReservations()]);
    } catch (err) {
        alert(`Reservation failed: ${err.message}`);
    }
}

function reviewItemTemplate(review) {
    const stars = "★".repeat(review.rating) + "☆".repeat(5 - review.rating);
    return `
        <div class="border rounded p-2 mb-2 bg-white">
            <div class="d-flex justify-content-between align-items-center">
                <strong>${review.reviewer_name}</strong>
                <span class="text-warning">${stars}</span>
            </div>
            <div class="small text-muted">${new Date(review.created_at).toLocaleString()}</div>
            <div>${review.comment}</div>
        </div>
    `;
}

async function loadVehicleDetails(vehicleId) {
    const details = await getJson(`/api/vehicles/${vehicleId}`);
    document.querySelector("#vehicle-modal-title").textContent = `${details.year} ${details.make} ${details.model}`;
    document.querySelector("#vehicle-exterior-image").src = details.exterior_image_url || details.url_image || "";
    document.querySelector("#vehicle-interior-image").src = details.interior_image_url || details.url_image || "";
    document.querySelector("#vehicle-description").textContent = details.description || "No description available.";
    document.querySelector("#review-vehicle-id").value = String(vehicleId);

    const specs = [
        `Category: ${details.category}`,
        `Location: ${details.location}`,
        `Price/Day: ${formatMoney(details.price_per_day)}`,
        `Seats: ${details.seats || "N/A"}`,
        `Transmission: ${details.transmission || "N/A"}`,
        `Fuel Type: ${details.fuel_type || "N/A"}`,
    ];
    document.querySelector("#vehicle-specs").innerHTML = specs
        .map((item) => `<li class="list-group-item">${item}</li>`)
        .join("");

    const reviews = details.reviews || [];
    const reviewsEl = document.querySelector("#vehicle-reviews");
    reviewsEl.innerHTML = reviews.length
        ? reviews.map(reviewItemTemplate).join("")
        : "<p class='text-muted'>No reviews yet.</p>";

    const modalEl = document.querySelector("#vehicleDetailsModal");
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
}

async function postVehicleReview(event) {
    event.preventDefault();
    const vehicleId = Number(document.querySelector("#review-vehicle-id").value);
    const rating = Number(document.querySelector("#review-rating").value);
    const comment = document.querySelector("#review-comment").value.trim();
    if (!vehicleId || !comment) return;

    await getJson(`/api/vehicles/${vehicleId}/reviews`, {
        method: "POST",
        body: JSON.stringify({ rating, comment }),
    });

    document.querySelector("#review-comment").value = "";
    await loadVehicleDetails(vehicleId);
}

function bindRentalEvents() {
    document.querySelector("#refresh-vehicles")?.addEventListener("click", loadVehicles);
    document.querySelector("#location-filter")?.addEventListener("change", loadVehicles);

    document.addEventListener("click", (event) => {
        const button = event.target.closest(".reserve-btn");
        if (button) {
            reserveVehicle(button.dataset.vehicleId, button.dataset.location);
            return;
        }

        const detailsBtn = event.target.closest(".vehicle-details-btn");
        if (detailsBtn) {
            loadVehicleDetails(detailsBtn.dataset.vehicleId);
        }
    });

    document.querySelector("#vehicle-review-form")?.addEventListener("submit", postVehicleReview);
}

function summaryCard(label, value) {
    return `
        <div class="col-sm-6 col-lg-3">
            <div class="card shadow-sm h-100">
                <div class="card-body">
                    <div class="text-muted small">${label}</div>
                    <div class="display-6 fw-bold">${value}</div>
                </div>
            </div>
        </div>
    `;
}

async function loadAdminDashboard() {
    const cards = document.querySelector("#admin-summary-cards");
    const byLocation = document.querySelector("#admin-location-breakdown");
    if (!cards || !byLocation) return;

    const summary = await getJson("/api/admin/summary");
    cards.innerHTML = [
        summaryCard("Users", summary.users),
        summaryCard("Vehicles", summary.vehicles),
        summaryCard("Available", summary.available_vehicles),
        summaryCard("Reservations", summary.reservations),
    ].join("");

    byLocation.innerHTML = Object.keys(summary.by_location)
        .sort()
        .map((location) => `<tr><td>${location}</td><td>${summary.by_location[location]}</td></tr>`)
        .join("");
}

async function main() {
    const isRentalPage = Boolean(document.querySelector("#vehicle-list"));
    const isAdminPage = Boolean(document.querySelector("#admin-stats"));

    if (isRentalPage) {
        bindRentalEvents();
        await loadLocations();
        initializeTrinidadMap();
        await Promise.all([loadVehicles(), loadMyReservations()]);
    }

    if (isAdminPage) {
        await loadAdminDashboard();
    }
}

main();