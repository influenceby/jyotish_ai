const adminLoginForm = document.getElementById("adminLoginForm");
const errorMessage = document.getElementById("errorMessage");

adminLoginForm.addEventListener("submit", async (event) => {

    event.preventDefault();

    errorMessage.textContent = "";

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    try {

        const response = await fetch("/admin/login", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                email: email,
                password: password
            })
        });


        const data = await response.json();


        if (!response.ok) {

            errorMessage.textContent =
                data.detail || "Invalid admin credentials.";

            return;
        }


        localStorage.setItem(
            "admin_token",
            data.access_token
        );


        window.location.href =
            "/static/admin-dashboard.html";


    } catch (error) {

        console.error(error);

        errorMessage.textContent =
            "Unable to connect to the server.";

    }

});
