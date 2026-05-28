(function (window) {
  const utils = window.NbxUploadUtils;

  window.NbxUploadValidation = {
    validateFile(file, validFlag, allowedExtensions) {
      const displayName = file.name || file.file_name;
      const extension = utils.fileExtension(displayName || '');
      if (!utils.VALID_IMAGE_EXTENSIONS.has(extension)) {
        return `File "${displayName}" must be an image: jpg, jpeg, png, gif, webp, bmp.`;
      }
      if (validFlag === '1' && allowedExtensions.length && !allowedExtensions.includes(extension)) {
        return `File "${displayName}" must be one of: ${allowedExtensions.join(', ')}.`;
      }
      return null;
    },
  };
})(window);

