def analyze(readings):
    """
    Analyzes a list of readings and returns a dictionary containing the minimum, maximum, and mean values.
    """
    if not readings:
        return {'min': None, 'max': None, 'mean': None}
    min_val = min(readings)
    max_val = max(readings)
    mean_val = sum(readings) / len(readings)
    return {'min': min_val, 'max': max_val, 'mean': mean_val}