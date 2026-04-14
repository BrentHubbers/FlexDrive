async function getJson(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    if (!response.ok) {
        let errorMessage = `Request failed: ${response.status}`;
        try {
            const errorBody = await response.json();
            errorMessage = errorBody.detail || errorBody.message || errorMessage;
        } catch {
            const errorText = await response.text();
            if (errorText) {
                errorMessage = errorText;
            }
        }
        throw new Error(errorMessage);
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

function syncReturnDateConstraints() {
    const pickupDateEl = document.querySelector('#rental-pickup-date');
    const returnDateEl = document.querySelector('#rental-return-date');
    if (!pickupDateEl || !returnDateEl || !pickupDateEl.value) return;

    returnDateEl.min = pickupDateEl.value;

    if (returnDateEl.value && returnDateEl.value <= pickupDateEl.value) {
        const nextDay = new Date(`${pickupDateEl.value}T00:00:00`);
        nextDay.setDate(nextDay.getDate() + 1);
        returnDateEl.value = formatDateInput(nextDay);
    }
}

function setReservationFeedback(message, type = "danger") {
    const feedback = document.querySelector("#reservation-feedback");
    if (!feedback) return;

    feedback.className = `alert alert-${type}`;
    feedback.textContent = message;
    feedback.classList.remove("d-none");
}

function clearReservationFeedback() {
    const feedback = document.querySelector("#reservation-feedback");
    if (!feedback) return;

    feedback.textContent = "";
    feedback.className = "alert d-none";
}

function getReservationFieldValue(selector) {
    return document.querySelector(selector)?.value?.trim() || "";
}

function getReservationField(selector) {
    return document.querySelector(selector);
}

function clearReservationFieldState(field) {
    if (!field) return;
    field.classList.remove("is-invalid", "reservation-field-flash");
    field.removeAttribute("aria-invalid");
}

function markReservationFieldError(selector) {
    const field = getReservationField(selector);
    if (!field) return;

    field.classList.add("is-invalid", "reservation-field-flash");
    field.setAttribute("aria-invalid", "true");
    window.setTimeout(() => {
        field.classList.remove("reservation-field-flash");
    }, 850);
}

function resetReservationFieldErrors() {
    const selectors = [
        "#rental-pickup-date",
        "#rental-return-date",
        "#driver-first-name",
        "#driver-last-name",
        "#driver-email",
        "#driver-phone",
        "#driver-address",
        "#driver-city",
        "#driver-license-num",
        "#driver-license-expiry-date",
    ];

    for (const selector of selectors) {
        clearReservationFieldState(getReservationField(selector));
    }
}

function validateReservationForm() {
    const errors = [];
    const vehicleId = Number(document.querySelector('#rental-vehicle-id').value);
    const fromValue = getReservationFieldValue('#rental-pickup-date');
    const toValue = getReservationFieldValue('#rental-return-date');
    const pickupLocation = getReservationFieldValue('#rental-pickup-location');
    const returnLocation = getReservationFieldValue('#rental-return-location');

    if (!Number.isFinite(vehicleId) || vehicleId <= 0) {
        errors.push({ selector: "#rental-vehicle-id", message: "Please select a vehicle before completing the reservation." });
    }

    if (!fromValue) {
        errors.push({ selector: "#rental-pickup-date", message: "Please choose a pickup date." });
    }

    if (!toValue) {
        errors.push({ selector: "#rental-return-date", message: "Please choose a return date." });
    }

    const pickupDate = new Date(`${fromValue}T00:00:00`);
    const returnDate = new Date(`${toValue}T00:00:00`);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (Number.isNaN(pickupDate.getTime()) || Number.isNaN(returnDate.getTime())) {
        if (fromValue) errors.push({ selector: "#rental-pickup-date", message: "Please enter a valid pickup date." });
        if (toValue) errors.push({ selector: "#rental-return-date", message: "Please enter a valid return date." });
    }

    if (pickupDate < today) {
        errors.push({ selector: "#rental-pickup-date", message: "Pickup date cannot be in the past." });
    }

    if (returnDate <= pickupDate) {
        errors.push({ selector: "#rental-return-date", message: "Return date must be after the pickup date." });
    }

    if (!pickupLocation || !returnLocation) {
        errors.push({ selector: "#rental-pickup-location", message: "Please select a branch location for pickup and return." });
    }

    const driverFirstName = getReservationFieldValue('#driver-first-name');
    const driverLastName = getReservationFieldValue('#driver-last-name');
    const driverEmail = getReservationFieldValue('#driver-email');
    const driverPhone = getReservationFieldValue('#driver-phone');
    const driverAddress = getReservationFieldValue('#driver-address');
    const driverCity = getReservationFieldValue('#driver-city');
    const driverLicenseNum = getReservationFieldValue('#driver-license-num');
    const driverLicenseExpiryDate = getReservationFieldValue('#driver-license-expiry-date');

    if (!driverFirstName) errors.push({ selector: "#driver-first-name", message: "Please enter your first name." });
    if (!driverLastName) errors.push({ selector: "#driver-last-name", message: "Please enter your last name." });
    if (!driverEmail) errors.push({ selector: "#driver-email", message: "Please enter your email address." });
    if (!driverPhone) errors.push({ selector: "#driver-phone", message: "Please enter your phone number." });
    if (!driverAddress) errors.push({ selector: "#driver-address", message: "Please enter your street address." });
    if (!driverCity) errors.push({ selector: "#driver-city", message: "Please enter your city or province." });
    if (!driverLicenseNum) errors.push({ selector: "#driver-license-num", message: "Please enter your driver license number." });
    if (!driverLicenseExpiryDate) errors.push({ selector: "#driver-license-expiry-date", message: "Please choose your license expiry date." });

    const emailOk = document.querySelector('#driver-email')?.checkValidity?.() ?? true;
    if (!emailOk) {
        errors.push({ selector: "#driver-email", message: "Please enter a valid email address." });
    }

    const phoneDigits = driverPhone.replace(/\D/g, "");
    if (phoneDigits.length < 7) {
        errors.push({ selector: "#driver-phone", message: "Please enter a valid phone number." });
    }

    const licenseExpiry = new Date(`${driverLicenseExpiryDate}T00:00:00`);
    if (Number.isNaN(licenseExpiry.getTime())) {
        errors.push({ selector: "#driver-license-expiry-date", message: "Please enter a valid license expiry date." });
    }

    if (licenseExpiry <= pickupDate) {
        errors.push({ selector: "#driver-license-expiry-date", message: "Your license must still be valid on the pickup date." });
    }

    if (errors.length > 0) {
        return errors;
    }

    return null;
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

const reservationViewState = {
    hideCancelled: localStorage.getItem("hideCancelledReservations") === "true",
};

function vehicleDisplayName(vehicle) {
    if (!vehicle) return "Unknown Vehicle";
    return `${vehicle.make} ${vehicle.model} (${vehicle.year})`;
}

function setVehicleDetailsFeedback(message, type = "danger") {
    const feedback = document.querySelector("#vehicle-details-feedback");
    if (!feedback) return;

    feedback.className = `alert alert-${type}`;
    feedback.textContent = message;
    feedback.classList.remove("d-none");
}

function clearVehicleDetailsFeedback() {
    const feedback = document.querySelector("#vehicle-details-feedback");
    if (!feedback) return;

    feedback.textContent = "";
    feedback.className = "alert d-none";
}

function setVehicleDetailsLoading(isLoading) {
    const title = document.querySelector("#vehicle-modal-title");
    const image = document.querySelector("#vehicle-exterior-image");
    const interiorImage = document.querySelector("#vehicle-interior-image");
    const interiorWrap = document.querySelector("#vehicle-interior-image-wrap");
    const description = document.querySelector("#vehicle-description");
    const specs = document.querySelector("#vehicle-specs");
    const reviews = document.querySelector("#vehicle-reviews");

    if (isLoading) {
        if (title) title.textContent = "Loading vehicle details...";
        if (image) {
            image.removeAttribute("src");
            image.alt = "Loading vehicle details";
        }
        if (interiorImage) {
            interiorImage.removeAttribute("src");
            interiorImage.alt = "Loading vehicle details";
        }
        if (interiorWrap) {
            interiorWrap.classList.add("d-none");
        }
        if (description) description.textContent = "Loading details...";
        if (specs) specs.innerHTML = "<li class='list-group-item text-muted'>Loading specs...</li>";
        if (reviews) reviews.innerHTML = "<p class='text-muted mb-0'>Loading reviews...</p>";
        return;
    }

    if (image) image.alt = "Vehicle";
    if (interiorImage) interiorImage.alt = "Vehicle";
}

function normalizeImageUrl(url) {
    return String(url || "").trim();
}

function isDuplicateVehicleImage(exteriorUrl, interiorUrl) {
    if (!exteriorUrl || !interiorUrl) return false;
    return normalizeImageUrl(exteriorUrl) === normalizeImageUrl(interiorUrl);
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
    return `
        <div class="col-md-6 col-xl-4">
            <div class="card h-100 vehicle-card">
                <img src="${vehicle.url_image || vehicle.exterior_image_url || ""}" class="card-img-top vehicle-thumb" alt="${vehicle.make} ${vehicle.model}">
                <div class="card-body d-flex flex-column">
                    <div class="mb-2">
                        <h5 class="card-title mb-1">${vehicleDisplayName(vehicle)}</h5>
                        <p class="text-muted mb-0">
                            <span class="d-inline-block px-2 py-1 rounded" style="background: rgba(177,10,10,0.08); font-size: 0.85rem;">${vehicle.category}</span>
                            <span class="d-inline-block px-2 py-1 rounded ms-2" style="background: rgba(247,181,0,0.12); font-size: 0.85rem;">${vehicle.location}</span>
                        </p>
                    </div>
                    <div class="mb-3 d-flex align-items-end gap-2">
                        <div>
                            <small class="text-muted d-block" style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">From</small>
                            <p class="fw-semibold mb-0">${formatMoney(vehicle.price_per_day)}</p>
                        </div>
                        <small class="text-muted" style="font-size: 0.9rem;">per day</small>
                    </div>
                    <div class="mt-auto">
                        <button class="btn btn-primary w-100 reserve-btn mb-2" data-vehicle-id="${vehicle.id}" data-location="${vehicle.location}">
                            Reserve Now
                        </button>
                        <button class="btn btn-outline-secondary w-100 vehicle-details-btn" data-vehicle-id="${vehicle.id}">
                            View Details
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

function getVehicleSlideImage(vehicle) {
    const candidates = [
        vehicle.exterior_image_url,
        vehicle.url_image,
        vehicle.interior_image_url,
    ]
        .map((value) => String(value || "").trim())
        .filter(Boolean);

    return candidates[0] || "https://via.placeholder.com/1200x800?text=Vehicle+Image";
}

function homeVehicleSlideTemplate(vehicle) {
    const imageUrl = getVehicleSlideImage(vehicle);
    const subtitle = `${vehicle.category} • ${vehicle.location} • ${formatMoney(vehicle.price_per_day)}/day`;
    return `
        <div class="home-slideshow-media">
            <img src="${imageUrl}" alt="${vehicle.make} ${vehicle.model}" onerror="this.onerror=null;this.src='https://via.placeholder.com/1200x800?text=Vehicle+Image';">
            <div class="home-slideshow-caption">
                <p class="home-slideshow-title">${vehicle.make} ${vehicle.model} (${vehicle.year})</p>
                <p class="home-slideshow-subtitle">${subtitle}</p>
            </div>
        </div>
    `;
}

function homeVehicleIndicatorTemplate(index, isActive) {
    return `
        <button type="button" data-bs-target="#home-available-carousel" data-bs-slide-to="${index}" class="${isActive ? "active" : ""}" ${isActive ? "aria-current='true'" : ""} aria-label="Slide ${index + 1}"></button>
    `;
}

async function loadHomeVehicleSlideshow() {
    const carouselEl = document.querySelector("#home-available-carousel");
    const innerEl = document.querySelector("#home-available-carousel-inner");
    const indicatorsEl = document.querySelector("#home-available-carousel-indicators");
    if (!carouselEl || !innerEl || !indicatorsEl) return;

    try {
        const vehicles = await getJson("/api/vehicles?available_only=true");
        const featured = vehicles.slice(0, 8);

        if (featured.length === 0) {
            innerEl.innerHTML = `
                <div class="carousel-item active">
                    <div class="home-slideshow-empty">No vehicles are currently available. Check back soon.</div>
                </div>
            `;
            indicatorsEl.innerHTML = "";
            bootstrap.Carousel.getOrCreateInstance(carouselEl).pause();
            return;
        }

        innerEl.innerHTML = featured
            .map((vehicle, index) => `
                <div class="carousel-item ${index === 0 ? "active" : ""}">
                    ${homeVehicleSlideTemplate(vehicle)}
                </div>
            `)
            .join("");

        indicatorsEl.innerHTML = featured
            .map((_, index) => homeVehicleIndicatorTemplate(index, index === 0))
            .join("");

        if (featured.length > 1) {
            bootstrap.Carousel.getOrCreateInstance(carouselEl).cycle();
        } else {
            bootstrap.Carousel.getOrCreateInstance(carouselEl).pause();
        }
    } catch (err) {
        innerEl.innerHTML = `
            <div class="carousel-item active">
                <div class="home-slideshow-empty">Unable to load vehicles right now.</div>
            </div>
        `;
        indicatorsEl.innerHTML = "";
    }
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
    const driverName = reservation.driver
        ? `${reservation.driver.first_name}${reservation.driver.last_name ? ' ' + reservation.driver.last_name : ''}`
        : "-";
    const driverPhone = reservation.driver ? reservation.driver.phone : "-";
    const driverInfo = `${driverName} (${driverPhone})`;

    const createdTime = new Date(reservation.created_at).getTime();
    const nowTime = Date.now();
    const hoursElapsed = (nowTime - createdTime) / (1000 * 60 * 60);
    const canCancel = reservation.status === "active" && hoursElapsed < 24;

    const addOns = [];
    if (reservation.protection_plan) addOns.push("🛡️ Protection");
    if (reservation.flexible_rebooking) addOns.push("🔄 Flexible");
    const addOnsText = addOns.length > 0 ? addOns.join(", ") : "None";

    const cancelBtn = canCancel
        ? `<button class="btn btn-sm btn-danger" onclick="cancelReservation(${reservation.id})">Cancel</button>`
        : "";

    return `
        <tr>
            <td>${reservation.id}</td>
            <td>${vehicleDisplayName(vehicle)}</td>
            <td>${driverInfo}</td>
            <td>${new Date(reservation.date_from).toLocaleString()}</td>
            <td>${new Date(reservation.date_to).toLocaleString()}</td>
            <td><small>${addOnsText}</small></td>
            <td>${reservation.status}</td>
            <td>${formatMoney(reservation.total_cost)}</td>
            <td>${cancelBtn}</td>
        </tr>
    `;
}

function reservationEmptyStateTemplate(message) {
    return `
        <tr>
            <td colspan="9" class="text-center text-muted py-4">${message}</td>
        </tr>
    `;
}

function updateReservationViewControls() {
    const toggleButton = document.querySelector("#reservation-toggle-cancelled-view");
    const note = document.querySelector("#reservation-view-note");

    if (toggleButton) {
        toggleButton.textContent = reservationViewState.hideCancelled ? "Show Cancelled" : "Hide Cancelled";
        toggleButton.classList.toggle("btn-outline-secondary", !reservationViewState.hideCancelled);
        toggleButton.classList.toggle("btn-secondary", reservationViewState.hideCancelled);
    }

    if (note) {
        note.textContent = reservationViewState.hideCancelled
            ? "Cancelled reservations are hidden from view. Click Show Cancelled to bring them back."
            : "Cancelled reservations are visible in the table.";
    }
}

function renderReservationList(reservations) {
    const listEl = document.querySelector("#reservation-list");
    if (!listEl) return;

    const visibleReservations = reservationViewState.hideCancelled
        ? reservations.filter((reservation) => String(reservation.status || "").toLowerCase() !== "cancelled")
        : reservations;

    if (visibleReservations.length === 0) {
        listEl.innerHTML = reservationViewState.hideCancelled
            ? reservationEmptyStateTemplate("No non-cancelled reservations are currently visible.")
            : reservationEmptyStateTemplate("You do not have any reservations yet.");
        updateReservationViewControls();
        return;
    }

    listEl.innerHTML = visibleReservations.map(reservationRowTemplate).join("");
    updateReservationViewControls();
}

async function loadMyReservations() {
    const listEl = document.querySelector("#reservation-list");
    if (!listEl) return;

    await ensureVehicleLookup();
    const reservations = await getJson("/api/my-reservations");
    renderReservationList(reservations);
}

function bindReservationEvents() {
    document.querySelector("#reservation-refresh")?.addEventListener("click", () => {
        loadMyReservations();
    });

    document.querySelector("#reservation-toggle-cancelled-view")?.addEventListener("click", () => {
        reservationViewState.hideCancelled = !reservationViewState.hideCancelled;
        localStorage.setItem("hideCancelledReservations", String(reservationViewState.hideCancelled));
        loadMyReservations();
    });
}

async function reserveVehicle(vehicleId, location) {
    clearReservationFeedback();
    resetReservationFieldErrors();
    document.querySelector('#rental-vehicle-id').value = vehicleId;
    document.querySelector('#rental-pickup-location').value = location;
    document.querySelector('#rental-return-location').value = location;

    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(now.getDate() + 1);
    const afterTomorrow = new Date(now);
    afterTomorrow.setDate(now.getDate() + 2);

    document.querySelector('#rental-details-form').reset();
    document.querySelector('#rental-pickup-date').value = formatDateInput(tomorrow);
    document.querySelector('#rental-return-date').value = formatDateInput(afterTomorrow);
    document.querySelector('#rental-pickup-date').min = formatDateInput(now);
    syncReturnDateConstraints();

    const modal = bootstrap.Modal.getOrCreateInstance(document.querySelector('#rentalDetailsModal'));
    modal.show();
}

async function submitReservationWithDriver() {
    clearReservationFeedback();
    resetReservationFieldErrors();

    const validationErrors = validateReservationForm();
    if (validationErrors) {
        for (const error of validationErrors) {
            if (error.selector && error.selector !== "#rental-vehicle-id") {
                markReservationFieldError(error.selector);
            }
        }

        const firstError = validationErrors[0];
        setReservationFeedback(firstError.message, "danger");

        const firstField = firstError.selector ? getReservationField(firstError.selector) : null;
        if (firstField && firstField.focus) {
            firstField.focus();
        }
        return;
    }

    const vehicleId = Number(document.querySelector('#rental-vehicle-id').value);
    const fromValue = document.querySelector('#rental-pickup-date').value;
    const toValue = document.querySelector('#rental-return-date').value;
    const location = document.querySelector('#rental-pickup-location').value;

    const driver = {
        first_name: document.querySelector('#driver-first-name').value.trim(),
        last_name: document.querySelector('#driver-last-name').value.trim(),
        email: document.querySelector('#driver-email').value.trim(),
        phone: document.querySelector('#driver-phone').value.trim(),
        address: document.querySelector('#driver-address').value.trim(),
        city: document.querySelector('#driver-city').value.trim(),
        license_num: document.querySelector('#driver-license-num').value.trim(),
        license_expiry_date: document.querySelector('#driver-license-expiry-date').value || null,
    };

    const hasProtectionPlan = document.querySelector('#driver-protection-plan').checked;
    const hasFlexibleRebooking = document.querySelector('#driver-flexible-rebooking').checked;

    const payload = {
        vehicle_id: vehicleId,
        date_from: `${fromValue}T10:00:00Z`,
        date_to: `${toValue}T10:00:00Z`,
        pickup_location: location,
        return_location: location,
        payment_method: "card",
        comment: "Booked from web app",
        driver,
        protection_plan: hasProtectionPlan,
        flexible_rebooking: hasFlexibleRebooking,
    };

    try {
        await getJson("/api/reservations", {
            method: "POST",
            body: JSON.stringify(payload),
        });
        const modalEl = document.querySelector('#rentalDetailsModal');
        const modalInstance = bootstrap.Modal.getInstance(modalEl);
        if (modalInstance) modalInstance.hide();
        setReservationFeedback("Reservation confirmed!", "success");
        await loadVehicles();
    } catch (err) {
        setReservationFeedback(err.message || "Reservation failed.", "danger");
    }
}

async function cancelReservation(reservationId) {
    if (!confirm("Are you sure you want to cancel this reservation? This action cannot be undone.")) {
        return;
    }

    try {
        await getJson(`/api/reservations/${reservationId}/cancel`, {
            method: "PATCH",
        });
        alert("Reservation cancelled successfully");
        await loadMyReservations();
    } catch (err) {
        alert(`Failed to cancel: ${err.message}`);
    }
}

function reviewItemTemplate(review) {
    const stars = "★".repeat(review.rating) + "☆".repeat(5 - review.rating);
    const pinnedBadge = review.pinned ? '<span class="badge bg-warning text-dark ms-2">Pinned</span>' : "";
    return `
        <div class="border rounded p-2 mb-2 bg-white">
            <div class="d-flex justify-content-between align-items-center">
                <div><strong>${review.reviewer_name}</strong>${pinnedBadge}</div>
                <span class="text-warning">${stars}</span>
            </div>
            <div class="small text-muted">${new Date(review.created_at).toLocaleString()}</div>
            <div>${review.comment}</div>
        </div>
    `;
}

async function loadVehicleDetails(vehicleId) {
    const modalEl = document.querySelector("#vehicleDetailsModal");
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();

    clearVehicleDetailsFeedback();
    setVehicleDetailsLoading(true);

    try {
        const details = await getJson(`/api/vehicles/${vehicleId}`);
        document.querySelector("#vehicle-modal-title").textContent = `${details.year} ${details.make} ${details.model}`;
        const exteriorImageUrl = details.exterior_image_url || details.url_image || "";
        const interiorImageUrl = details.interior_image_url || "";
        const exteriorImage = document.querySelector("#vehicle-exterior-image");
        const interiorImage = document.querySelector("#vehicle-interior-image");
        const interiorWrap = document.querySelector("#vehicle-interior-image-wrap");

        if (exteriorImage) {
            exteriorImage.src = exteriorImageUrl;
            exteriorImage.alt = `${details.make} ${details.model} exterior view`;
        }

        if (interiorImage && interiorWrap) {
            const shouldShowInterior = interiorImageUrl && !isDuplicateVehicleImage(exteriorImageUrl, interiorImageUrl);
            if (shouldShowInterior) {
                interiorImage.src = interiorImageUrl;
                interiorImage.alt = `${details.make} ${details.model} interior view`;
                interiorWrap.classList.remove("d-none");
            } else {
                interiorImage.removeAttribute("src");
                interiorWrap.classList.add("d-none");
            }
        }

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
    } catch (err) {
        document.querySelector("#vehicle-modal-title").textContent = "Vehicle Details";
        document.querySelector("#vehicle-description").textContent = "";
        document.querySelector("#vehicle-specs").innerHTML = "";
        document.querySelector("#vehicle-reviews").innerHTML = "";
        setVehicleDetailsFeedback(err.message || "Unable to load vehicle details.", "danger");
    } finally {
        setVehicleDetailsLoading(false);
    }
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
    document.querySelector("#confirm-rental-btn")?.addEventListener("click", submitReservationWithDriver);
    document.querySelector("#rental-pickup-date")?.addEventListener("change", syncReturnDateConstraints);

    document.querySelector("#rental-details-form")?.addEventListener("input", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement || target instanceof HTMLTextAreaElement)) {
            return;
        }

        if (target.id === "rental-pickup-date") {
            syncReturnDateConstraints();
        }

        clearReservationFieldState(target);
    });

    document.querySelector("#rental-details-form")?.addEventListener("change", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement || target instanceof HTMLTextAreaElement)) {
            return;
        }

        if (target.id === "rental-pickup-date") {
            syncReturnDateConstraints();
        }

        clearReservationFieldState(target);
    });

    document.addEventListener("click", (event) => {
        const button = event.target.closest(".reserve-btn");
        if (button) {
            reserveVehicle(button.dataset.vehicleId, button.dataset.location);
            return;
        }

        const detailsBtn = event.target.closest(".vehicle-details-btn");
        if (detailsBtn) {
            loadVehicleDetails(detailsBtn.dataset.vehicleId).catch((err) => {
                setVehicleDetailsFeedback(err.message || "Unable to load vehicle details.", "danger");
            });
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
        summaryCard("Reviews", summary.reviews),
    ].join("");

    byLocation.innerHTML = Object.keys(summary.by_location)
        .sort()
        .map((location) => `<tr><td>${location}</td><td>${summary.by_location[location]}</td></tr>`)
        .join("");
}

function adminReviewRowTemplate(review) {
    const vehicle = adminState.fleetById.get(review.vehicle_id);
    const hiddenLabel = review.hidden ? "Removed" : "Visible";
    const pinLabel = review.pinned ? "Unpin" : "Pin";
    const statusClass = review.hidden ? "text-danger" : review.pinned ? "text-warning" : "text-success";

    return `
        <tr>
            <td>${review.id}</td>
            <td>${vehicleDisplayName(vehicle) || `Vehicle #${review.vehicle_id}`}</td>
            <td>${review.reviewer_name}</td>
            <td>${"★".repeat(review.rating)}</td>
            <td>${review.comment}</td>
            <td><span class="${statusClass}">${hiddenLabel}${review.hidden ? "" : review.pinned ? " / Pinned" : ""}</span></td>
            <td class="d-flex gap-2 flex-wrap">
                <button class="btn btn-sm btn-outline-warning admin-toggle-review-pin-btn" data-review-id="${review.id}">${pinLabel}</button>
                <button class="btn btn-sm btn-outline-danger admin-remove-review-btn" data-review-id="${review.id}">Remove</button>
            </td>
        </tr>
    `;
}

async function loadAdminReviews() {
    const listEl = document.querySelector("#admin-review-list");
    if (!listEl) return;

    const reviews = await getJson("/api/admin/reviews");
    listEl.innerHTML = reviews.map(adminReviewRowTemplate).join("");
}

async function toggleAdminReviewPin(reviewId) {
    await getJson(`/api/admin/reviews/${reviewId}/pin`, {
        method: "PATCH",
    });

    await Promise.all([loadAdminDashboard(), loadAdminReviews()]);
}

async function removeAdminReview(reviewId) {
    await getJson(`/api/admin/reviews/${reviewId}`, {
        method: "DELETE",
    });

    await Promise.all([loadAdminDashboard(), loadAdminReviews()]);
}

function adminReservationRowTemplate(reservation) {
    const vehicle = adminState.fleetById.get(reservation.vehicle_id);
    const driverName = reservation.driver 
        ? `${reservation.driver.first_name}${reservation.driver.last_name ? ' ' + reservation.driver.last_name : ''}`
        : "-";
    return `
        <tr>
            <td>${reservation.id}</td>
            <td>${vehicleDisplayName(vehicle)}</td>
            <td>${vehicle?.license_plate || `ID-${reservation.vehicle_id}`}</td>
            <td>${reservation.user_id ?? "-"}</td>
            <td>${driverName}</td>
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

    document.querySelector("#admin-refresh-reviews")?.addEventListener("click", () => {
        loadAdminReviews();
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
            return;
        }

        const pinBtn = event.target.closest(".admin-toggle-review-pin-btn");
        if (pinBtn) {
            try {
                await toggleAdminReviewPin(pinBtn.dataset.reviewId);
            } catch (err) {
                alert(`Unable to update review: ${err.message}`);
            }
            return;
        }

        const reviewRemoveBtn = event.target.closest(".admin-remove-review-btn");
        if (reviewRemoveBtn) {
            try {
                await removeAdminReview(reviewRemoveBtn.dataset.reviewId);
            } catch (err) {
                alert(`Unable to remove review: ${err.message}`);
            }
        }
    });
}

async function main() {
    const isAppPage = Boolean(document.querySelector("#home-available-carousel-inner"));
    const isVehiclePage = Boolean(document.querySelector("#vehicle-list"));
    const isReservationPage = Boolean(document.querySelector("#reservation-list"));
    const isAdminPage = Boolean(document.querySelector("#admin-stats"));

    if (isAppPage) {
        await loadHomeVehicleSlideshow();
    }

    if (isVehiclePage) {
        bindRentalEvents();
        await loadLocations();
        initializeTrinidadMap();
        await loadVehicles();
    }

    if (isReservationPage && !isVehiclePage) {
        bindReservationEvents();
        await loadMyReservations();
    }

    if (isAdminPage) {
        bindAdminEvents();
        await Promise.all([loadAdminDashboard(), loadAdminReservations(), loadAdminReviews(), loadAdminFleet()]);
    }
}

main();