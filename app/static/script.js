// ============================================================
// JYOTISH AI - FRONTEND SCRIPT
// ============================================================


// ============================================================
// GET HTML ELEMENTS
// ============================================================

const birthScreen = document.getElementById("birth-screen");
const chatScreen = document.getElementById("chat-screen");

const birthForm = document.getElementById("birth-form");
const chatForm = document.getElementById("chat-form");

const chatMessages = document.getElementById("chat-messages");

const changeDetailsBtn =
    document.getElementById("change-details-btn");

const questionInput =
    document.getElementById("user-question");


// ============================================================
// TIME ELEMENTS
// ============================================================

const hourSelect =
    document.getElementById("birth-hour");

const minuteSelect =
    document.getElementById("birth-minute");

const ampmSelect =
    document.getElementById("birth-ampm");


// ============================================================
// STORE USER BIRTH DETAILS
// ============================================================

let userBirthDetails = {};

// ============================================================
// CONVERSATION STATE
// ============================================================

let currentConversationId = null;

const conversationList =
    document.getElementById("conversation-list");

const newChatButton =
    document.getElementById("new-chat-btn");



// ============================================================
// SETUP HOUR AND MINUTE DROPDOWNS
// ============================================================

function setupTimeDropdowns() {

    // --------------------------------------------------------
    // HOURS
    // --------------------------------------------------------

    for (let hour = 1; hour <= 12; hour++) {

        const option =
            document.createElement("option");

        const value =
            hour.toString().padStart(2, "0");

        option.value = value;

        option.textContent = value;

        hourSelect.appendChild(option);

    }


    // --------------------------------------------------------
    // MINUTES
    // --------------------------------------------------------

    for (let minute = 0; minute <= 59; minute++) {

        const option =
            document.createElement("option");

        const value =
            minute.toString().padStart(2, "0");

        option.value = value;

        option.textContent = value;

        minuteSelect.appendChild(option);

    }

}


// ============================================================
// CONVERT 12 HOUR TIME TO 24 HOUR TIME
// ============================================================

function convertTo24Hour(hour, minute, ampm) {

    let hour24 = parseInt(hour);

    const minuteValue =
        parseInt(minute);


    // --------------------------------------------------------
    // 12 AM = 00
    // --------------------------------------------------------

    if (ampm === "AM" && hour24 === 12) {

        hour24 = 0;

    }


    // --------------------------------------------------------
    // PM
    // --------------------------------------------------------

    if (ampm === "PM" && hour24 !== 12) {

        hour24 = hour24 + 12;

    }


    return {

        hour: hour24,

        minute: minuteValue

    };

}


// ============================================================
// START CONSULTATION
// ============================================================

