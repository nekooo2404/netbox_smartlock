(function (window) {
  const utils = window.NbxUploadUtils;
  const api = window.NbxUploadApi;

  function updateInputs(uploadRoot, files, markChanged = true) {
    const payload = files.map((file) => ({
      id: file.id || null,
      file_name: file.file_name,
      path: file.path || '',
      size: file.size || 0,
    }));
    uploadRoot.querySelector('.nbx-upload-all-files').value = JSON.stringify(payload);
    uploadRoot.querySelector('.nbx-upload-uploaded-files').value = JSON.stringify(
      payload.filter((file) => !file.id)
    );
    uploadRoot.querySelector('.nbx-upload-has-changes').value = markChanged ? 'true' : 'false';
  }

  function render(uploadRoot, files, markChanged = true) {
    const list = uploadRoot.querySelector('.nbx-upload-list');
    list.innerHTML = '';

    if (!files.length) {
      list.innerHTML = '<div class="list-group-item text-muted">No files attached</div>';
      updateInputs(uploadRoot, files, markChanged);
      return;
    }

    files.forEach((file, index) => {
      const item = document.createElement('div');
      item.className = 'list-group-item d-flex align-items-center gap-2';
      const fileName = utils.escapeHtml(file.file_name || file.name || 'Unnamed file');
      const meta = file.id
        ? [utils.formatSize(file.size), 'Saved']
        : [utils.formatSize(file.size), 'Pending save'];
      item.innerHTML = `
        <i class="mdi mdi-file-outline fs-5 text-secondary"></i>
        <div class="flex-grow-1 overflow-hidden">
          <div class="text-truncate">${fileName}</div>
          ${meta.length ? `<small class="text-muted">${utils.escapeHtml(meta.join(' - '))}</small>` : ''}
        </div>
        <button type="button" class="btn btn-sm btn-outline-danger" title="Remove file" data-index="${index}">
          <i class="mdi mdi-trash-can-outline"></i>
        </button>
      `;
      list.appendChild(item);
    });

    list.querySelectorAll('button[data-index]').forEach((button) => {
      button.addEventListener('click', () => {
        const index = Number(button.dataset.index);
        const [removed] = files.splice(index, 1);
        if (removed && !removed.id && removed.path) {
          api.deleteTempFile(uploadRoot, removed).catch(() => {});
        }
        render(uploadRoot, files, true);
      });
    });

    updateInputs(uploadRoot, files, markChanged);
  }

  window.NbxUploadRender = {
    updateInputs,
    render,
  };
})(window);

