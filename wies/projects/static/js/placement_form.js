document.addEventListener('DOMContentLoaded', function() {
    const periodSourceField = document.getElementById('id_period_source');
    const specificStartDateField = document.getElementById('specific_start_date_field');
    const specificEndDateField = document.getElementById('specific_end_date_field');
    const hoursSourceField = document.getElementById('id_hours_source');
    const specificHoursPerWeekField = document.getElementById('specific_hours_per_week_field');
    
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
});


