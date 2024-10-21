var employer_my_handlers = {
    // fill province
    fill_provinces: function() {
        // selected region
        var region_code = $(this).val();

        // set selected text to input
        var region_text = $(this).find("option:selected").text();
        let region_input = $('#employer_region-text'); // Updated ID
        region_input.val(region_text);
        
        // clear province & city & barangay input
        $('#employer_province-text').val(''); // Updated ID
        $('#employer_city-text').val(''); // Updated ID
        $('#employer_barangay-text').val(''); // Updated ID

        // province
        let dropdown = $('#employer_province'); // Updated ID
        dropdown.empty();
        dropdown.append('<option selected="true" disabled>Choose State/Province</option>');
        dropdown.prop('selectedIndex', 0);

        // city
        let city = $('#employer_city'); // Updated ID
        city.empty();
        city.append('<option selected="true" disabled></option>');
        city.prop('selectedIndex', 0);

        // barangay
        let barangay = $('#employer_barangay'); // Updated ID
        barangay.empty();
        barangay.append('<option selected="true" disabled></option>');
        barangay.prop('selectedIndex', 0);

        // filter & fill
        var url = 'ph-json/province.json';
        $.getJSON(url, function(data) {
            var result = data.filter(function(value) {
                return value.region_code == region_code;
            });

            result.sort(function(a, b) {
                return a.province_name.localeCompare(b.province_name);
            });

            $.each(result, function(key, entry) {
                dropdown.append($('<option></option>').attr('value', entry.province_code).text(entry.province_name));
            });
        });
    },

    // fill city
    fill_cities: function() {
        // selected province
        var province_code = $(this).val();

        // set selected text to input
        var province_text = $(this).find("option:selected").text();
        let province_input = $('#employer_province-text'); // Updated ID
        province_input.val(province_text);
        
        // clear city & barangay input
        $('#employer_city-text').val(''); // Updated ID
        $('#employer_barangay-text').val(''); // Updated ID

        // city
        let dropdown = $('#employer_city'); // Updated ID
        dropdown.empty();
        dropdown.append('<option selected="true" disabled>Choose city/municipality</option>');
        dropdown.prop('selectedIndex', 0);

        // barangay
        let barangay = $('#employer_barangay'); // Updated ID
        barangay.empty();
        barangay.append('<option selected="true" disabled></option>');
        barangay.prop('selectedIndex', 0);

        // filter & fill
        var url = 'ph-json/city.json';
        $.getJSON(url, function(data) {
            var result = data.filter(function(value) {
                return value.province_code == province_code;
            });

            result.sort(function(a, b) {
                return a.city_name.localeCompare(b.city_name);
            });

            $.each(result, function(key, entry) {
                dropdown.append($('<option></option>').attr('value', entry.city_code).text(entry.city_name));
            });
        });
    },

    // fill barangay
    fill_barangays: function() {
        // selected barangay
        var city_code = $(this).val();

        // set selected text to input
        var city_text = $(this).find("option:selected").text();
        let city_input = $('#employer_city-text'); // Updated ID
        city_input.val(city_text);
        
        // clear barangay input
        $('#employer_barangay-text').val(''); // Updated ID

        // barangay
        let dropdown = $('#employer_barangay'); // Updated ID
        dropdown.empty();
        dropdown.append('<option selected="true" disabled>Choose barangay</option>');
        dropdown.prop('selectedIndex', 0);

        // filter & fill
        var url = 'ph-json/barangay.json';
        $.getJSON(url, function(data) {
            var result = data.filter(function(value) {
                return value.city_code == city_code;
            });

            result.sort(function(a, b) {
                return a.brgy_name.localeCompare(b.brgy_name);
            });

            $.each(result, function(key, entry) {
                dropdown.append($('<option></option>').attr('value', entry.brgy_code).text(entry.brgy_name));
            });
        });
    },

    onchange_barangay: function() {
        // set selected text to input
        var barangay_text = $(this).find("option:selected").text();
        let barangay_input = $('#employer_barangay-text'); // Updated ID
        barangay_input.val(barangay_text);
    },
};

$(function() {
    // events
    $('#employer_region').on('change', employer_my_handlers.fill_provinces); // Updated ID
    $('#employer_province').on('change', employer_my_handlers.fill_cities); // Updated ID
    $('#employer_city').on('change', employer_my_handlers.fill_barangays); // Updated ID
    $('#employer_barangay').on('change', employer_my_handlers.onchange_barangay); // Updated ID

    // load region
    let dropdown = $('#employer_region'); // Updated ID
    dropdown.empty();
    dropdown.append('<option selected="true" disabled>Choose Region</option>');
    dropdown.prop('selectedIndex', 0);
    const url = 'ph-json/region.json';
    
    // Populate dropdown with list of regions
    $.getJSON(url, function(data) {
        $.each(data, function(key, entry) {
            dropdown.append($('<option></option>').attr('value', entry.region_code).text(entry.region_name));
        });
    });
});
