def remove_model_drift(stats, da, time, climy0, climy1):
    return stats.remove_drift(
        da,
        time,
        climy0,
        climy1,
    )
