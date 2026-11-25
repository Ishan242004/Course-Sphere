/**
 * CourseSphere Authentication & Interactive UI Scripts
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Password Visibility Toggle
    const toggleBtns = document.querySelectorAll('.btn-toggle-password');
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            const targetSelector = this.getAttribute('data-target');
            let input = null;
            if (targetSelector) {
                input = document.querySelector(targetSelector);
            } else {
                input = this.closest('.input-group-custom').querySelector('input');
            }

            if (!input) return;

            const icon = this.querySelector('i');
            if (input.type === 'password') {
                input.type = 'text';
                if (icon) {
                    icon.classList.remove('bi-eye');
                    icon.classList.add('bi-eye-slash');
                }
            } else {
                input.type = 'password';
                if (icon) {
                    icon.classList.remove('bi-eye-slash');
                    icon.classList.add('bi-eye');
                }
            }
        });
    });

    // 2. Real-time Password Match Validation for Registration
    const passInput = document.querySelector('.password-input');
    const confirmInput = document.querySelector('.confirm-password-input');
    const matchFeedback = document.getElementById('password-match-feedback');

    if (passInput && confirmInput && matchFeedback) {
        function validatePasswordMatch() {
            const passVal = passInput.value;
            const confirmVal = confirmInput.value;

            if (!confirmVal) {
                matchFeedback.textContent = '';
                matchFeedback.className = 'form-text';
                confirmInput.classList.remove('is-valid', 'is-invalid');
                return;
            }

            if (passVal === confirmVal) {
                matchFeedback.textContent = '✓ Passwords match';
                matchFeedback.className = 'form-text text-success fw-semibold';
                confirmInput.classList.remove('is-invalid');
                confirmInput.classList.add('is-valid');
            } else {
                matchFeedback.textContent = '✕ Passwords do not match';
                matchFeedback.className = 'form-text text-danger fw-semibold';
                confirmInput.classList.remove('is-valid');
                confirmInput.classList.add('is-invalid');
            }
        }

        passInput.addEventListener('input', validatePasswordMatch);
        confirmInput.addEventListener('input', validatePasswordMatch);
    }

    // 3. Form Submission Loading Indicator
    const authForms = document.querySelectorAll('.auth-form');
    authForms.forEach(form => {
        form.addEventListener('submit', function () {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                if (this.checkValidity()) {
                    submitBtn.disabled = true;
                    const originalText = submitBtn.innerHTML;
                    submitBtn.setAttribute('data-original-text', originalText);
                    submitBtn.innerHTML = `
                        <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                        Processing...
                    `;
                }
            }
        });
    });

    // 4. Auto-dismiss alerts after 6 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 6000);
    });

    // 5. Phone Input: Restrict to 10 digits only
    const phoneInputs = document.querySelectorAll('input[name="phone"], .phone-input');
    phoneInputs.forEach(input => {
        input.addEventListener('input', function () {
            this.value = this.value.replace(/[^0-9]/g, '').slice(0, 10);
        });
    });

    // 6. Dark / Light Theme Switcher (Desktop & Mobile buttons)
    const themeBtns = [
        document.getElementById('themeToggleBtn'),
        document.getElementById('themeToggleBtnMobile'),
    ].filter(Boolean);

    const themeIcons = [
        document.getElementById('themeToggleIcon'),
        document.getElementById('themeToggleIconMobile'),
    ].filter(Boolean);

    function syncThemeIcons() {
        const isDark = document.documentElement.classList.contains('dark');
        themeIcons.forEach(icon => {
            icon.className = isDark ? 'bi bi-sun-fill text-warning' : 'bi bi-moon-stars-fill';
        });
    }

    syncThemeIcons();

    themeBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            const isDark = document.documentElement.classList.toggle('dark');
            document.documentElement.setAttribute('data-bs-theme', isDark ? 'dark' : 'light');
            localStorage.setItem('cs-theme', isDark ? 'dark' : 'light');
            syncThemeIcons();
        });
    });
});
