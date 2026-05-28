(function (window) {
  const utils = {};

  utils.VALID_IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']);

  utils.getCookie = function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split(';') : [];
    for (const cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.startsWith(`${name}=`)) {
        return decodeURIComponent(trimmed.slice(name.length + 1));
      }
    }
    return null;
  };

  utils.getCsrfToken = function getCsrfToken(uploadRoot) {
    const formToken = uploadRoot.closest('form')?.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
    return formToken || utils.getCookie('csrftoken') || '';
  };

  utils.formatSize = function formatSize(bytes) {
    if (!bytes) return '0 KB';
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  utils.escapeHtml = function escapeHtml(value) {
    const replacements = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    };
    return String(value ?? '').replace(/[&<>"']/g, (char) => replacements[char]);
  };

  utils.fileExtension = function fileExtension(fileName) {
    return (fileName.split('.').pop() || '').toLowerCase();
  };

  utils.parseAllowedExtensions = function parseAllowedExtensions(rawValue) {
    if (!rawValue || !rawValue.trim()) return [];
    try {
      const parsed = JSON.parse(rawValue.replace(/'/g, '"'));
      if (Array.isArray(parsed)) return parsed.map((item) => String(item).toLowerCase());
    } catch (error) {
      return rawValue
        .replace('[', '')
        .replace(']', '')
        .split(',')
        .map((item) => item.trim().replace(/['"]/g, '').toLowerCase())
        .filter(Boolean);
    }
    return [];
  };

  utils.findInitialFiles = function findInitialFiles(uploadRoot) {
    const script = uploadRoot.nextElementSibling;
    if (!script || script.tagName !== 'SCRIPT' || script.type !== 'application/json') return [];
    try {
      return JSON.parse(script.textContent || '[]');
    } catch (error) {
      return [];
    }
  };

  window.NbxUploadUtils = utils;
})(window);

