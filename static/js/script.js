const filterButtons = document.querySelectorAll(".filter-pill");
const purposeInput = document.getElementById("purpose");

filterButtons.forEach(button => {
    button.addEventListener("click", () => {

        filterButtons.forEach(btn => {
            btn.classList.remove("active");
        });

        button.classList.add("active");

        purposeInput.value = button.dataset.purpose;
    });
});