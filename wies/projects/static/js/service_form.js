document.addEventListener('DOMContentLoaded', function() {
    const periodSourceField = document.getElementById('id_period_source');
    const specificStartDateField = document.getElementById('specific_start_date_field');
    const specificEndDateField = document.getElementById('specific_end_date_field');

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