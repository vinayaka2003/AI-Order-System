async function sendMessage() {

    let message =
        document.getElementById("message").value;

    if (message.trim() === "") {
        return;
    }

    // USER MESSAGE

    document.getElementById("response").innerHTML += `

    <div class="user-message">
        ${message}
    </div>

    `;

    // CLEAR INPUT

    document.getElementById("message").value = "";

    // SEND REQUEST

    let response = await fetch("/chat", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            message: message
        })

    });

    let data = await response.json();

    // AI RESPONSE

    document.getElementById("response").innerHTML += `

    <div class="ai-message">
        ${data.reply}
    </div>

    `;

    // AUTO SCROLL

    let chatBox =
        document.getElementById("response");

    chatBox.scrollTop =
        chatBox.scrollHeight;

    // RELOAD ORDERS

    loadOrders();
}

// =========================
// LOAD ORDERS
// =========================

async function loadOrders() {

    let response =
        await fetch("/orders");

    let data =
        await response.json();

    let ordersList =
        document.getElementById("orders-list");

    let currentOrder =
        document.getElementById("current-order");

    ordersList.innerHTML = "";

    // =========================
    // NO ORDERS
    // =========================

    if (data.orders.length === 0) {

        ordersList.innerHTML = `
            <p>No Orders Yet</p>
        `;

        currentOrder.innerHTML =
            "No active order";

        return;
    }

    // =========================
    // LATEST ORDER
    // =========================

    let latest = data.orders[0];

    currentOrder.innerHTML = `

        <div class="order-card">

            <h3>Order #${latest.id}</h3>

            <p><b>Item:</b> ${latest.item_name}</p>

            <p><b>Quantity:</b> ${latest.quantity}</p>

            <p><b>Status:</b> ${latest.status}</p>

            <p><b>Material:</b> ${latest.material}</p>

            <p><b>Deadline:</b> ${latest.deadline}</p>

            <p><b>Delivery:</b> ${latest.delivery_time}</p>

            <p><b>Created:</b> ${latest.created_at || "N/A"}</p>

            <p><b>Latest Note:</b> ${latest.latest_note}</p>

        </div>

    `;

    // =========================
    // HISTORY
    // =========================

    data.orders.forEach(order => {

        ordersList.innerHTML += `

        <div class="history-item">

            <h3>Order #${order.id}</h3>

            <p>📦 ${order.item_name}</p>

            <p>🔢 Qty: ${order.quantity}</p>

            <p>📌 Status: ${order.status}</p>

            <p>🏗️ Material: ${order.material}</p>

            <p>📅 Deadline: ${order.deadline}</p>

            <p>⏰ Delivery: ${order.delivery_time}</p>

            <p>🕒 Created: ${order.created_at || "N/A"}</p>

            <p>📝 Note: ${order.latest_note}</p>

        </div>

        `;
    });
}

// =========================
// INITIAL LOAD
// =========================

loadOrders();

// =========================
// AUTO REFRESH
// =========================

setInterval(loadOrders, 3000);

// =========================
// ENTER KEY SUPPORT
// =========================

document
.getElementById("message")
.addEventListener("keypress", function(e) {

    if (e.key === "Enter") {

        sendMessage();
    }

});