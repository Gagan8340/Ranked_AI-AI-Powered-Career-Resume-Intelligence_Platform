const formatTimeAgo = (dateString) => {
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hours ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} days ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 4) return `${weeks} weeks ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} months ago`;
  const years = Math.floor(days / 365);
  return `${years} years ago`;
};

const updateTimeAgo = () => {
  document.querySelectorAll(".time-ago").forEach((el) => {
    const raw = el.dataset.time;
    if (raw) {
      el.textContent = formatTimeAgo(raw);
    }
  });
};

const setTheme = (theme) => {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("theme", theme);
  
  const themeIconContainer = document.querySelector("#theme-toggle .dropdown-icon");
  if (themeIconContainer) {
    if (theme === "light") {
      themeIconContainer.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>`;
    } else {
      themeIconContainer.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>`;
    }
  }
};

const initTheme = () => {
  const savedTheme = localStorage.getItem("theme") || "dark";
  setTheme(savedTheme);
};


const showToast = (message, type = "info") => {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  if (type === "success") {
    toast.style.borderColor = "#10b981";
  }
  if (type === "error") {
    toast.style.borderColor = "#ef4444";
  }
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
};

const animateNumbers = () => {
  const elements = document.querySelectorAll("[data-number]");
  if (!elements.length) {
    return;
  }

  const animateValue = (element) => {
    if (element.dataset.animated === "true") {
      return;
    }
    const target = Number(element.dataset.number || 0);
    const suffix = element.dataset.suffix || "";
    const prefix = element.dataset.prefix || "";
    if (Number.isNaN(target)) {
      return;
    }
    const duration = 900;
    const start = performance.now();
    element.dataset.animated = "true";

    const step = (timestamp) => {
      const progress = Math.min((timestamp - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = Math.round(target * eased);
      element.textContent = `${prefix}${value}${suffix}`;
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    };
    requestAnimationFrame(step);
  };

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            animateValue(entry.target);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.4 }
    );
    elements.forEach((element) => observer.observe(element));
  } else {
    elements.forEach((element) => animateValue(element));
  }
};

const revealSections = () => {
  const elements = document.querySelectorAll("[data-reveal]");
  if (!elements.length) return;
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("revealed");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.2 }
    );
    elements.forEach((element) => observer.observe(element));
  } else {
    elements.forEach((element) => element.classList.add("revealed"));
  }
};

const initLazyMedia = () => {
  const media = document.querySelectorAll("[data-src]");
  if (!media.length) return;
  const loadItem = (item) => {
    const src = item.getAttribute("data-src");
    if (!src) return;
    item.setAttribute("src", src);
    item.removeAttribute("data-src");
    item.addEventListener("load", () => item.classList.add("loaded"), { once: true });
  };
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            loadItem(entry.target);
            observer.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "120px" }
    );
    media.forEach((item) => observer.observe(item));
  } else {
    media.forEach((item) => loadItem(item));
  }
};

const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(";").shift();
  }
  return null;
};

const apiFetch = async (url, options = {}) => {
  const token = localStorage.getItem("token");
  const headers = {
    ...(options.headers || {}),
  };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "include",
  });
  if (response.status === 401 && !options.skipAuthRedirect) {
    if (!url.includes("/auth/login") && !url.includes("/auth/register")) {
      window.location.href = "/login";
    }
    return null;
  }
  return response;
};

const getToken = () => localStorage.getItem("token");

const saveAuth = (token, student) => {
  if (token) {
    localStorage.setItem("token", token);
  }
  if (student) {
    localStorage.setItem("student", JSON.stringify(student));
  }
};

const logoutUser = () => {
  localStorage.removeItem("token");
  localStorage.removeItem("student");
  window.location.href = "/auth/logout";
};

const protectPage = () => {};

const attachTokenToRequests = () => {
  window.apiFetch = apiFetch;
};

const parseErrorMessage = async (response) => {
  if (!response) {
    return "Something went wrong";
  }
  try {
    const data = await response.json();
    return data.message || data.error || response.statusText;
  } catch (error) {
    return response.statusText || "Something went wrong";
  }
};

const setButtonLoading = (button, isLoading, loadingText) => {
  if (!button) return;
  const label = button.querySelector(".btn-label");
  if (isLoading) {
    button.classList.add("loading");
    button.disabled = true;
    if (label && loadingText) {
      label.textContent = loadingText;
    }
  } else {
    button.classList.remove("loading");
    button.disabled = false;
    if (label && loadingText) {
      label.textContent = loadingText;
    }
  }
};

const loginUser = async (event, form) => {
  event.preventDefault();
  const button = form.querySelector("button[type='submit']");
  setButtonLoading(button, true, "Signing in...");
  const formData = new FormData(form);
  const payload = {
    email: formData.get("email"),
    password: formData.get("password"),
  };
  try {
    const response = await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
      skipAuthRedirect: true,
    });
    if (!response || !response.ok) {
      const message = await parseErrorMessage(response);
      showToast(message, "error");
      const errorEl = document.getElementById("error");
      if (errorEl) {
        errorEl.textContent = message || "Login failed";
      }
      return;
    }
    const data = await response.json();
    if (data && data.success) {
      saveAuth(data.token, data.student);
      window.location.href = "/dashboard";
    } else {
      showToast("Login failed", "error");
    }
  } catch (error) {
    showToast("Login failed. Please try again.", "error");
  } finally {
    setButtonLoading(button, false, "Sign in");
  }
};

