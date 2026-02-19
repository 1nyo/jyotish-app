def get_varga_data(planet, varga_type):
    # ... existing logic ...
    try:
        data = swe.houses(...)  # Updated API call
        # Fix Ketu and Ascendant access logic
        if planet == 'Ketu':
            # New logic for Ketu
            return data['Ketu']
        elif planet == 'Ascendant':
            # New logic for Ascendant
            return data['Ascendant']
        # ... continue for other planets ...
    except Exception as e:
        print(f"Error in get_varga_data: {e}")
