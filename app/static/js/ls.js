const DEFAULT_PLACEHOLDERS = {
  paperType: 'Choose a service',
  proofType: 'Choose a service', 
  techType: 'Choose a service',
  academicLevel: 'Project-Level'
};
function initializeCustomDropdown(originalSelectId, displayId, optionsId) {
  const originalSelect = document.getElementById(originalSelectId);
  const display = document.getElementById(displayId);
  const options = document.getElementById(optionsId);

  function updateDisplay() {
    const selected = originalSelect.options[originalSelect.selectedIndex];
    const defaultPlaceholder = DEFAULT_PLACEHOLDERS[originalSelectId];
    // display.textContent = selected?.text && selected.value!=='' ? selected.text : 'Select option';
    // display.textContent = selected?.text || 'Choose a service';
    if (selected && selected.text !== 'Loading...' && selected.text !== 'Error Loading Optoions') {
        display.textContent = selected.text;
    } else {
        display.textContent = defaultPlaceholder; 
    }
  }

  function populateOptions() {
    options.innerHTML = '';
    Array.from(originalSelect.options).forEach(option => {
      if (option.text === 'Loading...' || option.text === 'Error loading options') {
        return;
      }
      const div = document.createElement('div');
      div.textContent = option.text;
      div.dataset.value = option.value;
      div.addEventListener('click', () => {
        originalSelect.value = div.dataset.value;
        updateDisplay();
        options.style.display = 'none';
        originalSelect.dispatchEvent(new Event('change')); // trigger any attached logic
      });
      options.appendChild(div);
    });
  }

  display.addEventListener('click', () => {
    if (originalSelect.disabled || originalSelect.classList.contains('loading')) {
      return;
    }
    options.style.display = options.style.display === 'block' ? 'none' : 'block';
  });

  document.addEventListener('click', (e) => {
    if (!display.contains(e.target) && !options.contains(e.target)) {
      options.style.display = 'none';
    }
  });

  // Observe changes in <select> content
  const observer = new MutationObserver(() => {
    populateOptions();
    updateDisplay();
  }, 50);
  observer.observe(originalSelect, { childList: true });

  // Initialize once at load
  populateOptions();
  updateDisplay();

  return {
    refresh: () => {
      populateOptions();
      updateDisplay();
    }
  };
}
let dropdownInstances = {};
// document.addEventListener('DOMContentLoaded', () => {
//   initializeCustomDropdown('paperType', 'customPaperType', 'customPaperOptions');
//   initializeCustomDropdown('proofType', 'customProofType', 'customProofOptions');
//   initializeCustomDropdown('techType', 'customTechType', 'customTechOptions');
//   initializeCustomDropdown('academicLevel', 'customAcademicLevel', 'customAcademicOptions');
// });
document.addEventListener('DOMContentLoaded', () => {
  dropdownInstances.paperType = initializeCustomDropdown('paperType', 'customPaperType', 'customPaperOptions');
  dropdownInstances.proofType = initializeCustomDropdown('proofType', 'customProofType', 'customProofOptions');
  dropdownInstances.techType = initializeCustomDropdown('techType', 'customTechType', 'customTechOptions');
  dropdownInstances.academicLevel = initializeCustomDropdown('academicLevel', 'customAcademicLevel', 'customAcademicOptions');
});

// Global function to refresh all dropdowns (for debugging or manual refresh)
window.refreshAllDropdowns = function() {
  Object.values(dropdownInstances).forEach(instance => {
    if (instance && instance.refresh) {
      instance.refresh();
    }
  });
};