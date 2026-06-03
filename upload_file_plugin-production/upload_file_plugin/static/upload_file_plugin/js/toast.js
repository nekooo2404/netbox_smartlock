function showCustomToast(message,status="success", title = "",  delay = 10000) {
  const toast = document.createElement("div");
  toast.className = "toast toast-dark border-0 shadow-sm";
  toast.setAttribute("role", "alert");
  toast.setAttribute("aria-live", "assertive");
  toast.setAttribute("aria-atomic", "true");
  toast.setAttribute("data-bs-delay", delay);

  toast.innerHTML = `
    <div class="toast-header text-bg-${status}">
      <i class="mdi mdi-${iconFromStatus(status)} me-1"></i>
      ${title}
      <button type="button" class="btn-close me-0 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
    <div class="toast-body">
      ${message}
    </div>
  `;

  // Find or create container
  let container = document.getElementById("django-messages");
  if (!container) {
    container = document.createElement("div");
    container.id = "django-messages";
    container.className = "toast-container position-fixed bottom-0 end-0 p-3";
    document.body.appendChild(container);
  }

  container.appendChild(toast);

  // Show using bootstrap
  if (window.bootstrap?.Toast) {
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
  } else {
    toast.classList.add("show"); // fallback if Bootstrap is unavailable
    setTimeout(() => {
      toast.remove();
    }, delay);
  }
}

function iconFromStatus(status) {
  switch (status) {
    case "success": return "check-circle-outline";
    case "danger": return "alert-circle-outline";
    case "warning": return "alert-outline";
    case "info": return "information-outline";
    default: return "information-outline";
  }
}
