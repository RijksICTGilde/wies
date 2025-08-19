document.addEventListener('DOMContentLoaded', function() {
    const periodSourceField = document.getElementById('id_period_source');
    const specificStartDateField = document.getElementById('specific_start_date_field');
    const specificEndDateField = document.getElementById('specific_end_date_field');
    const hoursSourceField = document.getElementById('id_hours_source');
    const specificHoursPerWeekField = document.getElementById('specific_hours_per_week_field');
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
    
    if (hoursSourceField && specificHoursPerWeekField) {
        function toggleHoursSourceFields() {
            if (hoursSourceField.value === 'PLACEMENT') {
                specificHoursPerWeekField.style.display = 'block';
            } else {
                specificHoursPerWeekField.style.display = 'none';
            }
        }
        
        // Initial toggle on page load
        toggleHoursSourceFields();
        
        // Toggle when hours source changes
        hoursSourceField.addEventListener('change', toggleHoursSourceFields);
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
                    
                    // Handle hours source for fixed price services
                    if (hoursSourceField) {
                        console.log(data.cost_type)
                        if (data.cost_type === 'FIXED_PRICE') {
                            console.log('here!')
                            hoursSourceField.value = 'PLACEMENT';
                            hoursSourceField.disabled = true;
                            if (specificHoursPerWeekField) {
                                specificHoursPerWeekField.style.display = 'block';
                            }
                        } else {
                            console.log('else')
                            hoursSourceField.disabled = false;
                            toggleHoursSourceFields();
                        }
                    }
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


