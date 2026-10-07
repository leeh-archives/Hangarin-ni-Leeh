// Shows an "Install app" button when the browser says Hangarin can be installed.
(function () {
    var button = document.getElementById("install-app");
    var saved = null;

    if (!button) {
        return;
    }

    window.addEventListener("beforeinstallprompt", function (event) {
        event.preventDefault();
        saved = event;
        button.hidden = false;
    });

    button.addEventListener("click", function () {
        if (!saved) {
            return;
        }
        saved.prompt();
        saved.userChoice.then(function () {
            saved = null;
            button.hidden = true;
        });
    });

    window.addEventListener("appinstalled", function () {
        button.hidden = true;
    });
})();