birthForm.addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();


        // ----------------------------------------------------
        // GET VALUES
        // ----------------------------------------------------

        const name =
            document
                .getElementById("name")
                .value
                .trim();


        const gender =
            document
                .getElementById("gender")
                .value;


        const dateOfBirth =
            document
                .getElementById("date_of_birth")
                .value;


        const birthHour =
            hourSelect.value;


        const birthMinute =
            minuteSelect.value;


        const birthAMPM =
            ampmSelect.value;


        const placeOfBirth =
            document
                .getElementById("place_of_birth")
                .value
                .trim();


        // ----------------------------------------------------
        // VALIDATE TIME
        // ----------------------------------------------------

        if (
            !birthHour ||
            !birthMinute ||
            !birthAMPM
        ) {

            alert(
                "Please select your complete time of birth."
            );

            return;

        }


        // ----------------------------------------------------
        // CONVERT TIME TO 24 HOUR FORMAT
        // ----------------------------------------------------

        const convertedTime =
            convertTo24Hour(
                birthHour,
                birthMinute,
                birthAMPM
            );


        // ----------------------------------------------------
        // FORMAT TIME FOR DISPLAY
        // ----------------------------------------------------

        const displayTime =
            `${birthHour}:${birthMinute} ${birthAMPM}`;


        // ----------------------------------------------------
        // STORE USER DETAILS
        // ----------------------------------------------------

        userBirthDetails = {

            name: name,

            gender: gender,

            date_of_birth: dateOfBirth,

            // Display time

            time_of_birth:
                displayTime,

            // API time

            hour:
                convertedTime.hour,

            minute:
                convertedTime.minute,

            place_of_birth:
                placeOfBirth

        };


        console.log(
            "User Birth Details:",
            userBirthDetails
        );


        // ----------------------------------------------------
        // GENERATE BIRTH CHART BEFORE ENTERING CHAT
        // ----------------------------------------------------

        const submitButton =
            birthForm.querySelector(
                'button[type="submit"]'
            );

        const originalButtonText =
            submitButton ? submitButton.textContent : "";

        try {

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent =
                    "✨ Generating your birth chart...";
            }

            const response = await fetch(
                "/generate-chart",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Authorization":
                            "Bearer " +
                            localStorage.getItem(
                                "jyotish_token"
                            )
                    },

                    body: JSON.stringify(
                        userBirthDetails
                    )
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                    "Failed to generate birth chart"
                );
            }

            // Store astrology JSON for the current session
            window.astrologyData = data;

            console.log(
                "Birth Chart Generated:",
                data
            );

            // Go directly to chat - do NOT display JSON
            birthScreen.classList.add("hidden");
            chatScreen.classList.remove("hidden");

            chatMessages.innerHTML = "";

            currentConversationId = null;

            addMessage(
                `Hello ${name}! Welcome to Jyotish AI.

I'm Raj Rao, your Vedic Life Counselor. I have your birth details and astrological information with me.

What would you like to explore today?`,
                "ai"
            );

            // Load any previous conversations for this user.
            loadConversations();

            questionInput.focus();

        } catch (error) {

            console.error(
                "Birth chart generation error:",
                error
            );

            alert(
                error.message ||
                "Unable to generate your birth chart. Please try again."
            );

        } finally {

            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent =
                    originalButtonText;
            }
        }

    }
);




// ============================================================
// CONVERSATION HISTORY
// ============================================================

function getAuthHeaders() {

    return {
        "Authorization":
            "Bearer " +
            localStorage.getItem("jyotish_token")
    };
}


async function loadConversations() {

    if (!conversationList) {
        return;
    }

    conversationList.innerHTML =
        '<div class="conversation-loading">Loading chats...</div>';

    try {

        const response = await fetch(
            "/conversations",
            {
                method: "GET",
                headers: getAuthHeaders()
            }
        );

        const data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Unable to load chat history."
            );
        }

        const conversations =
            data.conversations || [];

        renderConversationList(
            conversations
        );

        // Automatically open the most recent conversation
        // when the user enters the chat.
        //
        // If the user is already viewing a conversation,
        // do not replace it.
        if (
            conversations.length > 0 &&
            currentConversationId === null
        ) {

            await openConversation(
                conversations[0].id
            );

        }

    } catch (error) {

        console.error(
            "Conversation history error:",
            error
        );

        conversationList.innerHTML =
            '<div class="conversation-empty">Unable to load chats.</div>';
    }
}


function renderConversationList(conversations) {

    if (!conversationList) {
        return;
    }

    conversationList.innerHTML = "";

    if (!conversations.length) {

        conversationList.innerHTML =
            '<div class="conversation-empty">No previous chats yet.</div>';

        return;
    }

    conversations.forEach(
        function (conversation) {

            const button =
                document.createElement("button");

            button.type = "button";

            button.className =
                "conversation-item";

            if (
                currentConversationId ===
                conversation.id
            ) {

                button.classList.add(
                    "active"
                );
            }

            const title =
                document.createElement("div");

            title.className =
                "conversation-title";

            title.textContent =
                conversation.title ||
                "Previous Chat";


            const meta =
                document.createElement("div");

            meta.className =
                "conversation-meta";

            meta.textContent =
                `${conversation.message_count || 0} messages`;


            button.appendChild(title);
            button.appendChild(meta);


            button.addEventListener(
                "click",
                function () {

                    openConversation(
                        conversation.id
                    );

                }
            );


            conversationList.appendChild(
                button
            );

        }
    );
}


