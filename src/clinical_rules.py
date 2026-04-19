def calculate_mts_category(vitals: dict) -> int:
    """
    Deterministic Manchester Triage System (MTS) Rules Engine.
    Returns Triage Category 1-5 based on strict clinical threshold logic.
    """
    sys_bp = vitals.get("systolic_bp")
    spo2 = vitals.get("spo2")
    hr = vitals.get("heart_rate")
    pain = vitals.get("pain")
    
    # Validation helper
    def is_valid_number(val):
        return val is not None and isinstance(val, (int, float))

    # Rule 1: Category 1 (Immediate)
    # If Systolic BP < 90 or SpO2 < 90% or HR > 140 -> Return Category 1.
    if (is_valid_number(sys_bp) and sys_bp < 90) or \
       (is_valid_number(spo2) and spo2 < 90) or \
       (is_valid_number(hr) and hr > 140):
        return 1
        
    # Rule 2: Category 2 (Very Urgent)
    # If SpO2 < 92% or Pain == 8-10 -> Return Category 2.
    if (is_valid_number(spo2) and spo2 < 92) or \
       (is_valid_number(pain) and (8 <= pain <= 10)):
        return 2

    # Fallback to Category 3, 4, 5 logic (simplified for scope, default 3)
    # In a full implementation, further rules would determine 3-5.
    return 3
