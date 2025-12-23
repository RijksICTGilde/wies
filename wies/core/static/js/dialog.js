document.addEventListener('DOMContentLoaded', function() {

    const anyDialog = document.querySelector("[closedby='any']");

    const closeBtns = document.querySelectorAll(".close");

    anyDialogContent = document.getElementById("dialogContent")
    if (anyDialogContent){
        anyDialog.showModal();
    }

    closeBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
        btn.parentElement.close();
    });
    });

    anyDialog.addEventListener("close", () => {
        console.log("closed");
        window.location.assign('/dialog');
    })    

});