const registerUser = async (event, form) => {
  event.preventDefault();
  const button = form.querySelector("button[type='submit']");
  setButtonLoading(button, true, "Creating account...");
  const payload = new FormData(form);
  try {
    const response = await apiFetch("/auth/register", {
      method: "POST",
      body: payload,
      skipAuthRedirect: true,
    });
    if (!response || !response.ok) {
      const message = await parseErrorMessage(response);
      showToast(message, "error");
      return;
    }
    const data = await response.json();
    if (data && data.success) {
      showToast("Registration successful. Please sign in.", "success");
      window.location.href = "/login";
    } else {
      showToast("Registration failed", "error");
    }
  } catch (error) {
    showToast("Registration failed. Please try again.", "error");
  } finally {
    setButtonLoading(button, false, "Create account");
  }
};


document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  attachTokenToRequests();

  animateNumbers();
  revealSections();
  initLazyMedia();

  const content = document.getElementById("page-content");
  if (content) {
    requestAnimationFrame(() => content.classList.add("is-visible"));
  }

  const sidebarToggle = document.getElementById("sidebar-toggle");

  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", () => {
      document.body.classList.toggle("sidebar-collapsed");
      const sidebarEl = document.querySelector('.sidebar');
      if (sidebarEl) sidebarEl.classList.toggle("collapsed");
      const mainContentEl = document.querySelector('.main-content');
      if (mainContentEl) mainContentEl.classList.toggle("sidebar-collapsed");
      
      localStorage.setItem(
        "sidebarCollapsed",
        document.body.classList.contains("sidebar-collapsed") ? "true" : "false"
      );
    });
  }

  const collapsed = localStorage.getItem("sidebarCollapsed") === "true";
  if (collapsed) {
    document.body.classList.add("sidebar-collapsed");
    const sidebarEl = document.querySelector('.sidebar');
    if (sidebarEl) sidebarEl.classList.add("collapsed");
    const mainContentEl = document.querySelector('.main-content');
    if (mainContentEl) mainContentEl.classList.add("sidebar-collapsed");
  }


  const avatarBtn = document.getElementById("avatar-btn");
  const avatarDropdown = document.getElementById("avatar-dropdown");
  if (avatarBtn && avatarDropdown) {
    avatarBtn.addEventListener("click", () => {
      avatarDropdown.classList.toggle("open");
    });
    document.addEventListener("click", (event) => {
      if (!avatarDropdown.contains(event.target) && !avatarBtn.contains(event.target)) {
        avatarDropdown.classList.remove("open");
      }
    });
  }


  const themeToggle = document.getElementById("theme-toggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const currentTheme = document.documentElement.getAttribute("data-theme");
      const newTheme = currentTheme === "dark" ? "light" : "dark";
      setTheme(newTheme);
    });
  }

  const loginForm = document.querySelector("form[data-auth='login']");
  if (loginForm) {
    loginForm.addEventListener("submit", (event) => loginUser(event, loginForm));
  }

  const registerForm = document.querySelector("form[data-auth='register']");
  if (registerForm) {
    registerForm.addEventListener("submit", (event) => registerUser(event, registerForm));
  }

  document.querySelectorAll("[data-logout]").forEach((button) => {
    button.addEventListener("click", logoutUser);
  });

  document.querySelectorAll("[data-link]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.getAttribute("data-link");
      if (target) {
        document.body.classList.add("page-exit");
        setTimeout(() => window.location.href = target, 150);
      }
    });
  });

  document.querySelectorAll(".sidebar-nav a, .action-grid a").forEach((link) => {
    link.addEventListener("click", (e) => {
      const target = link.getAttribute("href");
      if (target && target.startsWith("/") && !target.includes("#") && target !== window.location.pathname) {
        e.preventDefault();
        document.body.classList.add("page-exit");
        setTimeout(() => window.location.href = target, 150);
      }
    });
  });

  document.querySelectorAll("[data-ai-action]").forEach((button) => {
    button.addEventListener("click", () => {
      showToast("Action queued.", "success");
    });
  });

  updateTimeAgo();
  setInterval(updateTimeAgo, 60000);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      document.body.classList.remove("sidebar-open");
    }
  });
});

window.showToast = showToast;
window.loginUser = loginUser;
window.logoutUser = logoutUser;
window.protectPage = protectPage;
window.attachTokenToRequests = attachTokenToRequests;
window.apiFetch = apiFetch;

// UI-7 Premium Animations & Intersection Observer
document.addEventListener('DOMContentLoaded', () => {
    const observerOptions = { threshold: 0.05, rootMargin: "0px 0px -20px 0px" };
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, i) => {
            if(entry.isIntersecting) {
                // Apply stagger dynamically based on index if multiple appear at once
                setTimeout(() => {
                    entry.target.classList.add('visible');
                }, i * 50);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Attach to all cards and major sections
    const elements = document.querySelectorAll('.widget-card, .card, .panel, .stat-card, section, .focus-item');
    elements.forEach(el => {
        el.classList.add('fade-up');
        observer.observe(el);
    });
});
/* Global Accordion Toggle Function */
window.toggleAccordion = function(header) {
    const content = header.nextElementSibling;
    if (!content) return;
    const icon = header.querySelector('.accordion-icon');
    
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        content.style.maxHeight = content.scrollHeight + "px";
        if (icon) icon.classList.remove('collapsed');
        setTimeout(() => {
            if (!content.classList.contains('collapsed')) {
                content.style.maxHeight = 'none';
            }
        }, 300);
    } else {
        content.style.maxHeight = content.scrollHeight + "px"; 
        setTimeout(() => {
            content.classList.add('collapsed');
            content.style.maxHeight = null;
        }, 10);
        if (icon) icon.classList.add('collapsed');
    }
}
