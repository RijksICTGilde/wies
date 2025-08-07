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