async function openConversation(conversationId) {

    try {

        const response = await fetch(
            `/conversations/${conversationId}`,
            {
                method: "GET",
                headers: getAuthHeaders()
            }
        );

        const data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Unable to open conversation."
            );
        }

        currentConversationId =
            data.conversation.id;


        chatMessages.innerHTML = "";


        /*
         * Render every saved Q&A from
         * first message to latest message.
         */

        const messages =
            data.messages || [];

        messages.forEach(
            function (message) {

                addMessage(
                    message.user_message,
                    "user"
                );

                addMessage(
                    message.ai_response,
                    "ai"
                );

            }
        );


        if (!messages.length) {

            addMessage(
                "This conversation is empty.",
                "ai"
            );

        }


        renderConversationList(
            await fetchConversationListData()
        );

        scrollToBottom();

        questionInput.focus();

    } catch (error) {

        console.error(
            "Open conversation error:",
            error
        );

        alert(
            error.message ||
            "Unable to open this conversation."
        );
    }
}


async function fetchConversationListData() {

    const response = await fetch(
        "/conversations",
        {
            method: "GET",
            headers: getAuthHeaders()
        }
    );

    if (!response.ok) {
        return [];
    }

    const data =
        await response.json();

    return data.conversations || [];
}


async function startNewChat() {

    currentConversationId = null;

    chatMessages.innerHTML = "";

    const storedUser =
        localStorage.getItem(
            "jyotish_user"
        );

    let name = "there";

    if (storedUser) {

        try {

            name =
                JSON.parse(
                    storedUser
                ).name || "there";

        } catch (error) {

            console.error(
                "Unable to read user:",
                error
            );

        }

    }

    addMessage(
        `Hello ${name}! Welcome to Jyotish AI.

I'm Raj Rao, your Vedic Life Counselor. I have your birth details and astrological information with me.

What would you like to explore today?`,
        "ai"
    );

    try {

        const conversations =
            await fetchConversationListData();

        renderConversationList(
            conversations
        );

    } catch (error) {

        console.error(
            "Unable to refresh conversation history:",
            error
        );

    }

    questionInput.focus();

}

if (newChatButton) {

    newChatButton.addEventListener(
        "click",
        function () {

            startNewChat();

        }
    );

}


// ============================================================
// ADD MESSAGE TO CHAT
// ============================================================

