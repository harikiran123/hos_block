document.addEventListener("DOMContentLoaded", function () {
    const image = document.getElementById("hospital-image");
    const welcomeMessage = document.getElementById("welcome-message");

    image.addEventListener("click", function () {
        document.body.classList.add("show-message");
        welcomeMessage.style.display = "block";
    });
});
