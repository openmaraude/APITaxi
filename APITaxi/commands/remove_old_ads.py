from . import manager
from APITaxi_models import db

@manager.command
def remove_old_ads():
    db.session.execute("""
       CREATE TABLE IF NOT EXISTS "ADS_old" AS "ADS" WITH NO DATA;
    """)
    db.session.execute("""
        SELECT * INTO "ADS_old" FROM "ADS" 
        WHERE "ADS".id NOT IN (SELECT ads_id FROM taxi);
    """)
    db.session.execute("""
        DELETE FROM "ADS" where id IN (SELECT id FROM "ADS_old")
    """)
    db.session.commit()

@manager.command
def restore_old_ads():
    db.session.execute(""" 
        SELECT * INTO "ADS" FROM "ADS_old"
    """)

