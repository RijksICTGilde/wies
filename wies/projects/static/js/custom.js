// Tab functionality - DISABLED: tabs are now regular links
/*
document.addEventListener('DOMContentLoaded', function() {
  const tabs = document.querySelectorAll('.rvo-tabs__item-link');
  const panels = document.querySelectorAll('.rvo-tabs__panel');
  
  tabs.forEach(tab => {
    tab.addEventListener('click', function(e) {
      e.preventDefault();
      
      // Remove active class from all tabs and panels
      tabs.forEach(t => {
        t.classList.remove('rvo-tabs__item-link--active', 'rvo-link--active');
        t.classList.add('rvo-link--normal');
        t.setAttribute('aria-selected', 'false');
      });
      
      panels.forEach(p => {
        p.classList.remove('rvo-tabs__panel--active');
        p.style.display = 'none';
      });
      
      // Add active class to clicked tab
      this.classList.add('rvo-tabs__item-link--active', 'rvo-link--active');
      this.classList.remove('rvo-link--normal');
      this.setAttribute('aria-selected', 'true');
      
      // Show corresponding panel
      const targetId = this.getAttribute('href').substring(1);
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) {
        targetPanel.classList.add('rvo-tabs__panel--active');
        targetPanel.style.display = 'block';
      }
    });
  });
});
*/

// Filter toggle functionality
function toggleFilters(button) {
  const details = document.querySelector('.rvo-collapsible-filter');
  const chevron = button.querySelector('.rvo-icon-delta-naar-rechts');
  
  details.toggleAttribute('open');
  chevron.classList.toggle('rotated');
}

// Placement form functionality
document.addEventListener('DOMContentLoaded', function() {
    const periodSourceField = document.getElementById('id_period_source');
    const specificStartDateField = document.getElementById('specific_start_date_field');
    const specificEndDateField = document.getElementById('specific_end_date_field');
    const serviceField = document.getElementById('id_service');
    const servicePreview = document.getElementById('service-preview');
    const servicePreviewBody = document.getElementById('service-preview-body');
    
    if (periodSourceField && specificStartDateField && specificEndDateField) {
        function togglePeriodSourceFields() {
            if (periodSourceField.value === 'PLACEMENT') {
                specificStartDateField.style.display = 'block';
                specificEndDateField.style.display = 'block';
            } else {
                specificStartDateField.style.display = 'none';
                specificEndDateField.style.display = 'none';
            }
        }
        
        // Initial toggle on page load
        togglePeriodSourceFields();
        
        // Toggle when period source changes
        periodSourceField.addEventListener('change', togglePeriodSourceFields);
    }
    
    if (serviceField && servicePreview && servicePreviewBody) {
        function loadServiceDetails() {
            const serviceId = serviceField.value;
            if (!serviceId) {
                servicePreview.style.display = 'none';
                return;
            }
            
            fetch(`/api/services/${serviceId}/`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        servicePreview.style.display = 'none';
                        return;
                    }
                    
                    const costCell = data.cost_calculation 
                        ? `${data.cost}<br><small style="color: #666; font-size: 0.8em;">${data.cost_calculation}</small>`
                        : data.cost;
                    
                    servicePreviewBody.innerHTML = `
                        <tr>
                            <td>${data.description}</td>
                            <td>${data.skill}</td>
                            <td>${data.start_date}</td>
                            <td>${data.end_date}</td>
                            <td>${costCell}</td>
                        </tr>
                    `;
                    servicePreview.style.display = 'block';
                })
                .catch(error => {
                    console.error('Error loading service details:', error);
                    servicePreview.style.display = 'none';
                });
        }
        
        // Load service details when service changes
        serviceField.addEventListener('change', loadServiceDetails);
        
        // Initial load
        loadServiceDetails();
    }
});

// Service form functionality
document.addEventListener('DOMContentLoaded', function() {
    const costTypeField = document.getElementById('id_cost_type');
    const fixedCostField = document.getElementById('fixed_cost_field');
    const hoursPerWeekField = document.getElementById('hours_per_week_field');
    
    const periodSourceField = document.getElementById('id_period_source');
    const specificStartDateField = document.getElementById('specific_start_date_field');
    const specificEndDateField = document.getElementById('specific_end_date_field');
    
    if (costTypeField && fixedCostField && hoursPerWeekField) {
        function toggleCostTypeFields() {
            if (costTypeField.value === 'FIXED_PRICE') {
                fixedCostField.style.display = 'block';
                hoursPerWeekField.style.display = 'none';
            } else if (costTypeField.value === 'PER_HOUR') {
                fixedCostField.style.display = 'none';
                hoursPerWeekField.style.display = 'block';
            } else {
                fixedCostField.style.display = 'none';
                hoursPerWeekField.style.display = 'none';
            }
        }
        
        // Initial toggle on page load
        toggleCostTypeFields();
        
        // Toggle when fields change
        costTypeField.addEventListener('change', toggleCostTypeFields);
    }
    
    if (periodSourceField && specificStartDateField && specificEndDateField) {
        function togglePeriodSourceFields() {
            if (periodSourceField.value === 'SERVICE') {
                specificStartDateField.style.display = 'block';
                specificEndDateField.style.display = 'block';
            } else {
                specificStartDateField.style.display = 'none';
                specificEndDateField.style.display = 'none';
            }
        }
        
        // Initial toggle on page load
        togglePeriodSourceFields();
        
        // Toggle when fields change
        periodSourceField.addEventListener('change', togglePeriodSourceFields);
    }
});

// Skills page functionality
document.addEventListener('DOMContentLoaded', function() {
    const skillsTableBody = document.getElementById('skills-table-body');
    
    if (skillsTableBody) {
        let skills = [];

        function loadSkills() {
            fetch('/api/skills/')
                .then(response => response.json())
                .then(data => {
                    skills = data;
                    renderSkillsTable();
                })
                .catch(error => {
                    console.error('Error loading skills:', error);
                });
        }

        function renderSkillsTable() {
            skillsTableBody.innerHTML = '';

            skills.forEach(skill => {
                const row = document.createElement('tr');
                row.className = 'rvo-table-row';
                row.innerHTML = `
                    <td class="rvo-table-cell">${skill.name}</td>
                    <td class="rvo-table-cell">
                        <button type="button" class="rvo-button rvo-button--danger rvo-button--sm" onclick="deleteSkill(${skill.id})">
                            Verwijderen
                        </button>
                    </td>
                `;
                skillsTableBody.appendChild(row);
            });
        }

        function deleteSkill(skillId) {
            const skill = skills.find(s => s.id === skillId);
            const skillName = skill ? skill.name : 'deze skill';
            
            if (!confirm(`Weet je zeker dat je "${skillName}" wilt verwijderen?`)) {
                return;
            }

            fetch(`/api/skills/${skillId}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Fout: ' + data.error);
                } else {
                    loadSkills(); // Reload the table
                    console.log('Skill verwijderd');
                }
            })
            .catch(error => {
                console.error('Error deleting skill:', error);
                alert('Er is een fout opgetreden bij het verwijderen van de skill');
            });
        }

        // Make deleteSkill globally available
        window.deleteSkill = deleteSkill;

        // Load skills on page load
        loadSkills();
    }
}); 