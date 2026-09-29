// Update file input label when user selects a file
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.form-file-input').forEach(function (input) {
    input.addEventListener('change', function () {
      var label = this.nextElementSibling;
      if (label && label.classList.contains('file-input-label')) {
        var fileName = this.files[0] ? this.files[0].name : 'Nenhum arquivo selecionado';
        label.textContent = fileName;
      }
    });
  });

  // Announce flash messages to screen readers
  var flashes = document.querySelectorAll('.flash');
  flashes.forEach(function (el) {
    el.setAttribute('role', 'alert');
    el.setAttribute('aria-live', 'assertive');
  });
});
