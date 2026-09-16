document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-destructive='true']").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm("This action removes local runtime resources. Continue?")) {
        event.preventDefault();
        return;
      }
      const confirmation = form.querySelector("input[name='confirm']");
      if (confirmation) confirmation.value = "true";
    });
  });
});
