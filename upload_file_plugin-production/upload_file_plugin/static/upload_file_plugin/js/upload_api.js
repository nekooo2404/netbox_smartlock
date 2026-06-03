(function (window) {
  const utils = window.NbxUploadUtils;

  function parseUploadResponse(response) {
    return response.text().then((body) => {
      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) {
        if (response.redirected || response.status === 403 || response.status === 401) {
          throw new Error('Tải file thất bại vì phiên đăng nhập hoặc CSRF không hợp lệ. Vui lòng tải lại trang và thử lại.');
        }
        throw new Error(`Tải file thất bại với HTTP ${response.status}. Máy chủ trả về HTML thay vì JSON.`);
      }

      let data;
      try {
        data = JSON.parse(body || '{}');
      } catch (error) {
        throw new Error('Tải file thất bại vì máy chủ trả về JSON không hợp lệ.');
      }

      if (!response.ok) {
        const message = data.error || (data.errors || []).join(', ') || `Tải file thất bại với HTTP ${response.status}.`;
        throw new Error(message);
      }

      return data;
    });
  }

  window.NbxUploadApi = {
    uploadFile(uploadRoot, selectedFile) {
      const formData = new FormData();
      formData.append('files', selectedFile);
      formData.append('object_id', uploadRoot.dataset.objectId || '');
      formData.append('model_name', uploadRoot.dataset.modelName || '');
      formData.append('session_key', '');
      formData.append('valid_flg', uploadRoot.dataset.validFlag || '0');
      formData.append('type_file', uploadRoot.dataset.typeFile || '[]');
      formData.append('csrfmiddlewaretoken', utils.getCsrfToken(uploadRoot));

      return fetch(uploadRoot.dataset.uploadUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': utils.getCsrfToken(uploadRoot),
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json',
        },
        body: formData,
      })
        .then(parseUploadResponse)
        .then((data) => {
          if (data.errors && data.errors.length) {
            throw new Error(data.errors.join(', '));
          }
          return data.saved_files || [];
        });
    },

    deleteTempFile(uploadRoot, file) {
      const formData = new FormData();
      formData.append('file_name', file.file_name);
      formData.append('path', file.path);
      formData.append('csrfmiddlewaretoken', utils.getCsrfToken(uploadRoot));

      return fetch(uploadRoot.dataset.deleteTempUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': utils.getCsrfToken(uploadRoot) },
        body: formData,
      });
    },
  };
})(window);