function escapeHtml(text) {
    return String(text ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function formatInlineMarkdown(text) {

    // Preserve Gemini's <br> tags as line breaks inside
    // paragraphs and especially inside Markdown table cells.
    let value = String(text ?? "")
        .replace(/<br\s*\/?>/gi, "__MARKDOWN_BR__");

    value = escapeHtml(value);

    // Code
    value = value.replace(
        /`([^`]+)`/g,
        "<code>$1</code>"
    );

    // Bold
    value = value.replace(
        /\*\*(.+?)\*\*/g,
        "<strong>$1</strong>"
    );

    // Italic
    value = value.replace(
        /(?<!\*)\*([^*\n]+)\*(?!\*)/g,
        "<em>$1</em>"
    );

    // Restore only the <br> tags that came from Gemini's
    // formatting. They are safe because the original content
    // was escaped before this replacement.
    value = value.replace(
        /__MARKDOWN_BR__/g,
        "<br>"
    );

    return value;
}


function renderMarkdown(message) {

    let text = String(message ?? "");

    const lines = text.split(/\r?\n/);

    let html = "";
    let i = 0;

    while (i < lines.length) {

        const line = lines[i];

        // Empty line
        if (!line.trim()) {
            i++;
            continue;
        }


        // Markdown table
        if (
            line.trim().startsWith("|") &&
            i + 1 < lines.length &&
            /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[i + 1])
        ) {

            const parseRow = function(row) {
                return row
                    .trim()
                    .replace(/^\|/, "")
                    .replace(/\|$/, "")
                    .split("|")
                    .map(cell => cell.trim());
            };

            const headers = parseRow(line);

            html += "<div class=\"markdown-table-wrapper\">";
            html += "<table class=\"markdown-table\">";
            html += "<thead><tr>";

            headers.forEach(function(cell) {
                html += "<th>" +
                    formatInlineMarkdown(cell) +
                    "</th>";
            });

            html += "</tr></thead>";
            html += "<tbody>";

            i += 2;

            while (
                i < lines.length &&
                lines[i].trim().startsWith("|")
            ) {

                const cells = parseRow(lines[i]);

                html += "<tr>";

                headers.forEach(function(_, index) {

                    const cell =
                        cells[index] !== undefined
                            ? cells[index]
                            : "";

                    html += "<td>" +
                        formatInlineMarkdown(cell) +
                        "</td>";
                });

                html += "</tr>";

                i++;
            }

            html += "</tbody></table></div>";

            continue;
        }


        // Heading
        const headingMatch =
            line.match(/^\s*(#{1,6})\s+(.+)$/);

        if (headingMatch) {

            const level =
                headingMatch[1].length;

            html +=
                "<h" + level + ">" +
                formatInlineMarkdown(headingMatch[2]) +
                "</h" + level + ">";

            i++;
            continue;
        }


        // Bullet list
        if (/^\s*[-*+]\s+/.test(line)) {

            html += "<ul>";

            while (
                i < lines.length &&
                /^\s*[-*+]\s+/.test(lines[i])
            ) {

                const item =
                    lines[i].replace(
                        /^\s*[-*+]\s+/,
                        ""
                    );

                html +=
                    "<li>" +
                    formatInlineMarkdown(item) +
                    "</li>";

                i++;
            }

            html += "</ul>";

            continue;
        }


        // Numbered list
        if (/^\s*\d+\.\s+/.test(line)) {

            html += "<ol>";

            while (
                i < lines.length &&
                /^\s*\d+\.\s+/.test(lines[i])
            ) {

                const item =
                    lines[i].replace(
                        /^\s*\d+\.\s+/,
                        ""
                    );

                html +=
                    "<li>" +
                    formatInlineMarkdown(item) +
                    "</li>";

                i++;
            }

            html += "</ol>";

            continue;
        }


        // Normal paragraph
        let paragraph = line;

        i++;

        while (
            i < lines.length &&
            lines[i].trim() &&
            !/^\s*(#{1,6})\s+/.test(lines[i]) &&
            !/^\s*[-*+]\s+/.test(lines[i]) &&
            !/^\s*\d+\.\s+/.test(lines[i]) &&
            !lines[i].trim().startsWith("|")
        ) {

            paragraph += " " + lines[i].trim();
            i++;
        }

        html +=
            "<p>" +
            formatInlineMarkdown(paragraph) +
            "</p>";
    }

    return html;
}


function addMessage(message, sender) {

    const messageDiv =
        document.createElement("div");


    messageDiv.classList.add(
        "message"
    );


    if (sender === "user") {

        messageDiv.classList.add(
            "user-message"
        );

    } else {

        messageDiv.classList.add(
            "ai-message"
        );

    }


    // Render Gemini Markdown safely.
    // This supports headings, bold, italic,
    // bullets, numbered lists, and Markdown tables.
    messageDiv.innerHTML =
        renderMarkdown(message);


    chatMessages.appendChild(
        messageDiv
    );


    scrollToBottom();

    return messageDiv;

}


// ============================================================

// ============================================================
// SCROLL CHAT TO BOTTOM
// ============================================================

function scrollToBottom() {

    chatMessages.scrollTop =
        chatMessages.scrollHeight;

}


// ============================================================
// CREATE THINKING MESSAGE
// ============================================================

function createLoadingMessage() {

    const loadingDiv =
        document.createElement("div");


    loadingDiv.classList.add(
        "message",
        "ai-message",
        "loading-message"
    );


    loadingDiv.innerHTML =
        "✨ Raj Rao is reflecting on your question...";


    chatMessages.appendChild(
        loadingDiv
    );


    scrollToBottom();


    return loadingDiv;

}


// ============================================================
// SEND CHAT QUESTION
// ============================================================

chatForm.addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();


        // ----------------------------------------------------
        // GET QUESTION
        // ----------------------------------------------------

        const question =
            questionInput.value.trim();


        if (!question) {

            return;

        }


        // ----------------------------------------------------
        // DISPLAY USER MESSAGE
        // ----------------------------------------------------

        addMessage(
            question,
            "user"
        );


        // Clear input

        questionInput.value = "";


        // Disable input while AI is responding

        questionInput.disabled = true;


        // Disable send button

        const sendButton =
            chatForm.querySelector("button");

        sendButton.disabled = true;


        // ----------------------------------------------------
        // SHOW LOADING MESSAGE
        // ----------------------------------------------------

        const loadingMessage =
            createLoadingMessage();


        try {


            // ------------------------------------------------
            // PREPARE DATA
            // ------------------------------------------------

            const requestData = {

                name:
                    userBirthDetails.name,

                gender:
                    userBirthDetails.gender,

                date_of_birth:
                    userBirthDetails.date_of_birth,

                time_of_birth:
                    userBirthDetails.time_of_birth,

                hour:
                    userBirthDetails.hour,

                minute:
                    userBirthDetails.minute,

                place_of_birth:
                    userBirthDetails.place_of_birth,

                question:
                    question,

                conversation_id:
                    currentConversationId

            };


            console.log(
                "Sending to Backend:",
                requestData
            );


            // ------------------------------------------------
            // CALL BACKEND
            // ------------------------------------------------

            const response =
                await fetch(
                    "/chat",
                    {

                        method:
                            "POST",

                        headers: {

                            "Content-Type":
                                "application/json",

                            "Authorization":
                                "Bearer " +
                                localStorage.getItem(
                                    "jyotish_token"
                                )

                        },

                        body:
                            JSON.stringify(
                                requestData
                            )

                    }
                );


            // ------------------------------------------------
            // HANDLE HTTP ERROR
            // ------------------------------------------------

            if (!response.ok) {

                const errorData =
                    await response.text();

                console.error(
                    "Backend Error:",
                    response.status,
                    errorData
                );

                throw new Error(
                    `Server error: ${response.status} - ${errorData}`
                );

            }


            // ------------------------------------------------
            // GET JSON RESPONSE
            // ------------------------------------------------

            const data =
                await response.json();


            console.log(
                "Backend Response:",
                data
            );


            // ------------------------------------------------
            // REMOVE LOADING
            // ------------------------------------------------

            loadingMessage.remove();


            // ------------------------------------------------
            // DISPLAY RESPONSE
            // ------------------------------------------------

            if (data.status === "success") {

                // Keep this chat attached to the same conversation.
                if (data.conversation_id) {

                    currentConversationId =
                        data.conversation_id;

                }

                const aiMessage =
                    addMessage(
                        data.message,
                        "ai"
                    );

                // Position the chat at the FIRST LINE
                // of the new AI response instead of the
                // bottom of a long response.
                requestAnimationFrame(function () {

                    chatMessages.scrollTop =
                        aiMessage.offsetTop - 10;

                });

                // Refresh the sidebar so newly created chats
                // immediately appear in Previous Chats.
                try {

                    const conversations =
                        await fetchConversationListData();

                    renderConversationList(
                        conversations
                    );

                } catch (historyError) {

                    console.error(
                        "Unable to refresh conversation history:",
                        historyError
                    );

                }

            } else {

                addMessage(
                    data.message ||
                    "Sorry, I couldn't process your question. Please try again.",
                    "ai"
                );

            }


        } catch (error) {


            console.error(
                "Chat Error:",
                error
            );


            // Remove loading message

            loadingMessage.remove();


            // Show error

            addMessage(
                "I'm sorry, something went wrong while processing your question. Please try again in a moment.",
                "ai"
            );


        } finally {


            // ------------------------------------------------
            // ENABLE CHAT AGAIN
            // ------------------------------------------------

            questionInput.disabled = false;

            sendButton.disabled = false;


            // Focus input

            questionInput.focus();

        }

    }
);


// ============================================================
// CHANGE BIRTH DETAILS
// ============================================================

changeDetailsBtn.addEventListener(
    "click",
    function () {


        // Hide chat

        chatScreen.classList.add(
            "hidden"
        );


        // Show birth screen

        birthScreen.classList.remove(
            "hidden"
        );


        // Clear messages

        chatMessages.innerHTML = "";


        // Reset user details

        userBirthDetails = {};


        // Reset form

        birthForm.reset();


        // Focus name field

        document
            .getElementById("name")
            .focus();

    }
);


// ============================================================
// INITIALIZE APPLICATION
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        setupTimeDropdowns();

        console.log(
            "✨ Jyotish AI frontend loaded successfully."
        );

    }
);


// ============================================================
// AUTHENTICATION
// ============================================================

const authScreen = document.getElementById("auth-screen");

const loginPanel =
    document.getElementById("login-panel");

const registerPanel =
    document.getElementById("register-panel");

const loginForm =
    document.getElementById("login-form");

const registerForm =
    document.getElementById("register-form");


// ------------------------------------------------------------
// SWITCH TO REGISTER
// ------------------------------------------------------------

document.getElementById("show-register")
    .addEventListener("click", function () {

        loginPanel.style.display = "none";

        registerPanel.style.display = "block";

    });


// ------------------------------------------------------------
// SWITCH TO LOGIN
// ------------------------------------------------------------

document.getElementById("show-login")
    .addEventListener("click", function () {

        registerPanel.style.display = "none";

        loginPanel.style.display = "block";

    });


// ------------------------------------------------------------
// REGISTER
// ------------------------------------------------------------

registerForm.addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();

        const name =
            document.getElementById(
                "register-name"
            ).value.trim();

        const email =
            document.getElementById(
                "register-email"
            ).value.trim();

        const password =
            document.getElementById(
                "register-password"
            ).value;

        try {

            const response = await fetch(
                "/register",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        name: name,
                        email: email,
                        password: password
                    })
                }
            );

            const data =
                await response.json();

            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "Registration failed"
                );

            }

            localStorage.setItem(
                "jyotish_token",
                data.access_token
            );

            localStorage.setItem(
                "jyotish_user",
                JSON.stringify(data.user)
            );

            updateLoggedInUser();
            updateBirthScreenUser();

            // New user → Birth details

            authScreen.classList.add(
                "hidden"
            );

            birthScreen.classList.remove(
                "hidden"
            );

            // Automatically fill name

            document.getElementById(
                "name"
            ).value = data.user.name;

            alert(
                "Account created successfully! Please enter your birth details."
            );

        } catch (error) {

            alert(
                error.message ||
                "Registration failed."
            );

        }

    }
);


// ------------------------------------------------------------
// LOGIN
// ------------------------------------------------------------

loginForm.addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();

        const email =
            document.getElementById(
                "login-email"
            ).value.trim();

        const password =
            document.getElementById(
                "login-password"
            ).value;

        try {

            const response = await fetch(
                "/login",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        email: email,
                        password: password
                    })
                }
            );

            const data =
                await response.json();

            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "Login failed"
                );

            }

            localStorage.setItem(
                "jyotish_token",
                data.access_token
            );

            localStorage.setItem(
                "jyotish_user",
                JSON.stringify(data.user)
            );

            updateLoggedInUser();
            updateBirthScreenUser();


            // Existing user

            if (data.user.has_birth_details) {

                alert(
                    "Login successful! Your saved birth details will be loaded."
                );

                // Load saved birth details

                userBirthDetails = {
                    name: data.user.name,
                    gender: data.user.gender,
                    date_of_birth: data.user.date_of_birth,
                    hour: data.user.hour,
                    minute: data.user.minute,
                    time_of_birth:
                        String(data.user.hour).padStart(2, "0") +
                        ":" +
                        String(data.user.minute).padStart(2, "0"),
                    place_of_birth: data.user.place_of_birth
                };

                console.log(
                    "Loaded Birth Details:",
                    userBirthDetails
                );

                authScreen.classList.add(
                    "hidden"
                );

                chatScreen.classList.remove(
                    "hidden"
                );

                // Start with no active conversation.
                // The user can select any previous chat
                // from the history sidebar.
                currentConversationId = null;

                chatMessages.innerHTML = "";

                addMessage(
                    `Hello ${userBirthDetails.name}! Welcome back to Jyotish AI.

You can continue one of your previous conversations from the sidebar, or start a new chat.`,
                    "ai"
                );

                // Load previous conversations.
                loadConversations();

            } else {

                // New user without birth details

                authScreen.classList.add(
                    "hidden"
                );

                birthScreen.classList.remove(
                    "hidden"
                );

                document.getElementById(
                    "name"
                ).value = data.user.name;

            }

        } catch (error) {

            alert(
                error.message ||
                "Login failed."
            );

        }

    }
);



// ============================================================
// SHOW LOGGED-IN USER
// ============================================================

function updateLoggedInUser() {

    const userElement =
        document.getElementById(
            "logged-in-user"
        );

    const storedUser =
        localStorage.getItem(
            "jyotish_user"
        );

    if (
        userElement &&
        storedUser
    ) {

        try {

            const user =
                JSON.parse(
                    storedUser
                );

            userElement.textContent =
                "👤 " + user.name;

        } catch (error) {

            console.error(
                "Unable to load user:",
                error
            );

        }

    }

}


// ============================================================
// LOGOUT
// ============================================================

const logoutButton =
    document.getElementById(
        "logout-btn"
    );


if (logoutButton) {

    logoutButton.addEventListener(
        "click",
        function () {

            const confirmLogout =
                confirm(
                    "Are you sure you want to logout?"
                );

            if (!confirmLogout) {
                return;
            }


            // Remove authentication data

            localStorage.removeItem(
                "jyotish_token"
            );

            localStorage.removeItem(
                "jyotish_user"
            );


            // Clear current session data

            window.astrologyData = null;


            // Hide other screens

            chatScreen.classList.add(
                "hidden"
            );

            birthScreen.classList.add(
                "hidden"
            );


            // Show authentication screen

            authScreen.classList.remove(
                "hidden"
            );


            // Show login panel

            registerPanel.style.display =
                "none";

            loginPanel.style.display =
                "block";


            // Clear login form

            loginForm.reset();


            console.log(
                "👋 User logged out successfully"
            );

        }
    );

}


// ============================================================
// LOAD USER NAME ON PAGE
// ============================================================

updateLoggedInUser();



// ============================================================
// BIRTH SCREEN USER + LOGOUT
// ============================================================

function updateBirthScreenUser() {

    const userElement =
        document.getElementById(
            "birth-logged-in-user"
        );

    const storedUser =
        localStorage.getItem(
            "jyotish_user"
        );

    if (userElement && storedUser) {

        try {

            const user = JSON.parse(storedUser);

            userElement.textContent =
                "👤 " + user.name;

        } catch (error) {

            console.error(
                "Unable to load birth screen user",
                error
            );

        }
    }
}


const birthLogoutButton =
    document.getElementById(
        "birth-logout-btn"
    );


if (birthLogoutButton) {

    birthLogoutButton.addEventListener(
        "click",
        function () {

            if (!confirm("Are you sure you want to logout?")) {
                return;
            }

            localStorage.removeItem(
                "jyotish_token"
            );

            localStorage.removeItem(
                "jyotish_user"
            );

            window.astrologyData = null;


            birthScreen.classList.add("hidden");
            chatScreen.classList.add("hidden");

            authScreen.classList.remove("hidden");

            registerPanel.style.display = "none";
            loginPanel.style.display = "block";

            console.log(
                "👋 User logged out from birth screen"
            );

        }
    );

}


updateBirthScreenUser();



// ============================================================
// DOWNLOAD BIRTH CHART PDF
// ============================================================

document.addEventListener("DOMContentLoaded", function () {

    const downloadButton = document.getElementById("download-chart-btn");

    if (!downloadButton) {
        return;
    }

    downloadButton.addEventListener("click", async function () {

        const token = localStorage.getItem("jyotish_token");

        if (!token) {
            alert("Please login again to download your chart.");
            return;
        }

        const originalText = downloadButton.innerHTML;

        try {

            downloadButton.disabled = true;
            downloadButton.innerHTML = "⏳ Preparing...";

            const response = await fetch("/download-chart-pdf", {
                method: "GET",
                headers: {
                    "Authorization": "Bearer " + token
                }
            });

            if (!response.ok) {

                let message = "Unable to download chart.";

                try {
                    const errorData = await response.json();

                    if (errorData.detail) {
                        message = errorData.detail;
                    }
                } catch (e) {}

                throw new Error(message);
            }

            const blob = await response.blob();

            const url = window.URL.createObjectURL(blob);

            const link = document.createElement("a");
            link.href = url;
            link.download = "birth_chart.pdf";

            document.body.appendChild(link);
            link.click();
            link.remove();

            window.URL.revokeObjectURL(url);

        } catch (error) {

            console.error("Chart PDF download error:", error);

            alert(
                error.message ||
                "Unable to download your birth chart. Please try again."
            );

        } finally {

            downloadButton.disabled = false;
            downloadButton.innerHTML = originalText;

        }
    });

});
