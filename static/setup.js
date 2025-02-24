document.getElementById("save-goals-btn").addEventListener("click", function() {
    const userData = {
        gender: document.getElementById("gender").value,
        age: parseInt(document.getElementById("age").value),
        height: parseFloat(document.getElementById("height").value),
        weight: parseFloat(document.getElementById("weight").value),
        activity_level: document.getElementById("activity_level").value,
        goal_type: document.getElementById("goal_type").value
    };

    fetch("/setup_user", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(userData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("Målene er lagret!");
            window.location.href = "/index"; // Sender deg direkte til index-siden
        } else {
            alert("Noe gikk galt. Prøv igjen.");
        }
    })
    .catch(error => {
        console.error("Feil ved lagring av mål:", error);
        alert("Feil ved lagring av mål.");
    });
});
