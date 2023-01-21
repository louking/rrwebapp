"""helpers
==========
random utilities
"""

def getagfactors(factortable):
    """get age grade factors for input to loutilities.agegrade.AgeGrade

    in return data structure:
    
    dist is distance in meters (approx)
    openstd is number of seconds for open standard for this distance
    age is age in years (integer)
    factor is age grade factor

    Args:
        factortable (AgeGradeTable): instance of AgeGradeTable

    Returns:
        dict: {
            'road: {
                'F':{dist:{'OC':openstd,age:factor,age:factor,...},...},
                'M':{dist:{'OC':openstd,age:factor,age:factor,...},...},
                'X':{dist:{'OC':openstd,age:factor,age:factor,...},...},
            },
            'trail: {
                'F':{dist:{'OC':openstd,age:factor,age:factor,...},...},
                'M':{dist:{'OC':openstd,age:factor,age:factor,...},...},
                'X':{dist:{'OC':openstd,age:factor,age:factor,...},...},
            },
        }
    """
    
    factors = {
        'road': {
            'F': {},
            'M': {},
            'X': {},
        },
        'track': {
            'F': {},
            'M': {},
            'X': {},
        },
    }
    
    for category in factortable.categories:
        dist_m = int(round(category.dist_mm/1000))
        factors[category.surface][category.gender].setdefault(dist_m, {})
        factors[category.surface][category.gender][dist_m]['OC'] = category.oc_secs
        for factor in category.factors:
            factors[category.surface][category.gender][dist_m].setdefault(factor.age, {})
            factors[category.surface][category.gender][dist_m][factor.age] = factor.factor

    return factors