from rrwebapp.model import db, AgeGradeTable, AgeGradeCategory, AgeGradeFactor
from rrwebapp.helpers import getagfactors


def test_getagfactors_builds_nested_structure_by_surface_gender_distance_age(dbapp):
    with dbapp.app_context():
        table = AgeGradeTable(name='2020 factors')
        db.session.add(table)
        db.session.commit()

        category = AgeGradeCategory(factortable_id=table.id, gender='F', surface='road',
                                     dist_mm=5_000_000, oc_secs=1000.0)
        db.session.add(category)
        db.session.commit()

        db.session.add(AgeGradeFactor(category_id=category.id, age=30, factor=0.85))
        db.session.add(AgeGradeFactor(category_id=category.id, age=40, factor=0.80))
        db.session.commit()

        db.session.refresh(table)
        factors = getagfactors(table)

    assert factors['road']['F'][5000]['OC'] == 1000.0
    assert factors['road']['F'][5000][30] == 0.85
    assert factors['road']['F'][5000][40] == 0.80
    # untouched surface/gender combos stay empty
    assert factors['road']['M'] == {}
    assert factors['track']['F'] == {}


def test_getagfactors_returns_empty_structure_for_table_with_no_categories(dbapp):
    with dbapp.app_context():
        table = AgeGradeTable(name='empty')
        db.session.add(table)
        db.session.commit()
        db.session.refresh(table)

        factors = getagfactors(table)

    assert factors == {
        'road': {'F': {}, 'M': {}, 'X': {}},
        'track': {'F': {}, 'M': {}, 'X': {}},
    }
