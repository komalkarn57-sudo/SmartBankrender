function loginUser(event) {

    event.preventDefault();

    const email =
        document.getElementById("loginEmail").value;

    const password =
        document.getElementById("loginPassword").value;

    const message =
        document.getElementById("loginMessage");


    if (email === "" || password === "") {

        message.innerText =
            "Please enter all details.";

        message.style.color = "red";

        return;
    }


    message.innerText =
        "Login form submitted successfully.";

    message.style.color = "#4c805f";

}


function registerUser(event) {

    event.preventDefault();


    const password =
        document.getElementById("password").value;

    const confirmPassword =
        document.getElementById("confirmPassword").value;

    const message =
        document.getElementById("registerMessage");


    if (password !== confirmPassword) {

        message.innerText =
            "Passwords do not match.";

        message.style.color = "red";

        return;
    }


    message.innerText =
        "Account form submitted successfully.";

    message.style.color = "#4c805f";

}