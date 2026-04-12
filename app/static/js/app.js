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

const rentalState = {
    allVehicles: [],
    vehicleById: new Map(),
};

const adminState = {
    fleet: [],
    fleetById: new Map(),
    sortKey: "vehicle",
    sortDirection: "asc",
};

function vehicleDisplayName(vehicle) {
    if (!vehicle) return "Unknown Vehicle";
    return `${vehicle.make} ${vehicle.model} (${vehicle.year})`;
}

function toComparable(value) {
    if (typeof value === "boolean") return value ? 1 : 0;
    if (typeof value === "number") return value;
    return String(value || "").toLowerCase();
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

function loadCategories() {
    const select = document.querySelector("#category-filter");
    if (!select) return;

    const categories = [...new Set(rentalState.allVehicles.map((vehicle) => (vehicle.category || "").trim()).filter(Boolean))]
        .sort((a, b) => a.localeCompare(b));

    select.innerHTML = '<option value="">All categories</option>';
    for (const category of categories) {
        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        select.appendChild(option);
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

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    const markers = [];
    Object.entries(TRINIDAD_BRANCHES).forEach(([location, coords]) => {
        const marker = L.marker([coords.lat, coords.lng]).addTo(map);
        marker.bindPopup(`<strong>${location}</strong><br/>Click to view available rentals`);
        marker.on("click", () => selectLocation(location));
        markers.push(marker);
    });

    if (markers.length > 0) {
        map.fitBounds(L.featureGroup(markers).getBounds().pad(0.2));
    }
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
                    <h5 class="card-title mb-1">${vehicleDisplayName(vehicle)}</h5>
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

function matchesPriceFilter(vehicle, priceFilter) {
    const price = Number(vehicle.price_per_day || 0);
    if (!priceFilter) return true;
    if (priceFilter === "lte-400") return price <= 400;
    if (priceFilter === "401-600") return price >= 401 && price <= 600;
    if (priceFilter === "gte-601") return price >= 601;
    return true;
}

function sortVehicles(vehicles, sortBy) {
    const sorted = [...vehicles];
    sorted.sort((a, b) => {
        if (sortBy === "price-asc") return Number(a.price_per_day || 0) - Number(b.price_per_day || 0);
        if (sortBy === "price-desc") return Number(b.price_per_day || 0) - Number(a.price_per_day || 0);
        if (sortBy === "year-desc") return Number(b.year || 0) - Number(a.year || 0);
        if (sortBy === "year-asc") return Number(a.year || 0) - Number(b.year || 0);
        return vehicleDisplayName(a).localeCompare(vehicleDisplayName(b));
    });
    return sorted;
}

function renderVehicles(vehicles) {
    const listEl = document.querySelector("#vehicle-list");
    if (!listEl) return;

    listEl.innerHTML = vehicles.map(vehicleCardTemplate).join("");
}

function applyRentalVehicleFilters() {
    const location = document.querySelector("#location-filter")?.value || "";
    const category = document.querySelector("#category-filter")?.value || "";
    const search = (document.querySelector("#vehicle-search")?.value || "").trim().toLowerCase();
    const priceFilter = document.querySelector("#price-filter")?.value || "";
    const sortBy = document.querySelector("#vehicle-sort")?.value || "name-asc";

    const filtered = rentalState.allVehicles.filter((vehicle) => {
        if (location && vehicle.location !== location) return false;
        if (category && vehicle.category !== category) return false;
        if (!matchesPriceFilter(vehicle, priceFilter)) return false;

        if (search) {
            const haystack = [
                vehicle.make,
                vehicle.model,
                vehicle.category,
                vehicle.location,
                vehicle.license_plate || "",
                String(vehicle.year || ""),
            ]
                .join(" ")
                .toLowerCase();
            if (!haystack.includes(search)) return false;
        }

        return true;
    });

    const sorted = sortVehicles(filtered, sortBy);
    renderVehicles(sorted);
}

async function loadVehicles() {
    const vehicles = await getJson("/api/vehicles?available_only=true");
    rentalState.allVehicles = vehicles;
    rentalState.vehicleById = new Map(vehicles.map((vehicle) => [vehicle.id, vehicle]));

    loadCategories();
    applyRentalVehicleFilters();
}

async function ensureVehicleLookup() {
    if (rentalState.vehicleById.size > 0) return;

    const vehicles = await getJson("/api/vehicles?available_only=false");
    rentalState.vehicleById = new Map(vehicles.map((vehicle) => [vehicle.id, vehicle]));
}

function reservationRowTemplate(reservation) {
    const vehicle = rentalState.vehicleById.get(reservation.vehicle_id);
    return `
        <tr>
            <td>${reservation.id}</td>
            <td>${vehicleDisplayName(vehicle)}</td>
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

    await ensureVehicleLookup();
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
    document.querySelector("#location-filter")?.addEventListener("change", applyRentalVehicleFilters);
    document.querySelector("#category-filter")?.addEventListener("change", applyRentalVehicleFilters);
    document.querySelector("#price-filter")?.addEventListener("change", applyRentalVehicleFilters);
    document.querySelector("#vehicle-sort")?.addEventListener("change", applyRentalVehicleFilters);
    document.querySelector("#vehicle-search")?.addEventListener("input", applyRentalVehicleFilters);

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

function adminReservationRowTemplate(reservation) {
    const vehicle = adminState.fleetById.get(reservation.vehicle_id);
    return `
        <tr>
            <td>${reservation.id}</td>
            <td>${vehicleDisplayName(vehicle)}</td>
            <td>${vehicle?.license_plate || `ID-${reservation.vehicle_id}`}</td>
            <td>${reservation.user_id ?? "-"}</td>
            <td><input type="date" class="form-control form-control-sm" id="admin-res-start-${reservation.id}" value="${String(reservation.date_from).slice(0, 10)}"></td>
            <td><input type="date" class="form-control form-control-sm" id="admin-res-end-${reservation.id}" value="${String(reservation.date_to).slice(0, 10)}"></td>
            <td>
                <select class="form-select form-select-sm" id="admin-res-status-${reservation.id}">
                    <option value="active" ${reservation.status === "active" ? "selected" : ""}>active</option>
                    <option value="cancelled" ${reservation.status === "cancelled" ? "selected" : ""}>cancelled</option>
                    <option value="completed" ${reservation.status === "completed" ? "selected" : ""}>completed</option>
                </select>
            </td>
            <td class="d-flex gap-2">
                <button class="btn btn-sm btn-primary admin-save-reservation-btn" data-reservation-id="${reservation.id}">Save</button>
                <button class="btn btn-sm btn-outline-danger admin-cancel-reservation-btn" data-reservation-id="${reservation.id}">Cancel</button>
            </td>
        </tr>
    `;
}

function adminFleetRowTemplate(vehicle) {
    return `
        <tr>
            <td>${vehicle.id}</td>
            <td>${vehicle.make} ${vehicle.model} (${vehicle.year})</td>
            <td>${vehicle.license_plate || `ID-${vehicle.id}`}</td>
            <td>${vehicle.category}</td>
            <td>${vehicle.location}</td>
            <td>${formatMoney(vehicle.price_per_day)}</td>
            <td>${vehicle.available ? "Yes" : "No"}</td>
            <td>
                <button class="btn btn-sm btn-outline-danger admin-delete-vehicle-btn" data-vehicle-id="${vehicle.id}">Remove</button>
            </td>
        </tr>
    `;
}

function sortFleet(vehicles) {
    const sorted = [...vehicles];
    const { sortKey, sortDirection } = adminState;

    sorted.sort((left, right) => {
        const leftValue = sortKey === "vehicle"
            ? `${left.make} ${left.model} ${left.year}`
            : left[sortKey];
        const rightValue = sortKey === "vehicle"
            ? `${right.make} ${right.model} ${right.year}`
            : right[sortKey];

        const comparableLeft = toComparable(leftValue);
        const comparableRight = toComparable(rightValue);

        if (comparableLeft < comparableRight) return sortDirection === "asc" ? -1 : 1;
        if (comparableLeft > comparableRight) return sortDirection === "asc" ? 1 : -1;
        return 0;
    });

    return sorted;
}

function updateAdminFleetSortIndicators() {
    const sortButtons = document.querySelectorAll(".admin-fleet-sort");
    for (const button of sortButtons) {
        const indicator = button.querySelector(".admin-sort-indicator");
        if (!indicator) continue;

        const isActive = button.dataset.sortKey === adminState.sortKey;
        button.classList.toggle("is-active", isActive);
        indicator.textContent = isActive
            ? (adminState.sortDirection === "asc" ? "↑" : "↓")
            : "↕";
    }
}

function renderAdminFleet() {
    const listEl = document.querySelector("#admin-fleet-list");
    if (!listEl) return;

    listEl.innerHTML = sortFleet(adminState.fleet).map(adminFleetRowTemplate).join("");
    updateAdminFleetSortIndicators();
}

async function loadAdminReservations() {
    const listEl = document.querySelector("#admin-reservation-list");
    if (!listEl) return;

    if (adminState.fleetById.size === 0) {
        await loadAdminFleet();
    }

    const reservations = await getJson("/api/admin/reservations");
    listEl.innerHTML = reservations.map(adminReservationRowTemplate).join("");
}

async function loadAdminFleet() {
    const fleet = await getJson("/api/admin/fleet");
    adminState.fleet = fleet;
    adminState.fleetById = new Map(fleet.map((vehicle) => [vehicle.id, vehicle]));
    renderAdminFleet();
}

async function saveAdminReservation(reservationId) {
    const start = document.querySelector(`#admin-res-start-${reservationId}`)?.value;
    const end = document.querySelector(`#admin-res-end-${reservationId}`)?.value;
    const status = document.querySelector(`#admin-res-status-${reservationId}`)?.value;
    if (!start || !end || !status) return;

    await getJson(`/api/admin/reservations/${reservationId}`, {
        method: "PATCH",
        body: JSON.stringify({
            date_from: `${start}T10:00:00Z`,
            date_to: `${end}T10:00:00Z`,
            status,
        }),
    });

    await Promise.all([loadAdminDashboard(), loadAdminReservations(), loadAdminFleet()]);
}

async function cancelAdminReservation(reservationId) {
    await getJson(`/api/admin/reservations/${reservationId}/cancel`, {
        method: "PATCH",
    });

    await Promise.all([loadAdminDashboard(), loadAdminReservations(), loadAdminFleet()]);
}

async function addAdminVehicle(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);

    const payload = {
        make: String(data.get("make") || "").trim(),
        model: String(data.get("model") || "").trim(),
        year: Number(data.get("year") || 0),
        category: String(data.get("category") || "").trim(),
        price_per_day: Number(data.get("price_per_day") || 0),
        location: String(data.get("location") || "").trim(),
        license_plate: String(data.get("license_plate") || "").trim() || null,
        url_image: String(data.get("url_image") || "").trim() || null,
        seats: data.get("seats") ? Number(data.get("seats")) : null,
        transmission: String(data.get("transmission") || "").trim() || null,
        fuel_type: String(data.get("fuel_type") || "").trim() || null,
    };

    await getJson("/api/admin/fleet", {
        method: "POST",
        body: JSON.stringify(payload),
    });

    form.reset();
    await Promise.all([loadAdminDashboard(), loadAdminFleet()]);
}

async function removeAdminVehicle(vehicleId) {
    await getJson(`/api/admin/fleet/${vehicleId}`, {
        method: "DELETE",
    });

    await Promise.all([loadAdminDashboard(), loadAdminFleet()]);
}

function bindAdminEvents() {
    document.querySelector("#admin-refresh-reservations")?.addEventListener("click", () => {
        loadAdminReservations();
    });

    document.querySelector("#admin-add-vehicle-form")?.addEventListener("submit", async (event) => {
        try {
            await addAdminVehicle(event);
        } catch (err) {
            alert(`Unable to add vehicle: ${err.message}`);
        }
    });

    document.addEventListener("click", async (event) => {
        const sortBtn = event.target.closest(".admin-fleet-sort");
        if (sortBtn) {
            const nextKey = sortBtn.dataset.sortKey;
            if (adminState.sortKey === nextKey) {
                adminState.sortDirection = adminState.sortDirection === "asc" ? "desc" : "asc";
            } else {
                adminState.sortKey = nextKey;
                adminState.sortDirection = "asc";
            }
            renderAdminFleet();
            return;
        }

        const saveBtn = event.target.closest(".admin-save-reservation-btn");
        if (saveBtn) {
            try {
                await saveAdminReservation(saveBtn.dataset.reservationId);
            } catch (err) {
                alert(`Unable to update reservation: ${err.message}`);
            }
            return;
        }

        const cancelBtn = event.target.closest(".admin-cancel-reservation-btn");
        if (cancelBtn) {
            try {
                await cancelAdminReservation(cancelBtn.dataset.reservationId);
            } catch (err) {
                alert(`Unable to cancel reservation: ${err.message}`);
            }
            return;
        }

        const removeBtn = event.target.closest(".admin-delete-vehicle-btn");
        if (removeBtn) {
            try {
                await removeAdminVehicle(removeBtn.dataset.vehicleId);
            } catch (err) {
                alert(`Unable to remove vehicle: ${err.message}`);
            }
        }
    });
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
        bindAdminEvents();
        await Promise.all([loadAdminDashboard(), loadAdminReservations(), loadAdminFleet()]);
    }
}

main();