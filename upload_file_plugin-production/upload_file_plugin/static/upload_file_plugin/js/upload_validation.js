(function (window) {
  const utils = window.NbxUploadUtils;

  window.NbxUploadValidation = {
    validateFile(file, validFlag, allowedExtensions) {
      const displayName = file.name || file.file_name;
      const extension = utils.fileExtension(displayName || '');
      if (!utils.VALID_IMAGE_EXTENSIONS.has(extension)) {
        return `File "${displayName}" phải là ảnh: jpg, jpeg, png, gif, webp, bmp.`;
      }
      if (validFlag === '1' && allowedExtensions.length && !allowedExtensions.includes(extension)) {
        return `File "${displayName}" phải thuộc một trong các định dạng: ${allowedExtensions.join(', ')}.`;
      }
      return null;
    },
  };
})(window);

