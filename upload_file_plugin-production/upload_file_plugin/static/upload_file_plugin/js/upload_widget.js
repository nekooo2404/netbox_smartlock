(function () {
  const utils = window.NbxUploadUtils;
  const validation = window.NbxUploadValidation;
  const api = window.NbxUploadApi;
  const renderer = window.NbxUploadRender;

  function setBusy(uploadRoot, isBusy) {
    uploadRoot.querySelector('.nbx-upload-browse').disabled = isBusy;
    uploadRoot.querySelector('.nbx-upload-dropzone').classList.toggle('disabled', isBusy);
  }

  function showErrors(uploadRoot, errors) {
    const errorBox = uploadRoot.querySelector('.nbx-upload-errors');
    if (!errors.length) {
      errorBox.classList.add('d-none');
      errorBox.innerHTML = '';
      return;
    }
    errorBox.classList.remove('d-none');
    errorBox.innerHTML = errors.map((error) => `<div>${utils.escapeHtml(error)}</div>`).join('');
  }

  function uploadFiles(uploadRoot, fileList, files) {
    const selectedFiles = Array.from(fileList || []);
    if (!selectedFiles.length) return;

    const allowedExtensions = utils.parseAllowedExtensions(uploadRoot.dataset.typeFile || '');
    const clientErrors = selectedFiles
      .map((file) => validation.validateFile(file, uploadRoot.dataset.validFlag, allowedExtensions))
      .filter(Boolean);

    if (clientErrors.length) {
      showErrors(uploadRoot, clientErrors);
      return;
    }

    setBusy(uploadRoot, true);
    showErrors(uploadRoot, []);

    Promise.allSettled(selectedFiles.map((selectedFile) => api.uploadFile(uploadRoot, selectedFile)))
      .then((results) => {
        const errors = [];
        results.forEach((result) => {
          if (result.status === 'rejected') {
            errors.push(result.reason.message || 'Tải file lên thất bại.');
            return;
          }
          result.value.forEach((file) => {
            files.push({
              file_name: file.file_name,
              path: file.path,
              size: file.size,
            });
          });
        });
        showErrors(uploadRoot, errors);
        renderer.render(uploadRoot, files, true);
      })
      .finally(() => {
        setBusy(uploadRoot, false);
        uploadRoot.querySelector('.nbx-upload-input').value = '';
      });
  }

  function initUpload(uploadRoot) {
    if (uploadRoot.dataset.initialized === 'true') return;
    uploadRoot.dataset.initialized = 'true';

    const files = utils.findInitialFiles(uploadRoot);
    const fileInput = uploadRoot.querySelector('.nbx-upload-input');
    const browseButton = uploadRoot.querySelector('.nbx-upload-browse');
    const dropzone = uploadRoot.querySelector('.nbx-upload-dropzone');

    browseButton.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (event) => uploadFiles(uploadRoot, event.target.files, files));

    dropzone.addEventListener('dragover', (event) => {
      event.preventDefault();
      dropzone.classList.add('border-primary');
    });
    dropzone.addEventListener('dragleave', () => {
      dropzone.classList.remove('border-primary');
    });
    dropzone.addEventListener('drop', (event) => {
      event.preventDefault();
      dropzone.classList.remove('border-primary');
      uploadFiles(uploadRoot, event.dataTransfer.files, files);
    });

    renderer.render(uploadRoot, files, false);
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.nbx-upload').forEach(initUpload);
  });
})();
