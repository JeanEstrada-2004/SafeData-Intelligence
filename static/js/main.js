// JavaScript principal para el Sistema de Denuncias

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar funciones principales
    initializeDateTime();
    initializeTooltips();
    initializeAnimations();
});

// Actualizar fecha y hora en tiempo real
function initializeDateTime() {
    function updateTime() {
        const now = new Date();
        const options = {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        };
        
        const timeElement = document.getElementById('current-time');
        if (timeElement) {
            timeElement.textContent = now.toLocaleDateString('es-ES', options);
        }
    }
    
    updateTime();
    setInterval(updateTime, 1000);
}

// Inicializar tooltips de Bootstrap
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Animaciones de entrada
function initializeAnimations() {
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
    });
}

// Funciones de utilidad
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    notification.innerHTML = `
        <i class="fas fa-${getIconForType(type)} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remover después del tiempo especificado
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 150);
        }
    }, duration);
}

function getIconForType(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle',
        'primary': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Validador de archivos
function validateFile(file, allowedTypes = ['.xlsx', '.xls'], maxSize = 10 * 1024 * 1024) {
    const errors = [];
    
    // Validar tipo de archivo
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedTypes.includes(fileExtension)) {
        errors.push(`Tipo de archivo no permitido. Solo se aceptan: ${allowedTypes.join(', ')}`);
    }
    
    // Validar tamaño
    if (file.size > maxSize) {
        errors.push(`El archivo es demasiado grande. Máximo permitido: ${formatFileSize(maxSize)}`);
    }
    
    return {
        isValid: errors.length === 0,
        errors: errors
    };
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Funciones para manejo de loading
function showLoading(element) {
    element.classList.add('loading');
    element.style.pointerEvents = 'none';
}

function hideLoading(element) {
    element.classList.remove('loading');
    element.style.pointerEvents = 'auto';
}

// Confirmar acciones
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Formatear fechas
function formatDate(dateString, format = 'dd/mm/yyyy') {
    const date = new Date(dateString);
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    
    switch (format) {
        case 'dd/mm/yyyy':
            return `${day}/${month}/${year}`;
        case 'yyyy-mm-dd':
            return `${year}-${month}-${day}`;
        default:
            return date.toLocaleDateString('es-ES');
    }
}

// Debounce para búsquedas
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Validación de formularios
function validateForm(formId, rules) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    let isValid = true;
    const errors = [];
    
    for (const [fieldName, fieldRules] of Object.entries(rules)) {
        const field = form.querySelector(`[name="${fieldName}"]`);
        if (!field) continue;
        
        // Limpiar errores previos
        field.classList.remove('is-invalid');
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) errorDiv.remove();
        
        // Validar campo
        for (const rule of fieldRules) {
            if (rule.type === 'required' && !field.value.trim()) {
                showFieldError(field, rule.message || `${fieldName} es requerido`);
                isValid = false;
                break;
            } else if (rule.type === 'minLength' && field.value.length < rule.value) {
                showFieldError(field, rule.message || `${fieldName} debe tener al menos ${rule.value} caracteres`);
                isValid = false;
                break;
            } else if (rule.type === 'email' && !isValidEmail(field.value)) {
                showFieldError(field, rule.message || 'Email no válido');
                isValid = false;
                break;
            }
        }
    }
    
    return isValid;
}

function showFieldError(field, message) {
    field.classList.add('is-invalid');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    field.parentNode.appendChild(errorDiv);
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Funciones para manejo de tablas
function sortTable(table, column, direction = 'asc') {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aVal = a.cells[column].textContent.trim();
        const bVal = b.cells[column].textContent.trim();
        
        if (direction === 'asc') {
            return aVal.localeCompare(bVal, 'es', { numeric: true });
        } else {
            return bVal.localeCompare(aVal, 'es', { numeric: true });
        }
    });
    
    rows.forEach(row => tbody.appendChild(row));
}

// Funciones para estadísticas
function calculatePercentage(value, total) {
    if (total === 0) return 0;
    return Math.round((value / total) * 100 * 100) / 100;
}

// Exportar a Excel (simulación)
function exportToExcel(data, filename = 'datos.xlsx') {
    // Esta es una simulación - en producción usarías una librería como SheetJS
    console.log('Exportando datos:', data);
    showNotification('Función de exportación implementada. En producción se descargaría el archivo.', 'info');
}

// Funciones para localStorage (aunque no se use en artifacts)
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
        return true;
    } catch (error) {
        console.error('Error saving to localStorage:', error);
        return false;
    }
}

function loadFromLocalStorage(key, defaultValue = null) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : defaultValue;
    } catch (error) {
        console.error('Error loading from localStorage:', error);
        return defaultValue;
    }
}

// Funciones de ayuda para formularios
function resetFormValidation(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    // Remover clases de validación
    form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    form.querySelectorAll('.is-valid').forEach(el => el.classList.remove('is-valid'));
    
    // Remover mensajes de error
    form.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
    form.querySelectorAll('.valid-feedback').forEach(el => el.remove());
}

// Función para copiar texto al portapapeles
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showNotification('Texto copiado al portapapeles', 'success');
    } catch (error) {
        console.error('Error copying to clipboard:', error);
        showNotification('Error al copiar texto', 'danger');
    }
}

// Función para scroll suave
function smoothScrollTo(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
    }
}

// Event listeners globales
document.addEventListener('click', function(e) {
    // Manejar clicks en elementos con atributo data-action
    if (e.target.hasAttribute('data-action')) {
        const action = e.target.getAttribute('data-action');
        const target = e.target.getAttribute('data-target');
        
        switch (action) {
            case 'scroll-to':
                e.preventDefault();
                smoothScrollTo(target);
                break;
            case 'copy':
                e.preventDefault();
                copyToClipboard(target);
                break;
        }
    }
});

// Manejo de errores globales
window.addEventListener('error', function(e) {
    console.error('Error global:', e.error);
    // En producción, enviarías este error a un servicio de logging
});

// Función de inicialización que se ejecuta cuando el DOM está listo
function init() {
    console.log('Sistema de Denuncias Ciudadanas inicializado');
    
    // Verificar si hay mensajes en URL params
    const urlParams = new URLSearchParams(window.location.search);
    const message = urlParams.get('message');
    const messageType = urlParams.get('type');
    
    if (message) {
        showNotification(decodeURIComponent(message), messageType || 'info');
        // Limpiar los parámetros de la URL
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}