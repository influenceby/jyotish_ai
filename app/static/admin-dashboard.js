const token = localStorage.getItem("admin_token");

let selectedUserId = null;
let selectedUserName = "";
let messageOffset = 0;
const messageLimit = 50;


if (!token) {
    window.location.href = "/admin";
}


async function apiRequest(url) {

    const response = await fetch(url, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    if (response.status === 401 || response.status === 403) {

        localStorage.removeItem("admin_token");

        window.location.href = "/admin";

        return null;
    }

    return await response.json();
}


async function loadData() {

    try {

        const usersData =
            await apiRequest("/admin/users");

        if (!usersData) {
            return;
        }

        document.getElementById(
            "totalUsers"
        ).textContent = usersData.total_users;


        renderUsers(usersData.users);

    }
    catch (error) {

        console.error("Admin dashboard error:", error);

        alert("Unable to load dashboard data.");
    }

}


function renderUsers(users) {

    const tableBody =
        document.getElementById("usersTableBody");

    tableBody.innerHTML = "";


    users.forEach(user => {

        const row = document.createElement("tr");

        row.style.cursor = "pointer";

        const astrologyStatus =
            user.has_astrology_data
                ? "✅ Generated"
                : "❌ Not Generated";


        row.innerHTML = `
            <td>${user.id}</td>
            <td>${escapeHtml(user.name || "")}</td>
            <td>${escapeHtml(user.email || "")}</td>
            <td>${escapeHtml(user.gender || "-")}</td>
            <td>${escapeHtml(user.place_of_birth || "-")}</td>
            <td>${astrologyStatus}</td>
            <td>${formatDate(user.created_at)}</td>
        `;


        row.addEventListener("click", () => {

            selectedUserId = user.id;
            selectedUserName = user.name || "User";
            messageOffset = 0;

            loadUserMessages(true);

        });


        tableBody.appendChild(row);

    });

}


async function loadUserMessages(reset = false) {

    if (!selectedUserId) {
        return;
    }


    try {

        if (reset) {

            messageOffset = 0;

            document.getElementById(
                "messagesContainer"
            ).innerHTML = "";

        }


        showMessages();


        document.getElementById(
            "messagesTitle"
        ).textContent =
            `Messages - ${selectedUserName}`;


        const data = await apiRequest(
            `/admin/users/${selectedUserId}/messages?limit=${messageLimit}&offset=${messageOffset}`
        );


        if (!data) {
            return;
        }


        document.getElementById(
            "totalMessages"
        ).textContent = data.total_messages;


        renderUserMessages(
            data.messages,
            reset
        );


        messageOffset += data.messages.length;


        const loadMoreButton =
            document.getElementById("loadMoreMessages");


        if (loadMoreButton) {

            if (
                messageOffset < data.total_messages
            ) {
                loadMoreButton.style.display = "block";
            }
            else {
                loadMoreButton.style.display = "none";
            }

        }

    }
    catch (error) {

        console.error(
            "Unable to load user messages:",
            error
        );

        alert("Unable to load user messages.");

    }

}


function renderUserMessages(messages, reset) {

    const container =
        document.getElementById(
            "messagesContainer"
        );


    if (reset) {
        container.innerHTML = "";
    }


    if (!messages.length && reset) {

        container.innerHTML =
            "<p>No messages available for this user.</p>";

        return;

    }


    messages.forEach(message => {

        const card =
            document.createElement("div");

        card.className = "message-card";


        card.innerHTML = `

            <div class="message-question">

                <strong>User Question:</strong>

                <p>
                    ${escapeHtml(message.user_message || "")}
                </p>

            </div>


            <div class="message-answer">

                <strong>AI Response:</strong>

                <p>
                    ${escapeHtml(message.ai_response || "")}
                </p>

            </div>


            <div class="message-date">

                ${formatDate(message.created_at)}

            </div>

        `;


        container.appendChild(card);

    });

}


function loadMoreMessages() {

    loadUserMessages(false);

}


function showUsers() {

    document.getElementById(
        "usersSection"
    ).style.display = "block";


    document.getElementById(
        "messagesSection"
    ).style.display = "none";

}


function showMessages() {

    document.getElementById(
        "usersSection"
    ).style.display = "none";


    document.getElementById(
        "messagesSection"
    ).style.display = "block";

}


function logout() {

    localStorage.removeItem("admin_token");

    window.location.href = "/admin";

}


function formatDate(dateString) {

    if (!dateString) {
        return "-";
    }

    return new Date(
        dateString
    ).toLocaleString();

}


function escapeHtml(value) {

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}


loadData();
